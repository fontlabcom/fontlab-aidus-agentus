# this_file: src/fontlab_aidus_agentus/launchers.py
"""Lazy Scripts-menu actions; Qt runs work after the FontLab script returns."""

from collections.abc import Callable
from pathlib import Path

_timers: list = []  # Retain PythonQt objects until their callbacks have run.


def _defer(action: Callable[[], None]) -> None:
    """Queue on the host UI thread without importing the plugin or AI brain."""
    try:
        import fontlab  # noqa: F401
        from PythonQt.QtCore import QTimer
    except ImportError:
        print("[Aidus Agentus] Run this script inside FontLab 9 (PythonQt required).")
        return

    timer = QTimer()

    def invoke() -> None:
        try:
            action()
        except ImportError:
            print(
                "[Aidus Agentus] Missing dependency. Install the current fontlab-aidus-agentus "
                "host package; MCP also needs fontlab-remopy in FontLab."
            )
            _print_help("installation.md")
        except Exception as error:  # noqa: BLE001 - UI callback must report safely.
            print(
                f"[Aidus Agentus] Action failed ({type(error).__name__}). "
                "Check python_exe and configuration."
            )
            _print_help("configure.md", "guides/troubleshooting.md")
        finally:
            _timers.remove(timer)
            timer.deleteLater()

    timer.setSingleShot(True)
    timer.timeout.connect(invoke)
    _timers.append(timer)
    timer.start(0)



def _print_help(*names: str) -> None:
    """Print readable authored help from a wheel or the canonical src-layout checkout."""
    package = Path(__file__).resolve().parent
    root = package / "_help"
    if not root.is_dir():
        root = package.parents[1] / "src_docs" / "md"
    paths = [root / name for name in names]
    try:
        readable = all(path.read_text(encoding="utf-8").strip() for path in paths)
    except (OSError, UnicodeError):
        readable = False
    if readable:
        for path in paths:
            print(f"[Aidus Agentus] Help: {path}")
    else:
        print(
            "[Aidus Agentus] Local help unavailable. Reinstall the current "
            "fontlab-aidus-agentus host package in FontLab's Python path; "
            "keep the AI brain in a separate Python 3.13+ environment."
        )


def start() -> None:
    """Return promptly, then open or show the embedded Aidus Agentus dock."""
    _defer(_start)


def _start() -> None:
    from fontlab_aidus_agentus.plugin import main

    dock = main.get_dock()
    if dock is not None:
        dock.show()
    else:
        main.run()


def enable_mcp() -> None:
    """Defer native MCP activation to the installed Remopy host helper."""
    _defer(_enable_mcp)


def _enable_mcp() -> None:
    from fontlab_remopy import enable_mcp as enable

    enable()
    print("[Aidus Agentus] FontLab MCP enabled. Reconnect Aidus Agentus to discover tools.")


def open_configuration() -> None:
    """Defer opening the active host JSON file in the system's default editor."""
    _defer(_open_configuration)


def _open_configuration() -> None:
    import json
    import os
    from pathlib import Path

    from PythonQt.QtCore import QUrl
    from PythonQt.QtGui import QDesktopServices

    from fontlab_aidus_agentus.plugin.config import _find_config_paths, load_config

    loaded = load_config().get("_loaded_from")
    existing = next((p for p in _find_config_paths() if Path(p).exists()), None)
    default = Path.home() / ".config" / "aidus_agentus" / "config.json"
    path = (
        Path(loaded or existing or os.environ.get("AIDUS_CONFIG") or default)
        .expanduser()
        .absolute()
    )
    path.parent.mkdir(parents=True, exist_ok=True)
    try:
        with path.open("x", encoding="utf-8") as stream:
            json.dump({"python_exe": None, "api_keys": {}}, stream, indent=2)
            stream.write("\n")
    except FileExistsError:
        pass  # Preserve user edits, even when the existing JSON is invalid.
    print(f"[Aidus Agentus] Configuration: {path}")
    if not QDesktopServices.openUrl(QUrl.fromLocalFile(str(path))):
        print(
            "[Aidus Agentus] Open this file in a text editor, then save and restart Aidus Agentus."
        )
