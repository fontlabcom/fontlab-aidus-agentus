# this_file: tests/test_scripts_menu.py
"""Scripts-menu launchers work without FontLab or AI imports on the run path."""

import builtins
import importlib.util
import json
import os
import py_compile
import runpy
import shutil
import subprocess
import sys
from pathlib import Path
from types import ModuleType, SimpleNamespace
from unittest.mock import Mock

import pytest

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "Scripts" / "Aidus Agentus"
ACTIONS = {
    "Start Aidus Agentus.py": "start",
    "Enable FontLab MCP.py": "enable_mcp",
    "Open Configuration.py": "open_configuration",
}


# FontLab compiles menu scripts in place (`Start Aidus Agentus.pyc`); git ignores them.
HOST_ARTIFACTS = ("*.pyc", "__pycache__", ".DS_Store")


def menu_entries(folder):
    """Menu folder entries, ignoring what FontLab or macOS leaves beside the scripts."""
    return {p.name for p in folder.iterdir() if not any(p.match(g) for g in HOST_ARTIFACTS)}


def test_menu_entries_when_host_artifacts_present_ignores_them(tmp_path):
    for name in ("Start Aidus Agentus.py", "README.md"):
        (tmp_path / name).write_text("")
    (tmp_path / "Start Aidus Agentus.pyc").write_bytes(b"\x00")
    (tmp_path / "__pycache__").mkdir()
    (tmp_path / ".DS_Store").write_bytes(b"")
    (tmp_path / "Extra.py").write_text("")
    assert menu_entries(tmp_path) == {"Start Aidus Agentus.py", "README.md", "Extra.py"}, (
        "Compiled caches are ignored; a real extra script is still reported"
    )


def test_scripts_folder_when_listed_contains_only_user_entrypoints_and_readme():
    assert menu_entries(SCRIPTS) == {*ACTIONS, "README.md"}
    assert not SCRIPTS.is_symlink(), "The orchestrator owns symlink creation"


@pytest.mark.parametrize("filename,action", ACTIONS.items())
def test_script_when_compiled_and_imported_is_small_and_calls_installed_package(
    filename, action, monkeypatch, tmp_path
):
    path = SCRIPTS / filename
    source = path.read_text()
    assert len(source.splitlines()) <= 20, "Menu scripts must remain thin"
    assert len(source.encode()) <= 1024, "Keep implementation in installed packages"
    py_compile.compile(str(path), cfile=str(tmp_path / "script.pyc"), doraise=True)
    package = ModuleType("fontlab_aidus_agentus.launchers")
    target = Mock()
    setattr(package, action, target)
    monkeypatch.setitem(sys.modules, "fontlab_aidus_agentus.launchers", package)
    monkeypatch.setitem(sys.modules, "fontlab", ModuleType("fontlab"))
    monkeypatch.setitem(sys.modules, "PythonQt", ModuleType("PythonQt"))
    monkeypatch.setattr(sys, "dont_write_bytecode", True)
    spec = importlib.util.spec_from_file_location("menu_script", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    target.assert_called_once_with()


@pytest.mark.parametrize("filename", ACTIONS)
def test_script_when_package_missing_prints_install_guidance(
    filename, monkeypatch, capsys
):
    monkeypatch.setitem(sys.modules, "fontlab_aidus_agentus", None)
    monkeypatch.setitem(sys.modules, "fontlab_aidus_agentus.launchers", None)
    runpy.run_path(str(SCRIPTS / filename))
    output = capsys.readouterr().out
    assert "fontlab-aidus-agentus" in output and "install" in output.lower()
    assert "FontLab's Python path" in output
    assert "separate" in output and "brain" in output
    assert "repository access required" in output
    assert "https://github.com/fontlabcom/fontlab-aidus-agentus/blob/main/README.md" in output


@pytest.fixture
def host(monkeypatch):
    """Capture Qt callbacks rather than executing them during a script run."""
    timer = Mock()
    qt_core = ModuleType("PythonQt.QtCore")
    qt_core.QTimer = Mock(return_value=timer)
    qt_core.QUrl = SimpleNamespace(fromLocalFile=lambda path: ("local", path))
    desktop = Mock()
    qt_gui = ModuleType("PythonQt.QtGui")
    qt_gui.QDesktopServices = desktop
    monkeypatch.setitem(sys.modules, "fontlab", ModuleType("fontlab"))
    monkeypatch.setitem(sys.modules, "PythonQt", ModuleType("PythonQt"))
    monkeypatch.setitem(sys.modules, "PythonQt.QtCore", qt_core)
    monkeypatch.setitem(sys.modules, "PythonQt.QtGui", qt_gui)
    return SimpleNamespace(timer=timer, desktop=desktop)


def test_launchers_when_cold_run_defer_all_work_within_five_seconds():
    code = """
import builtins, pathlib, runpy, sys, types
from unittest.mock import Mock
original_import = builtins.__import__
def guarded(name, *args, **kwargs):
    assert not name.startswith(('fontlab_aidus_agentus.plugin', 'fontlab_aidus_agentus.core', 'agentpool', 'fontlab_remopy')), name
    return original_import(name, *args, **kwargs)
builtins.__import__ = guarded
sys.modules['fontlab'] = types.ModuleType('fontlab')
sys.modules['PythonQt'] = types.ModuleType('PythonQt')
core = types.ModuleType('PythonQt.QtCore')
core.QTimer = Mock()
sys.modules['PythonQt.QtCore'] = core
for script in pathlib.Path('Scripts/Aidus Agentus').glob('*.py'):
    runpy.run_path(str(script))
assert core.QTimer.call_count == 3
assert core.QTimer.return_value.start.call_args.args == (0,)
"""
    result = subprocess.run(
        [sys.executable, "-S", "-B", "-c", code],
        cwd=ROOT,
        env={**os.environ, "PYTHONPATH": str(ROOT / "src")},
        capture_output=True,
        text=True,
        timeout=5,
        check=False,
    )
    assert result.returncode == 0, result.stderr


def test_start_when_scheduled_keeps_timer_alive_and_starts_only_on_callback(
    host, monkeypatch
):
    from fontlab_aidus_agentus.plugin import main
    from fontlab_aidus_agentus import launchers

    run = Mock()
    monkeypatch.setattr(main, "run", run)
    monkeypatch.setattr(main, "get_dock", lambda: None)
    launchers.start()
    run.assert_not_called()
    assert host.timer in launchers._timers
    host.timer.setSingleShot.assert_called_once_with(True)
    host.timer.start.assert_called_once_with(0)
    host.timer.timeout.connect.call_args.args[0]()
    run.assert_called_once_with()
    assert host.timer not in launchers._timers
    host.timer.deleteLater.assert_called_once_with()


def test_start_when_dock_exists_shows_it_without_starting_another_child(
    host, monkeypatch
):
    from fontlab_aidus_agentus.plugin import main
    from fontlab_aidus_agentus import launchers

    dock, run = Mock(), Mock()
    monkeypatch.setattr(main, "get_dock", lambda: dock)
    monkeypatch.setattr(main, "run", run)
    launchers.start()
    host.timer.timeout.connect.call_args.args[0]()
    dock.show.assert_called_once_with()
    run.assert_not_called()


def test_enable_when_callback_runs_delegates_to_remopy(host, monkeypatch, capsys):
    from fontlab_aidus_agentus import launchers

    enable = Mock()
    monkeypatch.setitem(
        sys.modules, "fontlab_remopy", SimpleNamespace(enable_mcp=enable)
    )
    launchers.enable_mcp()
    enable.assert_not_called()
    host.timer.timeout.connect.call_args.args[0]()
    enable.assert_called_once_with()
    assert "Reconnect" in capsys.readouterr().out


def test_enable_when_remopy_missing_prints_guidance_and_releases_timer(
    host, monkeypatch, capsys
):
    from fontlab_aidus_agentus import launchers

    monkeypatch.setitem(sys.modules, "fontlab_remopy", None)
    launchers.enable_mcp()
    host.timer.timeout.connect.call_args.args[0]()
    assert "fontlab-remopy" in capsys.readouterr().out
    assert host.timer not in launchers._timers


@pytest.mark.parametrize("existing", [None, '{"python_exe":"keep"}', "invalid json"])
def test_open_configuration_when_explicit_creates_template_or_preserves_file(
    existing, host, monkeypatch, tmp_path
):
    from fontlab_aidus_agentus import launchers

    path = tmp_path / "nested" / "config.json"
    monkeypatch.setenv("AIDUS_CONFIG", str(path))
    if existing is not None:
        path.parent.mkdir()
        path.write_text(existing)
    launchers.open_configuration()
    assert path.exists() is (existing is not None), "File I/O must be deferred"
    host.timer.timeout.connect.call_args.args[0]()
    if existing is None:
        assert json.loads(path.read_text()) == {"python_exe": None, "api_keys": {}}
    else:
        assert path.read_text() == existing, "Never overwrite user configuration"
    host.desktop.openUrl.assert_called_once_with(("local", str(path)))


INVALID_CONFIGS = [
    pytest.param(
        '{"private": "synthetic-private-value"}'.encode("utf-16"),
        "not UTF-8",
        id="utf-16",
    ),
    pytest.param(
        b'{"private": "synthetic-private-value\xff"}',
        "not UTF-8",
        id="invalid-utf-8",
    ),
    pytest.param(
        b'{"private": "synthetic-private-value"',
        "invalid JSON",
        id="malformed-json",
    ),
    pytest.param(b'["synthetic-private-value"]', "JSON object", id="non-object-json"),
]


@pytest.mark.parametrize("contents,diagnostic", INVALID_CONFIGS)
def test_open_configuration_when_invalid_reports_and_opens_unchanged_bytes(
    contents, diagnostic, host, monkeypatch, tmp_path, capsys
):
    from fontlab_aidus_agentus import launchers

    path = tmp_path / "config.json"
    path.write_bytes(contents)
    monkeypatch.setenv("AIDUS_CONFIG", str(path))
    launchers.open_configuration()
    host.timer.timeout.connect.call_args.args[0]()
    host.desktop.openUrl.assert_called_once_with(("local", str(path)))
    assert path.read_bytes() == contents, "Repair must preserve every original byte"
    assert set(tmp_path.iterdir()) == {path}, "Do not create a replacement config"
    output = capsys.readouterr().out
    assert diagnostic in output, "Explain why this configuration could not load"
    assert str(path) in output and "repair" in output.lower(), (
        "Identify the repair file"
    )
    assert "synthetic-private-value" not in output, "Never print config contents"
    assert host.timer not in launchers._timers, "Clean up the completed callback"


@pytest.mark.parametrize("contents,diagnostic", INVALID_CONFIGS)
def test_load_config_when_invalid_reports_and_uses_next_valid_file(
    contents, diagnostic, monkeypatch, tmp_path, capsys
):
    from fontlab_aidus_agentus.plugin import config

    invalid, valid = tmp_path / "invalid.json", tmp_path / "valid.json"
    invalid.write_bytes(contents)
    valid.write_text('{"timeout_seconds": 45}', encoding="utf-8")
    monkeypatch.setattr(
        config, "_find_config_paths", lambda: [str(invalid), str(valid)]
    )
    loaded = config.load_config()
    assert loaded["_loaded_from"] == str(valid), "Continue to the next valid config"
    assert loaded["timeout_seconds"] == 45, "Use the selected file's settings"
    assert invalid.read_bytes() == contents, "Loading must not alter invalid bytes"
    output = capsys.readouterr().out
    assert diagnostic in output and str(invalid) in output, "Identify the invalid file"
    assert "synthetic-private-value" not in output, (
        "Keep diagnostics free of file contents"
    )


def test_open_configuration_when_default_creates_user_file(host, monkeypatch, tmp_path):
    from fontlab_aidus_agentus.plugin import config
    from fontlab_aidus_agentus import launchers

    monkeypatch.delenv("AIDUS_CONFIG", raising=False)
    monkeypatch.setattr(Path, "home", classmethod(lambda cls: tmp_path))
    monkeypatch.setattr(config, "_find_config_paths", list)
    launchers.open_configuration()
    host.timer.timeout.connect.call_args.args[0]()
    path = tmp_path / ".config" / "aidus_agentus" / "config.json"
    assert path.is_file()
    host.desktop.openUrl.assert_called_once_with(("local", str(path)))


def test_open_configuration_when_loaded_opens_actual_file(host, monkeypatch, tmp_path):
    from fontlab_aidus_agentus.plugin import config
    from fontlab_aidus_agentus import launchers

    path = tmp_path / "aidus_config.json"
    path.write_text("{}")
    monkeypatch.setattr(config, "load_config", lambda: {"_loaded_from": str(path)})
    launchers.open_configuration()
    host.timer.timeout.connect.call_args.args[0]()
    host.desktop.openUrl.assert_called_once_with(("local", str(path)))


def test_open_configuration_when_editor_unavailable_prints_path(
    host, monkeypatch, tmp_path, capsys
):
    from fontlab_aidus_agentus import launchers

    path = tmp_path / "config.json"
    monkeypatch.setenv("AIDUS_CONFIG", str(path))
    host.desktop.openUrl.return_value = False
    launchers.open_configuration()
    host.timer.timeout.connect.call_args.args[0]()
    assert str(path) in capsys.readouterr().out


def test_deferred_action_when_it_fails_reports_type_without_secret_value(
    host, monkeypatch, capsys
):
    from fontlab_aidus_agentus.plugin import main
    from fontlab_aidus_agentus import launchers

    monkeypatch.setattr(
        main, "get_dock", Mock(side_effect=RuntimeError("synthetic-private-value"))
    )
    launchers.start()
    host.timer.timeout.connect.call_args.args[0]()
    output = capsys.readouterr().out
    assert "RuntimeError" in output
    assert str(ROOT / "src_docs/md/configure.md") in output
    assert str(ROOT / "src_docs/md/guides/troubleshooting.md") in output
    assert "synthetic-private-value" not in output
    assert host.timer not in launchers._timers


def test_launcher_when_outside_fontlab_prints_host_guidance(monkeypatch, capsys):
    from fontlab_aidus_agentus import launchers

    monkeypatch.setitem(sys.modules, "fontlab", None)
    launchers.start()
    assert "inside FontLab" in capsys.readouterr().out


@pytest.mark.parametrize("layout", ["checkout", "installed"])
@pytest.mark.parametrize("error", [ImportError, RuntimeError])
def test_deferred_error_when_outside_checkout_prints_readable_absolute_help(
    layout, error, host, monkeypatch, tmp_path, capsys
):
    from fontlab_aidus_agentus import launchers

    package = tmp_path / "distribution" / "src" / "fontlab_aidus_agentus"
    package.mkdir(parents=True)
    help_root = (package / "_help" if layout == "installed"
                 else package.parents[1] / "src_docs/md")
    shutil.copytree(ROOT / "src_docs/md", help_root)
    monkeypatch.setattr(launchers, "__file__", str(package / "launchers.py"))
    unrelated = tmp_path / "elsewhere"
    unrelated.mkdir()
    monkeypatch.chdir(unrelated)

    def fail():
        raise error("synthetic-private-value")

    original_import = builtins.__import__

    def guarded(name, *args, **kwargs):
        assert not name.startswith(("fontlab_aidus_agentus.core", "fontlab_aidus_agentus.plugin",
                                    "agentpool", "fontlab_remopy", "socket", "httpx"))
        return original_import(name, *args, **kwargs)

    monkeypatch.setattr(builtins, "__import__", guarded)
    launchers._defer(fail)
    host.timer.timeout.connect.call_args.args[0]()
    output = capsys.readouterr().out
    names = (["installation.md"] if error is ImportError
             else ["configure.md", "guides/troubleshooting.md"])
    for name in names:
        path = help_root / name
        assert str(path) in output
        assert path.is_absolute() and path.read_text(encoding="utf-8").strip()
        assert path.read_bytes() == (ROOT / "src_docs/md" / name).read_bytes()
    assert "synthetic-private-value" not in output
    assert host.timer not in launchers._timers
    host.timer.deleteLater.assert_called_once_with()
    host.desktop.openUrl.assert_not_called()


@pytest.mark.parametrize("contents", [None, b"", b"\xff"])
def test_deferred_error_when_help_unreadable_reports_reinstall_without_bad_path(
    contents, host, monkeypatch, tmp_path, capsys
):
    from fontlab_aidus_agentus import launchers

    package = tmp_path / "fontlab_aidus_agentus"
    help_root = package / "_help"
    help_root.mkdir(parents=True)
    path = help_root / "installation.md"
    if contents is not None:
        path.write_bytes(contents)
    monkeypatch.setattr(launchers, "__file__", str(package / "launchers.py"))

    def fail():
        raise ImportError("synthetic-private-value")

    launchers._defer(fail)
    host.timer.timeout.connect.call_args.args[0]()
    output = capsys.readouterr().out
    assert "Local help unavailable" in output
    assert "reinstall" in output.lower() and "fontlab-aidus-agentus" in output
    assert str(path) not in output and "synthetic-private-value" not in output
    assert host.timer not in launchers._timers
    host.timer.deleteLater.assert_called_once_with()
    host.desktop.openUrl.assert_not_called()
