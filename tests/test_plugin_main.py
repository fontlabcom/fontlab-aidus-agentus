# this_file: tests/test_plugin_main.py
"""Plugin boot (fontlab_aidus_agentus.plugin.main/__init__) and the fontlab_aidus_agentus facade, host-side."""

import importlib
import importlib.metadata
import os
import runpy
import stat
import sys
from types import ModuleType, SimpleNamespace

import pytest

import fontlab_aidus_agentus.plugin
import fontlab_aidus_agentus
from fontlab_aidus_agentus.plugin import main


def _executable(path):
    path.write_text("#!/bin/sh\n")
    path.chmod(path.stat().st_mode | stat.S_IXUSR)
    return str(path)


# --- _resolve_paths -------------------------------------------------------


def test_resolve_paths_when_env_python_uses_installed_launcher(monkeypatch, tmp_path):
    monkeypatch.setenv("AIDUS_PYTHON", "~/brain/bin/python")
    python, boot, core = main._resolve_paths()
    assert python == os.path.expanduser("~/brain/bin/python")
    assert boot == os.path.join(os.path.dirname(fontlab_aidus_agentus.__file__), "core_launcher.py")
    assert core == os.path.dirname(fontlab_aidus_agentus.__file__)


def test_resolve_paths_when_config_names_python_and_legacy_core(monkeypatch, tmp_path):
    core = tmp_path / "legacy core"
    core.mkdir()
    monkeypatch.setattr(
        "fontlab_aidus_agentus.plugin.config.load_config",
        lambda: {"python_exe": "/opt/py", "core_path": str(core)},
    )
    python, boot, core_dir = main._resolve_paths()
    assert python == "/opt/py" and core_dir == str(core)
    assert boot == os.path.join(str(core), "boot.py"), "Without core_launcher.py fall back to boot.py"


def test_resolve_paths_when_env_beats_config(monkeypatch):
    monkeypatch.setenv("AIDUS_PYTHON", "/env/python")
    monkeypatch.setattr("fontlab_aidus_agentus.plugin.config.load_config", lambda: {"python_exe": "/cfg/python"})
    assert main._resolve_paths()[0] == "/env/python"


def test_resolve_paths_when_only_path_helper_exists_uses_it(monkeypatch):
    monkeypatch.setattr("shutil.which", lambda name: "/usr/local/bin/" + name)
    assert main._resolve_paths()[0] == "/usr/local/bin/fontlab-aidus-python"


def test_resolve_paths_when_nothing_configured_raises_with_guidance(monkeypatch):
    monkeypatch.setattr("shutil.which", lambda name: None)
    with pytest.raises(RuntimeError, match="AIDUS_PYTHON or python_exe"):
        main._resolve_paths()


# --- bootstrap/run/shutdown with fakes ------------------------------------


class Recorder:
    instances = []

    def __init__(self, **kwargs):
        self.kwargs = kwargs
        self.calls = []
        Recorder.instances.append(self)


@pytest.fixture
def fake_parts(monkeypatch, tmp_path):
    """Replace transport/client/executor/dock with recorders; keep config real."""
    created = {}

    class Signal:
        def __init__(self):
            self.slots = []

        def connect(self, slot):
            self.slots.append(slot)

        def disconnect(self, slot):
            self.slots.remove(slot)

        def emit(self, *args):
            for slot in list(self.slots):
                slot(*args)

    class Transport(Recorder):
        start_result = (True, None)

        def __init__(self, **kwargs):
            super().__init__(**kwargs)
            self.stderrReceived, self.processFinished, self.processError = Signal(), Signal(), Signal()

        def start(self):
            self.calls.append("start")
            return Transport.start_result

        def stop(self):
            self.calls.append("stop")

    class Client(Recorder):
        initialize_result = True

        def __init__(self, transport, executor):
            super().__init__(transport=transport, executor=executor)
            self._transport = transport

        def initialize(self):
            self.calls.append("initialize")
            return Client.initialize_result

        def cleanup(self):
            self.calls.append("cleanup")

    class Dock(Recorder):
        def __init__(self, client):
            super().__init__(client=client)
            self.errors = []

        def show_error(self, message):
            self.errors.append(message)

        def get_client(self):
            return self.kwargs["client"]

        def close(self):
            self.calls.append("close")

        def deleteLater(self):
            self.calls.append("deleteLater")

        def show(self):
            self.calls.append("show")

    class Executor(Recorder):
        pass

    for module, name, cls in (
        ("fontlab_aidus_agentus.plugin.transport", "ACPTransport", Transport),
        ("fontlab_aidus_agentus.plugin.client", "AidusAgentusClient", Client),
        ("fontlab_aidus_agentus.plugin.executor", "FontLabExecutor", Executor),
        ("fontlab_aidus_agentus.plugin.ui", "AidusAgentusDock", Dock),
    ):
        monkeypatch.setattr(importlib.import_module(module), name, cls)
        created[name] = cls
    brain = _executable(tmp_path / "python")
    monkeypatch.setenv("AIDUS_PYTHON", brain)
    monkeypatch.setattr(main, "_dock", None)
    return SimpleNamespace(**created, python=brain)


def test_bootstrap_when_healthy_starts_transport_and_initializes(fake_parts, monkeypatch):
    dock = main.bootstrap()
    client = dock.get_client()
    transport = client._transport
    assert transport.calls == ["start"] and client.calls == ["initialize"]
    assert transport.kwargs["python_exe"] == fake_parts.python
    assert transport.kwargs["timeout_seconds"] == 30
    assert dock.errors == [] and main.get_dock() is dock


def test_bootstrap_when_transport_fails_reports_and_skips_initialize(fake_parts):
    fake_parts.ACPTransport.start_result = (False, "boom")
    try:
        dock = main.bootstrap()
    finally:
        fake_parts.ACPTransport.start_result = (True, None)
    assert dock.errors == ["Failed to start Core: boom"]
    assert dock.get_client().calls == []


def test_bootstrap_when_initialize_fails_reports(fake_parts):
    fake_parts.AidusAgentusClient.initialize_result = False
    try:
        dock = main.bootstrap()
    finally:
        fake_parts.AidusAgentusClient.initialize_result = True
    assert dock.errors == ["Failed to initialize ACP client"]


def test_bootstrap_when_first_run_incomplete_shows_message_and_does_not_start(fake_parts, monkeypatch):
    monkeypatch.setattr("fontlab_aidus_agentus.plugin.config.get_first_run_message", lambda: "setup needed")
    dock = main.bootstrap()
    assert dock.errors == ["setup needed"]
    assert dock.get_client()._transport.calls == []


def test_bootstrap_when_api_keys_configured_passes_child_environment_only(fake_parts, monkeypatch, isolated_home):
    key = isolated_home / "openai.txt"
    key.write_text(" synthetic \n")
    monkeypatch.setattr(
        "fontlab_aidus_agentus.plugin.config.load_config",
        lambda: {"api_keys": {"openai": str(key), "mistralai": "env:SYNTH_M"}, "timeout_seconds": 7},
    )
    monkeypatch.setenv("SYNTH_M", "m-value")
    dock = main.bootstrap()
    transport = dock.get_client()._transport
    assert transport.kwargs["environment"] == {"OPENAI_API_KEY": "synthetic", "MISTRAL_API_KEY": "m-value"}
    assert transport.kwargs["timeout_seconds"] == 7
    assert "OPENAI_API_KEY" not in os.environ


def test_run_when_fontlab_missing_prints_standalone(monkeypatch, capsys):
    monkeypatch.setattr(main, "FL_AVAILABLE", False)
    main.run()
    assert "standalone mode" in capsys.readouterr().out


def _fake_fontlab(window):
    workspace = SimpleNamespace(instance=lambda: SimpleNamespace(mainWindow=window))
    return SimpleNamespace(flWorkspace=workspace)


def _install_qtcore(monkeypatch):
    core = ModuleType("PythonQt.QtCore")
    core.Qt = SimpleNamespace(LeftDockWidgetArea=1)
    package = ModuleType("PythonQt")
    package.QtCore = core
    monkeypatch.setitem(sys.modules, "PythonQt", package)
    monkeypatch.setitem(sys.modules, "PythonQt.QtCore", core)


def test_run_when_in_fontlab_docks_widget_left(fake_parts, monkeypatch, capsys):
    added = []
    window = SimpleNamespace(addDockWidget=lambda area, dock: added.append((area, dock)))
    monkeypatch.setattr(main, "FL_AVAILABLE", True)
    monkeypatch.setattr(main, "fl", _fake_fontlab(window))
    _install_qtcore(monkeypatch)
    main.run()
    assert added == [(1, main.get_dock())]
    assert "Plugin loaded successfully" in capsys.readouterr().out


def test_run_when_docking_fails_reports(fake_parts, monkeypatch, capsys):
    def refuse(area, dock):
        raise RuntimeError("no window")

    monkeypatch.setattr(main, "FL_AVAILABLE", True)
    monkeypatch.setattr(main, "fl", _fake_fontlab(SimpleNamespace(addDockWidget=refuse)))
    _install_qtcore(monkeypatch)
    main.run()
    assert "Failed to register dock: no window" in capsys.readouterr().out


def test_run_when_bootstrap_returns_none_reports(monkeypatch, capsys):
    monkeypatch.setattr(main, "FL_AVAILABLE", True)
    monkeypatch.setattr(main, "bootstrap", lambda: None)
    main.run()
    assert "Failed to bootstrap" in capsys.readouterr().out


def test_shutdown_when_dock_open_stops_child_and_deletes_dock(fake_parts):
    dock = main.bootstrap()
    client = dock.get_client()
    main.shutdown()
    assert client._transport.calls == ["start", "stop"]
    assert client.calls[-1] == "cleanup"
    assert dock.calls == ["close", "deleteLater"] and main.get_dock() is None
    main.shutdown()  # idempotent


def test_shutdown_when_dock_has_no_client_still_closes(monkeypatch):
    dock = SimpleNamespace(get_client=lambda: None, close=lambda: None, deleteLater=lambda: None)
    monkeypatch.setattr(main, "_dock", dock)
    main.shutdown()
    assert main.get_dock() is None


@pytest.mark.filterwarnings("ignore:.*found in sys.modules:RuntimeWarning")
def test_main_module_when_run_outside_fontlab_reports_bootstrap(monkeypatch, capsys, fake_parts):
    monkeypatch.setitem(sys.modules, "fontlab", None)
    runpy.run_module("fontlab_aidus_agentus.plugin.main", run_name="__main__")
    out = capsys.readouterr().out
    assert "Running in test mode" in out and "Bootstrap completed successfully" in out


# --- src/fontlab_aidus_agentus/plugin/__init__ -------------------------------------------


@pytest.mark.parametrize(
    "text,expected",
    [("1.2.3", (1, 2, 3)), ("2", (2, 0, 0)), ("1.4", (1, 4, 0)), ("1.0.2-rc1", (1, 0, 2)),
     ("", (0, 0, 0)), ("x.y", (0, 0, 0)), (None, (0, 0, 0))],
)
def test_parse_version_when_varied_input(text, expected):
    assert fontlab_aidus_agentus.plugin.parse_version(text) == expected


@pytest.mark.parametrize("core,ok", [("1.0.2", True), ("1.9.0", True), ("2.0.0", False), ("0.9.0", False), ("garbage", False)])
def test_is_compatible_when_core_version_varies(core, ok):
    assert fontlab_aidus_agentus.plugin.is_compatible(core) is ok


@pytest.mark.parametrize("name", ["bootstrap", "run", "shutdown"])
def test_package_entrypoints_when_main_missing_raise_import_error(monkeypatch, name):
    monkeypatch.setattr(fontlab_aidus_agentus.plugin, "_%s_fn" % name, None)
    with pytest.raises(ImportError, match="loaded from FontLab"):
        getattr(fontlab_aidus_agentus.plugin, name)()


@pytest.mark.parametrize("name", ["bootstrap", "run", "shutdown"])
def test_package_entrypoints_when_main_present_delegate(monkeypatch, name):
    calls = []
    monkeypatch.setattr(fontlab_aidus_agentus.plugin, "_%s_fn" % name, lambda: calls.append(name) or "result")
    result = getattr(fontlab_aidus_agentus.plugin, name)()
    assert calls == [name] and (result == "result" if name == "bootstrap" else result is None)


# --- fontlab_aidus_agentus facade --------------------------------------------


def test_facade_run_and_shutdown_when_called_delegate_to_plugin(monkeypatch):
    calls = []
    monkeypatch.setattr(main, "run", lambda: calls.append("run"))
    monkeypatch.setattr(main, "shutdown", lambda: calls.append("shutdown"))
    fontlab_aidus_agentus.run()
    fontlab_aidus_agentus.shutdown()
    assert calls == ["run", "shutdown"]


def test_facade_version_when_distribution_missing_is_unknown(monkeypatch):
    def missing(name):
        raise importlib.metadata.PackageNotFoundError(name)

    monkeypatch.setattr(importlib.metadata, "version", missing)
    fresh = importlib.reload(fontlab_aidus_agentus)
    try:
        assert fresh.__version__ == "0+unknown"
    finally:
        monkeypatch.undo()
        importlib.reload(fontlab_aidus_agentus)


def test_brain_boot_when_host_python_refuses_with_guidance(monkeypatch, capsys):
    from fontlab_aidus_agentus import boot

    monkeypatch.setattr(sys, "version_info", (3, 11, 6))
    assert boot.main() == 1
    assert "external Python 3.13+" in capsys.readouterr().err


def test_brain_boot_when_brain_extra_missing_explains(monkeypatch, capsys):
    from fontlab_aidus_agentus import boot

    monkeypatch.setattr(sys, "version_info", (3, 13, 0))
    monkeypatch.setitem(sys.modules, "fontlab_aidus_agentus.core.boot", None)
    assert boot.main() == 1
    assert "fontlab-aidus-agentus[brain]" in capsys.readouterr().err


def test_brain_boot_when_available_returns_core_exit_code(monkeypatch):
    from fontlab_aidus_agentus import boot

    fake = ModuleType("fontlab_aidus_agentus.core.boot")
    fake.main = lambda: 7
    monkeypatch.setattr(sys, "version_info", (3, 13, 0))
    monkeypatch.setitem(sys.modules, "fontlab_aidus_agentus.core.boot", fake)
    assert boot.main() == 7


def test_core_launcher_when_executed_exits_with_boot_status(monkeypatch):
    from fontlab_aidus_agentus import boot

    monkeypatch.setattr(boot, "main", lambda: 5)
    with pytest.raises(SystemExit) as stop:
        runpy.run_module("fontlab_aidus_agentus.core_launcher", run_name="__main__")
    assert stop.value.code == 5


# --- brain stderr wiring --------------------------------------------------


def test_bootstrap_when_brain_logs_error_prints_it_to_output(fake_parts, capsys):
    transport = main.bootstrap().get_client()._transport
    transport.stderrReceived.emit('{"level": "info", "event": "quiet"}\n{"level": "error", "event": "loud"}\n')
    out = capsys.readouterr().out
    assert "[Aidus brain]" in out and "loud" in out and "quiet" not in out


def test_bootstrap_when_brain_exits_nonzero_shows_bounded_tail_in_dock(fake_parts):
    dock = main.bootstrap()
    transport = dock.get_client()._transport
    transport.stderrReceived.emit("".join("line %d\n" % i for i in range(30)) + "Fatal: " + "z" * 5000 + "\n")
    transport.processFinished.emit(1)
    message = dock.errors[-1]
    assert message.startswith("Brain exited with code 1") and "line 29" in message and "line 20" not in message
    assert len(message) < 2000, "The dock shows a bounded tail"


def test_bootstrap_when_brain_exits_cleanly_shows_nothing(fake_parts):
    dock = main.bootstrap()
    transport = dock.get_client()._transport
    transport.stderrReceived.emit("bye\n")
    transport.processFinished.emit(0)
    assert dock.errors == []


def test_bootstrap_when_transport_error_shows_recent_brain_lines(fake_parts):
    dock = main.bootstrap()
    transport = dock.get_client()._transport
    transport.stderrReceived.emit("ImportError: agentpool\n")
    transport.processError.emit("Process error: Crashed")
    assert "ImportError: agentpool" in dock.errors[-1]
    transport.processError.emit("again")
    assert len(dock.errors) == 2


def test_shutdown_when_called_disconnects_brain_log_slots(fake_parts):
    transport = main.bootstrap().get_client()._transport
    main.shutdown()
    assert transport.stderrReceived.slots == [] and transport.processFinished.slots == []
    assert transport.processError.slots == []


def test_bootstrap_when_brain_dies_mid_line_shows_the_unterminated_text(fake_parts):
    dock = main.bootstrap()
    transport = dock.get_client()._transport
    transport.stderrReceived.emit("Fatal: missing dependency")
    transport.processFinished.emit(1)
    assert "Fatal: missing dependency" in dock.errors[-1]


def test_bootstrap_when_second_child_fails_silently_does_not_reuse_first_output(fake_parts):
    dock = main.bootstrap()
    transport = dock.get_client()._transport
    transport.stderrReceived.emit("first child trouble\n")
    transport.processFinished.emit(1)
    transport.processFinished.emit(2)
    assert dock.errors[-1] == "Brain exited with code 2."


def test_shutdown_when_stop_uncertain_retains_dock_and_client(fake_parts, monkeypatch):
    dock = main.bootstrap()
    client = dock.get_client()
    monkeypatch.setattr(client._transport, "stop", lambda: False)
    main.shutdown()
    assert main.get_dock() is dock
    assert "cleanup" not in client.calls
    assert "deleteLater" not in dock.calls
