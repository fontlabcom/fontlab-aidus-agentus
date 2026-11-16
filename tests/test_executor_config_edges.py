# this_file: tests/test_executor_config_edges.py
"""Executor guards/sandbox/timeout and configuration edge cases, host-side."""

import json
import os
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest

from fontlab_aidus_agentus.plugin import config, executor as executor_module
from fontlab_aidus_agentus.plugin.executor import FontLabExecutor, ToolError


@pytest.fixture
def ex():
    return FontLabExecutor()


def fontlab(font=True, glyph=None):
    return SimpleNamespace(CurrentFont=lambda: object() if font else None, CurrentGlyph=lambda: glyph,
                           flWorkspace=SimpleNamespace(instance=lambda: SimpleNamespace(
                               findPackageId=lambda identity: glyph.package)))


class NativeGlyph:
    """flGlyph-like: advanceWidth plus transform-based sidebearings; no `width`."""

    def __init__(self, layers=("L",), active="L", setters_ok=True):
        self.name, self.advanceWidth = "Ą", 500
        self.fgGlyphId = 201
        self.fgGlyph = SimpleNamespace(name=self.name, id=201, unicode=0x104)
        class Font(dict):
            id = 301
        self.package = SimpleNamespace(id=401, fgId=301, isNull=False,
                                       fgPackage=Font({self.name: self.fgGlyph}))
        self.layers = [SimpleNamespace(transform=t, autoLayer=False) for t in layers]
        self.activeLayer = SimpleNamespace(transform=active, autoLayer=False) if active else None
        self._lsb, self._rsb, self.setters_ok = 40, 60, setters_ok

    def getLSB(self, transform):
        return self._lsb

    def getRSB(self, transform):
        return self._rsb

    def setLSB(self, value, _flag, transform):
        if self.setters_ok:
            self._lsb = value
        return self.setters_ok

    def setRSB(self, value, transform):
        if self.setters_ok:
            self._rsb = value
        return self.setters_ok


@pytest.fixture
def in_fontlab(monkeypatch):
    def install(**kwargs):
        monkeypatch.setattr(executor_module, "FL_AVAILABLE", True)
        monkeypatch.setattr(executor_module, "fl", fontlab(**kwargs))
    return install


def test_run_when_fontlab_absent_guards_glyph_tools(ex, monkeypatch):
    monkeypatch.setattr(executor_module, "FL_AVAILABLE", False)
    assert ex.run("get_current_glyph_info") == {"error": "FontLab not available"}


def test_run_when_no_font_or_no_glyph_reports_each(ex, in_fontlab):
    in_fontlab(font=False)
    assert ex.run("get_current_glyph_info") == {"error": "No font is currently open"}
    in_fontlab(font=True, glyph=None)
    assert ex.run("set_glyph_metrics", {"width": 1}) == {"error": "No glyph is currently selected"}


def test_run_when_registry_inconsistent_reports_registration_error(ex):
    ex._registry._tools["ghost"] = lambda: None  # registered handler without metadata
    assert ex.run("ghost") == {"error": "Tool registration error"}


def test_run_when_handler_raises_tool_error_or_exception(ex):
    ex._registry.register("tool_error", lambda: (_ for _ in ()).throw(ToolError("refused")))
    ex._registry.register("crash", lambda: 1 / 0)
    assert ex.run("tool_error") == {"error": "refused"}
    assert ex.run("crash")["error"].startswith("Execution error: division by zero")


@pytest.mark.parametrize(
    "value,expected",
    [(None, {"success": True}), ([1, (2, 3)], {"result": [1, [2, 3]]}), ((), {"result": []}),
     (3.5, {"result": 3.5}), ({1: {"set": {9}}}, {"1": {"set": "{9}"}}), (b"x", {"result": "b'x'"})],
)
def test_sanitize_result_when_varied_values_are_json_safe(ex, value, expected):
    result = ex._sanitize_result(value)
    assert result == expected
    json.dumps(result)


def test_native_glyph_info_when_flglyph_reads_transform_metrics(ex, in_fontlab):
    in_fontlab(glyph=NativeGlyph())
    info = ex.run("get_current_glyph_info")
    assert info == {"name": "Ą", "unicode": 0x104, "width": 500, "lsb": 40, "rsb": 60, "height": None, "layers": 1}


def test_native_metrics_when_no_active_layer_uses_first_layer(ex, in_fontlab):
    in_fontlab(glyph=NativeGlyph(active=None))
    assert ex.run("set_glyph_metrics", {"lsb": 10})["metrics"]["lsb"] == 10


def test_native_metrics_when_no_layers_reports_tool_error(ex, in_fontlab):
    in_fontlab(glyph=NativeGlyph(layers=(), active=None))
    assert ex.run("set_glyph_metrics", {"width": 1}) == {"error": "No active glyph layer available for metrics"}


@pytest.mark.parametrize("field", ["lsb", "rsb"])
def test_native_metrics_when_setter_refuses_and_value_differs_reports_error(ex, in_fontlab, field):
    in_fontlab(glyph=NativeGlyph(setters_ok=False))
    result = ex.run("set_glyph_metrics", {"width": 520, field: 5})
    assert result["error"] == "%s change was not applied" % field.upper()
    assert result["changes"] == ["width=520"], "Report the partial change"


def test_native_metrics_when_setter_noop_but_value_matches_succeeds(ex, in_fontlab):
    in_fontlab(glyph=NativeGlyph(setters_ok=False))
    result = ex.run("set_glyph_metrics", {"lsb": 40, "rsb": 60.0000001})
    assert result["success"] and result["changes"] == ["lsb=40", "rsb=60"]


def test_script_when_sys_exit_reports_and_keeps_output(ex, monkeypatch):
    monkeypatch.setattr(executor_module, "FL_AVAILABLE", False)
    result = ex.run("run_fontlab_script", {"code": "print('before')\nraise SystemExit(3)"})
    assert result == {"error": "Script called sys.exit()", "stdout": "before\n"}


def test_script_when_exception_returns_traceback_tail_and_output(ex):
    result = ex.run("run_fontlab_script", {"code": "print('partial')\n{}['missing']"})
    assert result["error"] == "Script error" and result["stdout"] == "partial\n"
    assert any("KeyError" in line for line in result["traceback"])


def test_script_when_runs_forever_is_interrupted_by_timeout(ex):
    previous, stdout = sys.gettrace(), sys.stdout
    ex.set_timeout(0.2)
    try:
        result = ex.run("run_fontlab_script", {"code": "while True:\n    x = 1"})
    finally:
        sys.settrace(previous)
    assert result["error"] == "Script error"
    assert any("timed out" in line for line in result["traceback"])
    assert sys.stdout is stdout, "stdout is restored after an interrupted script"


@pytest.mark.parametrize("code", ["import os", "open('/etc/passwd')", "eval('1')", "__import__('os')"])
def test_script_when_dangerous_builtin_used_fails_in_sandbox(ex, code):
    result = ex.run("run_fontlab_script", {"code": code})
    assert result["error"] == "Script error"


def test_script_when_syntax_error_reports_line(ex):
    result = ex.run("run_fontlab_script", {"code": "x = (\n"})
    assert result["error"].startswith("Syntax error") and result["line"]


def test_script_when_in_fontlab_exposes_font_and_glyph(ex, in_fontlab):
    glyph = SimpleNamespace(name="a")
    in_fontlab(glyph=glyph)
    result = ex.run("run_fontlab_script", {"code": "result = (font is not None, glyph.name, CurrentGlyph() is glyph)"})
    assert result == {"success": True, "result": [True, "a", True]}


def test_list_tools_and_has_tool_when_queried(ex):
    names = {tool["name"] for tool in ex.run("list_tools")["tools"]}
    assert names == set(ex.list_tools()) and ex.has_tool("run_fontlab_script") and not ex.has_tool("x")


# --- configuration --------------------------------------------------------


def test_get_api_key_when_no_mapping_uses_canonical_env(monkeypatch):
    monkeypatch.setenv("ANTHROPIC_API_KEY", "a-key")
    assert config.get_api_key({}, "anthropic") == "a-key"
    assert config.get_api_key({}, "openai") is None


def test_get_api_key_when_key_file_missing_or_unreadable_returns_none(tmp_path, monkeypatch):
    assert config.get_api_key({"api_keys": {"x": str(tmp_path / "absent")}}, "x") is None
    folder = tmp_path / "dir-not-file"
    folder.mkdir()
    assert config.get_api_key({"api_keys": {"x": str(folder)}}, "x") is None


def test_get_api_key_when_key_file_has_unicode_and_whitespace_strips(isolated_home):
    path = isolated_home / "key"
    path.write_text("\n  klucz-ż  \n", encoding="utf-8")
    assert config.get_api_key({"api_keys": {"x": "~/key"}}, "x") == "klucz-ż"


def test_child_environment_when_aliases_and_missing_keys(monkeypatch):
    monkeypatch.setenv("G", "g")
    env = config.child_environment({"api_keys": {"gemini": "env:G", "mistralai": "env:NOPE"}})
    assert env == {"GOOGLE_API_KEY": "g"}


def test_save_default_config_when_path_given_writes_template_without_keys(tmp_path):
    path = tmp_path / "c.json"
    assert config.save_default_config(str(path)) is True
    data = json.loads(path.read_text())
    assert data["api_keys"]["openai"] == "env:OPENAI_API_KEY" and data["timeout_seconds"] == 30


def test_save_default_config_when_unwritable_returns_false(tmp_path):
    assert config.save_default_config(str(tmp_path / "missing-dir" / "c.json")) is False


def test_save_default_config_when_no_path_targets_package_parent_not_checkout(monkeypatch, tmp_path):
    fake_pkg = tmp_path / "site" / "fontlab_aidus_agentus.plugin"
    fake_pkg.mkdir(parents=True)
    monkeypatch.setattr(config, "__file__", str(fake_pkg / "config.py"))
    assert config.save_default_config() is True
    assert (tmp_path / "site" / "aidus_config.json").is_file()


def test_first_run_when_core_path_lacks_launcher_reports_issue(monkeypatch, tmp_path):
    monkeypatch.setattr(config, "load_config", lambda: {"core_path": str(tmp_path)})
    status = config.check_first_run_setup()
    assert status["ready"] is False and "boot.py not found" in status["issues"][0]
    message = config.get_first_run_message()
    assert "needs setup" in message and "AIDUS_PYTHON" in message


def test_first_run_when_installed_launcher_present_is_ready():
    assert config.check_first_run_setup()["ready"] is True
    assert config.get_first_run_message() is None


def test_load_config_when_explicit_path_is_only_candidate(monkeypatch, tmp_path):
    path = tmp_path / "only.json"
    path.write_text('{"timeout_seconds": 9}', encoding="utf-8")
    monkeypatch.setenv("AIDUS_CONFIG", str(path))
    assert config._find_config_paths() == [str(path)]
    assert config.load_config()["timeout_seconds"] == 9


def test_load_config_when_home_config_present_is_used(isolated_home):
    target = isolated_home / ".config" / "aidus_agentus" / "config.json"
    target.parent.mkdir(parents=True)
    target.write_text('{"python_exe": "/x/python"}', encoding="utf-8")
    loaded = config.load_config()
    assert loaded["python_exe"] == "/x/python" and loaded["_loaded_from"] == str(target)


def test_load_config_when_file_unreadable_reports_and_falls_back(monkeypatch, tmp_path, capsys):
    unreadable = tmp_path / "locked.json"
    unreadable.write_text("{}")
    unreadable.chmod(0)
    try:
        monkeypatch.setattr(config, "_find_config_paths", lambda: [str(unreadable)])
        assert config.load_config()["timeout_seconds"] == 30
        assert "unreadable" in capsys.readouterr().out
    finally:
        unreadable.chmod(0o644)


def test_glyph_tools_when_current_glyph_is_fgglyph_use_flglyph_wrapper(ex, monkeypatch):
    """FontLab 9's CurrentGlyph() returns an fgGlyph (has width, no sidebearings);
    native run 2026-10-16 failed with "'fgGlyph' object has no attribute 'lsb'"."""
    fg_glyph = SimpleNamespace(name="A", width=640, unicode=65)
    font = object()
    native = NativeGlyph()
    wrapped = []

    def fl_glyph(glyph, package):
        wrapped.append((glyph, package))
        return native

    monkeypatch.setattr(executor_module, "FL_AVAILABLE", True)
    monkeypatch.setattr(executor_module, "fl", SimpleNamespace(
        CurrentFont=lambda: font, CurrentGlyph=lambda: fg_glyph, flGlyph=fl_glyph,
        flWorkspace=SimpleNamespace(instance=lambda: SimpleNamespace(
            findPackageId=lambda identity: native.package))))
    info = ex.run("get_current_glyph_info")
    assert info["width"] == 500 and info["lsb"] == 40 and info["unicode"] == 0x104
    assert wrapped[0] == (fg_glyph, font)
    result = ex.run("set_glyph_metrics", {"width": 520, "lsb": 30})
    assert result["success"] and native.advanceWidth == 520 and native._lsb == 30
    assert ex.run("run_fontlab_script", {"code": "result = glyph.name"})["result"] == "A"


@pytest.mark.parametrize("timeout", [30, 0])
def test_script_when_finished_restores_previous_trace_function(ex, timeout):
    """The timeout guard must not silence a debugger or coverage tracer already installed."""
    def outer_tracer(frame, event, arg):
        return None

    previous = sys.gettrace()
    sys.settrace(outer_tracer)
    ex.set_timeout(timeout)
    try:
        ex.run("run_fontlab_script", {"code": "result = 1"})
        after = sys.gettrace()
    finally:
        sys.settrace(previous)
    assert after is outer_tracer


class Items:
    def __init__(self):
        self.calls = []

    def notifyChangesApplied(self, name, objects):
        self.calls.append((name, list(objects)))


def _fontlab_with_items(glyph):
    items = Items()
    return items, SimpleNamespace(CurrentFont=lambda: object(), CurrentGlyph=lambda: glyph,
                                  flItems=lambda: items)


def test_native_metrics_when_changed_add_one_undo_step_with_layer_then_glyph(ex, monkeypatch):
    glyph = NativeGlyph()
    items, fake = _fontlab_with_items(glyph)
    monkeypatch.setattr(executor_module, "FL_AVAILABLE", True)
    monkeypatch.setattr(executor_module, "fl", fake)
    widths = []
    items.notifyChangesApplied = lambda name, objects: (
        items.calls.append((name, list(objects))), widths.append(glyph.advanceWidth))
    assert ex.run("set_glyph_metrics", {"width": 520, "rsb": 70})["success"]
    # Native fact (glyport probe_undo_first_edit): FontLab stores an object's state at each
    # notification and Undo restores the previous stored one, so the pre-change state is
    # notified first, then the result. AGENTS.md: layers first, then the glyph, one list.
    assert widths == [500, 520], "pre-change state, then the edited state"
    assert all(objects == [glyph.activeLayer, glyph] for _, objects in items.calls)
    assert all("metrics" in name.lower() for name, _ in items.calls)


def test_native_metrics_when_partially_applied_still_notify_the_applied_part(ex, monkeypatch):
    glyph = NativeGlyph(setters_ok=False)
    items, fake = _fontlab_with_items(glyph)
    monkeypatch.setattr(executor_module, "FL_AVAILABLE", True)
    monkeypatch.setattr(executor_module, "fl", fake)
    assert ex.run("set_glyph_metrics", {"width": 520, "lsb": 5})["error"]
    assert len(items.calls) == 2, "The width change is undoable even though LSB failed"


def test_native_metrics_when_nothing_requested_send_no_notification(ex, monkeypatch):
    glyph = NativeGlyph()
    items, fake = _fontlab_with_items(glyph)
    monkeypatch.setattr(executor_module, "FL_AVAILABLE", True)
    monkeypatch.setattr(executor_module, "fl", fake)
    assert ex.run("set_glyph_metrics", {})["success"]
    assert items.calls == []


@pytest.mark.parametrize("request_", [{"width": 500}, {"lsb": 40, "rsb": 60}, {"width": 500, "lsb": 40.0000001}])
def test_native_metrics_when_values_already_match_add_no_undo_step(ex, monkeypatch, request_):
    glyph = NativeGlyph(setters_ok=False)  # FontLab's setters report False for no-ops
    items, fake = _fontlab_with_items(glyph)
    monkeypatch.setattr(executor_module, "FL_AVAILABLE", True)
    monkeypatch.setattr(executor_module, "fl", fake)
    assert ex.run("set_glyph_metrics", request_)["success"]
    assert items.calls == [], "Nothing changed, so no Undo entry"


def test_native_metrics_when_one_value_differs_still_add_the_step(ex, monkeypatch):
    glyph = NativeGlyph()
    items, fake = _fontlab_with_items(glyph)
    monkeypatch.setattr(executor_module, "FL_AVAILABLE", True)
    monkeypatch.setattr(executor_module, "fl", fake)
    assert ex.run("set_glyph_metrics", {"width": 500, "lsb": 41})["success"]
    assert len(items.calls) == 2 and glyph._lsb == 41


TIGHT_LOOP_PROBE = """
import json, sys, time
from fontlab_aidus_agentus.plugin.executor import FontLabExecutor
ex = FontLabExecutor()
ex.set_timeout(0.2)
start = time.monotonic()
result = ex.run("run_fontlab_script", {"code": sys.argv[1]})
print(json.dumps({"elapsed": time.monotonic() - start, "result": result, "trace": sys.gettrace() is None}))
"""


@pytest.mark.parametrize("code", ["while True: pass", "while True:\n    pass", "x = 0\nwhile True: x += 1",
                                  "def spin():\n    while True: pass\nspin()"])
def test_script_when_tight_loop_runs_forever_timeout_still_fires(code, tmp_path):
    """X5 P2: on CPython 3.11 a one-line loop produced no line events and ran past the
    timeout; run in a child bounded by an outer 20 s deadline on whichever Python runs the suite."""
    import subprocess

    root = Path(executor_module.__file__).resolve().parents[2]
    completed = subprocess.run([sys.executable, "-c", TIGHT_LOOP_PROBE, code], capture_output=True, text=True,
                               timeout=20, cwd=tmp_path, env={**os.environ, "PYTHONPATH": str(root)})
    assert completed.returncode == 0, completed.stderr[-2000:]
    report = json.loads(completed.stdout.strip().splitlines()[-1])
    assert report["result"]["error"] == "Script error"
    assert any("timed out" in line for line in report["result"]["traceback"])
    assert report["elapsed"] < 5 and report["trace"] is True
