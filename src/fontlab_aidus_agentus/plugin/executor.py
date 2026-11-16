# this_file: src/fontlab_aidus_agentus/plugin/executor.py
# Copyright 2025 Fontlab Ltd. All rights reserved.
"""FontLab tool executor: runs LLM-requested operations inside FontLab's sandbox.

When the Core's LLM decides to call a tool (e.g. ``run_fontlab_script``), it
sends a tool-call request back over stdin. The Plugin picks this up, routes it
here, and executes it inside FontLab's Python environment.

The sandbox strips dangerous builtins (eval, exec, __import__, open) and
captures stdout so script output can be returned to the LLM as a tool result.

Tools are registered via :class:`ToolRegistry`. Each tool entry carries:
- A handler callable
- Metadata: required_params, optional_params, description, requires_font, requires_glyph

Outside FontLab (e.g. during static analysis), the ``fontlab`` import fails
gracefully: ``FL_AVAILABLE`` is False and tool calls return an error response
rather than crashing.
"""

from __future__ import annotations

import sys
import math
import traceback
from io import StringIO
from typing import Any, Callable, Dict, List, Optional

# E5.08: FL_AVAILABLE flag for graceful degradation outside FontLab
_fl_available = False
fl: Any = None
try:
    import fontlab as fl  # type: ignore[import-not-found, no-redef]

    _fl_available = True
except ImportError:
    _fl_available = False

FL_AVAILABLE = _fl_available
METRIC_ABS_TOLERANCE = 1e-6


class ToolError(Exception):
    """Error raised when tool execution fails."""

    pass


class ToolRegistry:
    """Registry for FontLab tools (E5.01, E5.02)."""

    def __init__(self) -> None:
        self._tools: Dict[str, Callable[..., Any]] = {}
        self._tool_info: Dict[str, Dict[str, Any]] = {}

    def register(
        self,
        name: str,
        handler: Callable[..., Any],
        required_params: Optional[List[str]] = None,
        optional_params: Optional[List[str]] = None,
        requires_font: bool = False,
        requires_glyph: bool = False,
    ) -> None:
        """Register a tool handler."""
        self._tools[name] = handler
        self._tool_info[name] = {
            "required_params": required_params or [],
            "optional_params": optional_params or [],
            "requires_font": requires_font,
            "requires_glyph": requires_glyph,
        }

    def get(self, name: str) -> Optional[Callable[..., Any]]:
        return self._tools.get(name)

    def get_info(self, name: str) -> Optional[Dict[str, Any]]:
        return self._tool_info.get(name)

    def has(self, name: str) -> bool:
        return name in self._tools

    def list_all(self) -> List[str]:
        return list(self._tools.keys())


class FontLabExecutor:
    """
    Executor for FontLab tool calls.

    Dispatches tool calls to the appropriate handlers with error handling,
    argument validation, and result sanitization.
    """

    def __init__(self) -> None:
        self._registry = ToolRegistry()
        self._timeout_seconds: int = 30
        self._script_interrupted = False
        self._register_builtin_tools()

    def _register_builtin_tools(self) -> None:
        """Register built-in FontLab tools."""
        self._registry.register(
            "get_current_glyph_info",
            self._get_current_glyph_info,
            requires_glyph=True,
        )
        self._registry.register(
            "set_glyph_metrics",
            self._set_glyph_metrics,
            optional_params=["width", "lsb", "rsb"],
            requires_glyph=True,
        )
        self._registry.register(
            "run_fontlab_script",
            self._run_fontlab_script,
            required_params=["code"],
            requires_font=False,
        )
        self._registry.register(
            "list_tools",
            self._list_tools,
        )

    # ==========================================================================
    # E5.01: Main run() Dispatcher
    # ==========================================================================

    def run(self, tool_name: str, arguments: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Execute a tool and return the result."""
        if arguments is None:
            arguments = {}
        if tool_name == "run_fontlab_script" and "script" in arguments and "code" not in arguments:
            arguments = {**arguments, "code": arguments["script"]}
            del arguments["script"]

        if not self._registry.has(tool_name):
            return self._make_error("Unknown tool: %s" % tool_name)

        info = self._registry.get_info(tool_name)
        handler = self._registry.get(tool_name)

        if info is None or handler is None:
            return self._make_error("Tool registration error")

        # E5.09: Validate arguments
        validation_error = self._validate_args(tool_name, arguments, info)
        if validation_error:
            return validation_error

        # Native preflight and handlers share the tool error contract.
        try:
            # E5.11: Check FontLab requirements
            if info.get("requires_font"):
                guard_error = self._require_font()
                if guard_error:
                    return guard_error

            if info.get("requires_glyph"):
                guard_error = self._require_glyph()
                if guard_error:
                    return guard_error

            result = handler(**arguments)
            return self._sanitize_result(result)
        except ToolError as e:
            return self._make_error(str(e))
        except Exception as e:
            return self._make_error("Execution error: %s" % str(e))

    # ==========================================================================
    # E5.09: Argument Validation
    # ==========================================================================

    def _validate_args(
        self,
        tool_name: str,
        arguments: Dict[str, Any],
        info: Dict[str, Any],
    ) -> Optional[Dict[str, Any]]:
        """Validate tool arguments against required/optional params."""
        required = set(info.get("required_params", []))
        optional = set(info.get("optional_params", []))
        allowed = required | optional
        provided = set(arguments.keys())

        missing = required - provided
        if missing:
            return self._make_error(
                "Missing required params for %s: %s" % (tool_name, ", ".join(sorted(missing)))
            )

        unknown = provided - allowed
        if unknown and allowed:
            return self._make_error(
                "Unknown params for %s: %s" % (tool_name, ", ".join(sorted(unknown)))
            )

        return None

    # ==========================================================================
    # E5.10: Result Sanitization
    # ==========================================================================

    def _sanitize_result(self, result: Any) -> Dict[str, Any]:
        """Convert result to JSON-safe dictionary."""
        if result is None:
            return {"success": True}

        if isinstance(result, dict):
            return self._sanitize_dict(result)

        if isinstance(result, (list, tuple)):
            return {"result": [self._sanitize_value(v) for v in result]}

        return {"result": self._sanitize_value(result)}

    def _sanitize_dict(self, d: Dict[str, Any]) -> Dict[str, Any]:
        return {str(k): self._sanitize_value(v) for k, v in d.items()}

    def _sanitize_value(self, value: Any) -> Any:
        """Convert a single value to JSON-safe format."""
        if value is None or isinstance(value, (bool, int, float, str)):
            return value
        if isinstance(value, (list, tuple)):
            return [self._sanitize_value(v) for v in value]
        if isinstance(value, dict):
            return self._sanitize_dict(value)
        # Fallback: convert to string
        return str(value)

    # ==========================================================================
    # E5.11: Font/Glyph Guards
    # ==========================================================================

    def _require_font(self) -> Optional[Dict[str, Any]]:
        """Guard that requires a font to be open."""
        if not FL_AVAILABLE:
            return self._make_error("FontLab not available")
        if fl is None or fl.CurrentFont() is None:
            return self._make_error("No font is currently open")
        return None

    def _require_glyph(self) -> Optional[Dict[str, Any]]:
        """Guard that requires a glyph to be selected."""
        font_error = self._require_font()
        if font_error:
            return font_error
        try:  # the workspace record answers without CurrentGlyph()'s destructive export
            active = fl.flWorkspace.instance().currentGlyph
            if active is not None and active.glyph is not None and not getattr(active.glyph, "isNull", False):
                return None
        except AttributeError:
            pass
        if fl.CurrentGlyph() is None:
            return self._make_error("No glyph is currently selected")
        return None

    def _make_error(self, message: str) -> Dict[str, Any]:
        return {"error": message}

    # ==========================================================================
    # E5.03: get_current_glyph_info Tool
    # ==========================================================================

    def _current_glyph(self) -> Any:
        """Return a glyph with metric accessors.

        FontLab 9's CurrentGlyph() returns an fgGlyph, which has no sidebearings;
        wrap it as flGlyph(fgGlyph, CurrentFont()), as TypeRig does.
        """
        glyph = fl.CurrentGlyph()  # type: ignore[union-attr]
        if glyph is None:
            raise ToolError("No glyph is currently selected")
        if hasattr(glyph, "lsb") or hasattr(glyph, "getLSB") or not hasattr(fl, "flGlyph"):
            return glyph
        return fl.flGlyph(glyph, fl.CurrentFont())  # type: ignore[union-attr]

    def _active_glyph_for_read(self) -> Any:
        """Return the workspace's active glyph without calling CurrentGlyph().

        CurrentGlyph() exports the glyph through fgGlyph(true), which drops a fresh
        lib.note mirror (fl#8525). The workspace record is read-only. It must belong
        to the workspace's current font, otherwise it is stale and we refuse to guess.
        Builds without a workspace glyph keep the old CurrentGlyph() route.
        """
        try:
            workspace = fl.flWorkspace.instance()  # type: ignore[union-attr]
            active = workspace.currentGlyph
            glyph = None if active is None else active.glyph
            package = workspace.currentPackage
        except AttributeError:
            return self._current_glyph()
        if glyph is None or getattr(glyph, "isNull", False):
            return self._current_glyph()
        owner = getattr(glyph, "package", None)
        if (package is None or getattr(package, "isNull", False) or owner is None
                or owner.id != package.id):
            raise ToolError("Active glyph does not belong to the active font")
        return glyph

    def _require_same_glyph_as_read(self, glyph: Any) -> None:
        """Refuse a write when CurrentGlyph() is not the glyph the read path shows.

        The info read uses the workspace's active glyph, the write uses CurrentGlyph().
        If the two disagree (glyph window closed, another glyph selected) the user
        would read glyph A and edit glyph B. Builds without a workspace record keep
        trusting CurrentGlyph().
        """
        try:
            workspace = fl.flWorkspace.instance()  # type: ignore[union-attr]
            active = workspace.currentGlyph
            shown = None if active is None else active.glyph
            package = workspace.currentPackage
        except AttributeError:
            return
        if shown is None or getattr(shown, "isNull", False):
            return
        owner = getattr(shown, "package", None)
        font = fl.CurrentFont()  # type: ignore[union-attr]
        if (shown.name != glyph.name or owner is None or package is None
                or owner.id != package.id or package.fgId != font.id):
            raise ToolError("The active glyph differs from the current glyph; select the glyph again")

    def _get_current_glyph_info(self) -> Dict[str, Any]:
        """Get information about the currently selected glyph."""
        glyph = self._active_glyph_for_read()
        native = not hasattr(glyph, "width")
        if native:
            layer = self._metric_layer(glyph)
            width, lsb, rsb = glyph.advanceWidth, glyph.getLSB(layer.transform), glyph.getRSB(layer.transform)
            unicode_value = self._native_unicode(glyph)
        else:
            width, lsb, rsb, unicode_value = glyph.width, glyph.lsb, glyph.rsb, glyph.unicode
        return {"name": glyph.name, "unicode": unicode_value, "width": width,
                "lsb": lsb, "rsb": rsb, "height": getattr(glyph, "height", None),
                "layers": len(getattr(glyph, "layers", []))}

    def _native_unicode(self, glyph: Any) -> Any:
        """Read the registered owner's record without rebuilding glyph data."""
        owner = glyph.package
        if owner is None or owner.isNull:
            raise ToolError("Glyph has no registered font owner")
        # findPackageId takes the FontGate id (uint), not flPackage.id; verified natively 2026-11-03.
        package = fl.flWorkspace.instance().findPackageId(owner.fgId)
        if (package is None or package.isNull or package.id != owner.id
                or package.fgId != owner.fgId):
            raise ToolError("Glyph no longer belongs to its registered font")
        # Never read fgPackage on an orphan or fgGlyph on a fresh-note glyph.
        font = package.fgPackage
        if font is None or font.id != package.fgId:
            raise ToolError("Registered FontGate font identity changed")
        if sum(name == glyph.name for name in font.keys()) != 1:
            raise ToolError("Registered FontGate glyph name is missing or ambiguous")
        record = font[glyph.name]
        if record is None or record.name != glyph.name or record.id != glyph.fgGlyphId:
            raise ToolError("Registered FontGate glyph identity changed")
        return record.unicode

    def _metric_layer(self, glyph: Any) -> Any:
        """Use the glyph's native layer transform, which FontLab can convert."""
        layer = glyph.activeLayer
        if layer is None and glyph.layers:
            layer = glyph.layers[0]
        if layer is None:
            raise ToolError("No active glyph layer available for metrics")
        return layer

    # ==========================================================================
    # E5.04: set_glyph_metrics Tool
    # ==========================================================================

    def _set_glyph_metrics(
        self,
        width: Optional[int] = None,
        lsb: Optional[int] = None,
        rsb: Optional[int] = None,
    ) -> Dict[str, Any]:
        """Set metrics on the currently selected glyph; native edits add one Undo step."""
        glyph = self._current_glyph()
        self._require_same_glyph_as_read(glyph)
        changes: List[str] = []
        native = not hasattr(glyph, "width")
        layer = self._metric_layer(glyph) if native else None
        if native and any(value is not None for value in (width, lsb, rsb)):
            if layer.autoLayer:
                raise ToolError("Cannot change metrics on an automatic layer")
        undoable = native and self._metrics_differ(glyph, layer, width, lsb, rsb)
        if undoable:
            # FontLab stores an object's state at each notification and Undo restores
            # the previous stored one: record the pre-change state first.
            self._notify_undo_step(layer, glyph)
        try:
            return self._apply_glyph_metrics(glyph, layer, changes, width, lsb, rsb)
        finally:
            if undoable and changes:
                self._notify_undo_step(layer, glyph)

    @staticmethod
    def _metrics_differ(glyph: Any, layer: Any, width: Any, lsb: Any, rsb: Any) -> bool:
        """True when any requested metric differs from the current one (no-ops add no Undo entry)."""
        current = (
            (width, glyph.advanceWidth),
            (lsb, glyph.getLSB(layer.transform) if lsb is not None else None),
            (rsb, glyph.getRSB(layer.transform) if rsb is not None else None),
        )
        return any(
            wanted is not None
            and not math.isclose(have, wanted, rel_tol=0, abs_tol=METRIC_ABS_TOLERANCE)
            for wanted, have in current
        )

    def _notify_undo_step(self, layer: Any, glyph: Any) -> None:
        """An Edit > Undo state needs the changed layer, then its glyph, in one list."""
        items = getattr(fl, "flItems", None)
        if items is not None:
            items().notifyChangesApplied("Aidus: set glyph metrics", [layer, glyph])

    def _apply_glyph_metrics(
        self, glyph: Any, layer: Any, changes: List[str],
        width: Optional[int], lsb: Optional[int], rsb: Optional[int],
    ) -> Dict[str, Any]:
        native = layer is not None
        if width is not None:
            if native:
                glyph.advanceWidth = width
            else:
                glyph.width = width
            changes.append("width=%d" % width)
        if lsb is not None:
            if native:
                if not glyph.setLSB(lsb, False, layer.transform) and not math.isclose(
                    glyph.getLSB(layer.transform), lsb, rel_tol=0, abs_tol=METRIC_ABS_TOLERANCE
                ):
                    return {"error": "LSB change was not applied", "changes": changes}
            else:
                glyph.lsb = lsb
            changes.append("lsb=%d" % lsb)
        if rsb is not None:
            if native:
                if not glyph.setRSB(rsb, layer.transform) and not math.isclose(
                    glyph.getRSB(layer.transform), rsb, rel_tol=0, abs_tol=METRIC_ABS_TOLERANCE
                ):
                    return {"error": "RSB change was not applied", "changes": changes}
            else:
                glyph.rsb = rsb
            changes.append("rsb=%d" % rsb)

        result = {"success": True, "changes": changes, "glyph": glyph.name}
        if native:
            result["metrics"] = {"width": glyph.advanceWidth, "lsb": glyph.getLSB(layer.transform),
                                 "rsb": glyph.getRSB(layer.transform)}
        return result

    # ==========================================================================
    # E5.05 & E5.06 & E5.07: run_fontlab_script Tool
    # ==========================================================================

    def _run_fontlab_script(self, code: str) -> Dict[str, Any]:
        """Execute arbitrary Python code in FontLab context."""
        # E5.14: Validate code syntax before execution
        validation_error = self._validate_code_syntax(code)
        if validation_error:
            return validation_error

        # E5.06: Build script context
        context = self._build_script_context()

        # E5.12: Set up timeout tracer
        self._script_interrupted = False
        if self._timeout_seconds > 0:
            self._setup_timeout_tracer()

        # E5.15: Capture stdout during execution
        captured_stdout = StringIO()
        original_stdout = sys.stdout

        try:
            # Redirect stdout to capture print() output
            sys.stdout = captured_stdout

            # E5.05: Execute code
            exec(code, context)  # noqa: S102 - Intentional dynamic execution for FL scripting

            # Get captured output
            stdout_output = captured_stdout.getvalue()

            result: Dict[str, Any] = {"success": True, "result": context.get("result")}
            if stdout_output:
                result["stdout"] = stdout_output
            return result

        except SystemExit:
            stdout_output = captured_stdout.getvalue()
            error_result = self._make_error("Script called sys.exit()")
            if stdout_output:
                error_result["stdout"] = stdout_output
            return error_result

        except Exception:
            # E5.07: Capture traceback
            tb_lines = traceback.format_exc().splitlines()
            stdout_output = captured_stdout.getvalue()
            error_result: Dict[str, Any] = {"error": "Script error", "traceback": tb_lines[-5:]}
            if stdout_output:
                error_result["stdout"] = stdout_output
            return error_result

        finally:
            # Always restore stdout
            sys.stdout = original_stdout
            self._clear_timeout_tracer()

    def _validate_code_syntax(self, code: str) -> Optional[Dict[str, Any]]:
        """Validate Python code syntax using compile() (E5.14)."""
        try:
            compile(code, "<script>", "exec")
            return None
        except SyntaxError as e:
            error_msg = "Syntax error"
            if e.lineno:
                error_msg = "Syntax error at line %d" % e.lineno
            if e.msg:
                error_msg = "%s: %s" % (error_msg, e.msg)
            return {"error": error_msg, "line": e.lineno, "offset": e.offset}

    def _build_script_context(self) -> Dict[str, Any]:
        """Build the execution context for scripts (E5.06)."""
        context: Dict[str, Any] = {
            "__builtins__": self._get_sandboxed_builtins(),
            "result": None,
        }

        if FL_AVAILABLE and fl is not None:
            context["fl"] = fl
            context["CurrentFont"] = fl.CurrentFont
            context["CurrentGlyph"] = fl.CurrentGlyph
            font = fl.CurrentFont()
            if font is not None:
                context["font"] = font
            glyph = fl.CurrentGlyph()
            if glyph is not None:
                context["glyph"] = glyph

        return context

    def _get_sandboxed_builtins(self) -> Dict[str, Any]:
        """Return builtins with dangerous functions removed (E5.16)."""
        import builtins

        dangerous = {
            "eval",
            "exec",
            "compile",
            "__import__",
            "open",
            "input",
            "breakpoint",
            "exit",
            "quit",
        }

        safe_builtins: Dict[str, Any] = {}
        for name in dir(builtins):
            if not name.startswith("_") and name not in dangerous:
                safe_builtins[name] = getattr(builtins, name)

        safe_builtins["True"] = True
        safe_builtins["False"] = False
        safe_builtins["None"] = None

        return safe_builtins

    # ==========================================================================
    # E5.12: Timeout Protection
    # ==========================================================================

    def _setup_timeout_tracer(self) -> None:
        """Set up execution timeout via sys.settrace."""
        import time

        self._script_start_time = time.time()
        self._previous_tracer = sys.gettrace()
        self._tracer_active = True

        events = [0]

        def timeout_tracer(frame: Any, event: str, arg: Any) -> Optional[Callable[..., Any]]:
            if event == "call":
                # A one-line loop (`while True: pass`) emits no line events on CPython 3.11;
                # opcode events reach it on every version.
                frame.f_trace_opcodes = True
            events[0] += 1
            if event != "call" and events[0] % 64:
                return timeout_tracer  # read the clock every 64 events, not per opcode
            if self._script_interrupted:
                raise TimeoutError("Script execution timed out")
            elapsed = time.time() - self._script_start_time
            if elapsed > self._timeout_seconds:
                self._script_interrupted = True
                raise TimeoutError("Script execution timed out (%.1fs)" % elapsed)
            return timeout_tracer

        sys.settrace(timeout_tracer)

    def _clear_timeout_tracer(self) -> None:
        """Remove the timeout tracer, restoring any tracer (debugger, coverage) it replaced."""
        if getattr(self, "_tracer_active", False):
            sys.settrace(self._previous_tracer)
            self._tracer_active, self._previous_tracer = False, None

    # ==========================================================================
    # Tool Introspection (E5.13 - list available tools)
    # ==========================================================================

    def _list_tools(self) -> Dict[str, Any]:
        """List all available tools and their parameters."""
        tools: List[Dict[str, Any]] = []
        for name in self._registry.list_all():
            info = self._registry.get_info(name)
            if info:
                tools.append(
                    {
                        "name": name,
                        "required_params": info.get("required_params", []),
                        "optional_params": info.get("optional_params", []),
                        "requires_font": info.get("requires_font", False),
                        "requires_glyph": info.get("requires_glyph", False),
                    }
                )
        return {"tools": tools}

    def has_tool(self, name: str) -> bool:
        """Check if a tool is registered."""
        return self._registry.has(name)

    def list_tools(self) -> List[str]:
        """Get list of tool names."""
        return self._registry.list_all()

    def set_timeout(self, seconds: int) -> None:
        """Set script execution timeout in seconds."""
        self._timeout_seconds = seconds
