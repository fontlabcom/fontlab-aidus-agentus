# this_file: tests/test_transport_process.py
"""ACPTransport process lifecycle against a scripted QProcess fake."""

import json
import stat

import pytest

from fontlab_aidus_agentus.plugin import transport as transport_module
from fontlab_aidus_agentus.plugin.transport import MAX_CHUNK_SIZE, ACPTransport, TransportState


class Signal:
    def __init__(self):
        self.slots = []

    def connect(self, slot):
        self.slots.append(slot)

    def emit(self, *args):
        for slot in list(self.slots):
            slot(*args)


class FakeProcess:
    """Scripted QProcess: records writes and honours start/finish outcomes."""

    NotRunning, SeparateChannels = 0, 0
    started_ok = True
    finishes_on_close = True
    finishes_on_terminate = True
    instances = []

    def __init__(self, parent=None):
        self.readyReadStandardOutput = Signal()
        self.readyReadStandardError = Signal()
        self.finished = Signal()
        self.errorOccurred = Signal()
        self.writes, self.calls, self.env, self.cwd = [], [], None, None
        self.stdout, self.stderr = b"", b""
        FakeProcess.instances.append(self)

    def setProcessEnvironment(self, env):
        self.env = env

    def setWorkingDirectory(self, path):
        self.cwd = path

    def setProcessChannelMode(self, mode):
        self.calls.append(("mode", mode))

    def start(self, program, args):
        self.calls.append(("start", program, list(args)))

    def waitForStarted(self, timeout):
        return FakeProcess.started_ok

    def write(self, data):
        self.writes.append(bytes(data))

    def readAllStandardOutput(self):
        data, self.stdout = self.stdout, b""
        return data

    def readAllStandardError(self):
        data, self.stderr = self.stderr, b""
        return data

    def closeWriteChannel(self):
        self.calls.append(("closeWriteChannel",))

    def waitForFinished(self, timeout):
        self.calls.append(("waitForFinished", timeout))
        last = [c[0] for c in self.calls if c[0] in ("closeWriteChannel", "terminate", "kill")][-1]
        return {"closeWriteChannel": FakeProcess.finishes_on_close,
                "terminate": FakeProcess.finishes_on_terminate, "kill": True}[last]

    def terminate(self):
        self.calls.append(("terminate",))

    def kill(self):
        self.calls.append(("kill",))


class FakeEnvironment:
    def __init__(self):
        self.values = {"PATH": "/bin"}

    @classmethod
    def systemEnvironment(cls):
        return cls()

    def insert(self, name, value):
        self.values[name] = value


class FakeTimer:
    def __init__(self, parent=None):
        self.timeout = Signal()
        self.intervals, self.stopped = [], 0

    def start(self, interval):
        self.intervals.append(interval)

    def stop(self):
        self.stopped += 1


@pytest.fixture
def qt(monkeypatch):
    FakeProcess.instances = []
    FakeProcess.started_ok = FakeProcess.finishes_on_close = FakeProcess.finishes_on_terminate = True
    monkeypatch.setattr(transport_module, "QProcess", FakeProcess)
    monkeypatch.setattr(transport_module, "QProcessEnvironment", FakeEnvironment)
    monkeypatch.setattr(transport_module, "QTimer", FakeTimer)
    return FakeProcess


@pytest.fixture
def paths(tmp_path):
    python = tmp_path / "py thon"
    python.write_text("#!/bin/sh\n")
    python.chmod(python.stat().st_mode | stat.S_IXUSR)
    boot = tmp_path / "core_launcher.py"
    boot.write_text("")
    return str(python), str(boot)


def make(paths, **kwargs):
    transport = ACPTransport(python_exe=paths[0], boot_script=paths[1], **kwargs)
    events = {"state": [], "error": [], "message": [], "stderr": [], "finished": []}
    transport.stateChanged = Signal()
    transport.processError = Signal()
    transport.messageReceived = Signal()
    transport.stderrReceived = Signal()
    transport.processFinished = Signal()
    transport.stateChanged.connect(events["state"].append)
    transport.processError.connect(events["error"].append)
    transport.messageReceived.connect(events["message"].append)
    transport.stderrReceived.connect(events["stderr"].append)
    transport.processFinished.connect(events["finished"].append)
    return transport, events


def test_start_when_paths_valid_launches_child_with_env_cwd_and_args(qt, paths, tmp_path):
    transport, events = make(paths, working_dir=tmp_path, environment={"OPENAI_API_KEY": "k"})
    assert transport.start(["--flag"]) == (True, None)
    process = qt.instances[-1]
    assert ("start", paths[0], [paths[1], "--flag"]) in process.calls
    assert process.env.values == {"PATH": "/bin", "OPENAI_API_KEY": "k"}, "Parent env preserved, key added"
    assert process.cwd == str(tmp_path)
    assert events["state"] == [TransportState.CONNECTING, TransportState.CONNECTED]
    assert transport._timeout_timer.intervals == [1000]
    assert [s.__name__ for s in process.readyReadStandardOutput.slots] == ["_on_stdout_ready"]


def test_start_when_no_environment_does_not_replace_process_env(qt, paths):
    transport, _ = make(paths)
    transport.start()
    assert qt.instances[-1].env is None and qt.instances[-1].cwd is None


def test_start_when_already_active_refuses(qt, paths):
    transport, _ = make(paths)
    transport.start()
    ok, error = transport.start()
    assert not ok and "already active" in error


@pytest.mark.parametrize("which", ["python", "boot"])
def test_start_when_path_missing_reports_error_state(qt, paths, tmp_path, which):
    python, boot = paths
    if which == "python":
        python = str(tmp_path / "missing")
    else:
        boot = str(tmp_path / "missing.py")
    transport, events = make((python, boot))
    ok, error = transport.start()
    assert not ok and "not found" in error
    assert events["state"] == [TransportState.ERROR] and events["error"] == [error]
    assert qt.instances == []


def test_validate_paths_when_directory_or_unreadable(qt, paths, tmp_path):
    transport, _ = make(paths)
    assert "not a file" in transport._validate_python_path(str(tmp_path))[1]
    plain = tmp_path / "plain"
    plain.write_text("")
    plain.chmod(0o644)
    assert "not executable" in transport._validate_python_path(str(plain))[1]
    assert "not a file" in transport._validate_boot_script(str(tmp_path))[1]
    secret = tmp_path / "secret.py"
    secret.write_text("")
    secret.chmod(0)
    try:
        assert "not readable" in transport._validate_boot_script(str(secret))[1]
    finally:
        secret.chmod(0o644)


def test_start_when_child_fails_to_start_reports(qt, paths):
    qt.started_ok = False
    transport, events = make(paths)
    ok, error = transport.start()
    assert (ok, error) == (False, "Core process failed to start")
    assert transport.state() == TransportState.ERROR


def test_stop_when_child_exits_on_eof_closes_stdin_only(qt, paths):
    transport, events = make(paths)
    transport.start()
    process = qt.instances[-1]
    transport.stop()
    names = [c[0] for c in process.calls]
    assert "closeWriteChannel" in names and "terminate" not in names and "kill" not in names
    assert transport.state() == TransportState.DISCONNECTED and transport._process is None


def test_stop_when_child_ignores_eof_terminates_then_kills(qt, paths):
    qt.finishes_on_close = qt.finishes_on_terminate = False
    transport, _ = make(paths)
    transport.start()
    process = qt.instances[-1]
    transport.stop(timeout_ms=10)
    assert [c[0] for c in process.calls if c[0] in ("closeWriteChannel", "terminate", "kill")] == [
        "closeWriteChannel", "terminate", "kill"]


def test_stop_when_not_graceful_kills_immediately(qt, paths):
    transport, _ = make(paths)
    transport.start()
    process = qt.instances[-1]
    transport.stop(graceful=False)
    assert ("kill",) in process.calls and ("closeWriteChannel",) not in process.calls


def test_stop_when_never_started_is_safe(qt, paths):
    transport, events = make(paths)
    transport.stop()
    assert transport.state() == TransportState.DISCONNECTED and events["state"] == []


def test_send_when_large_message_writes_bounded_chunks(qt, paths):
    transport, _ = make(paths)
    transport.start()
    payload = {"id": 1, "method": "session/prompt", "params": {"sessionId": "s", "text": "ą" * MAX_CHUNK_SIZE}}
    assert transport.send(payload)
    writes = qt.instances[-1].writes
    assert len(writes) > 1 and all(len(w) <= MAX_CHUNK_SIZE for w in writes)
    assert json.loads(b"".join(writes).decode("utf-8")) == payload


def test_send_when_unencodable_reports_and_returns_false(qt, paths):
    transport, events = make(paths)
    transport.start()
    assert transport.send({"id": 1, "method": "x", "params": {"bad": {1, 2}}}) is False
    assert "Failed to encode message" in events["error"][-1]


def test_send_when_not_connected_or_no_process_returns_false(qt, paths):
    transport, _ = make(paths)
    assert transport.send({"id": 1}) is False
    transport._process = FakeProcess()
    assert transport.send({"id": 1}) is False
    transport._send_chunked(b"x")  # process present but not connected: no crash
    transport._process = None
    transport._send_chunked(b"x")


def test_stdout_when_frames_split_and_blank_lines_emits_each_message(qt, paths):
    transport, events = make(paths)
    transport.start()
    process = qt.instances[-1]
    for chunk in (b'{"id": 1, "res', b'ult": {}}\n\n   \n{"method": "n"}\nnot json\n'):
        process.stdout = chunk
        transport._on_stdout_ready()
    assert events["message"] == [{"id": 1, "result": {}}, {"method": "n"}]


def test_stdout_when_qbytearray_like_uses_data(qt, paths):
    transport, events = make(paths)
    transport.start()

    class ByteArray:
        def data(self):
            return b'{"ok": true}\n'

    qt.instances[-1].readAllStandardOutput = ByteArray
    transport._on_stdout_ready()
    assert events["message"] == [{"ok": True}]


def test_stderr_when_received_is_forwarded_and_tail_flushed_on_finish(qt, paths):
    transport, events = make(paths)
    transport.start()
    process = qt.instances[-1]
    process.stderr = "warn ł".encode("utf-8")[:-1]
    transport._on_stderr_ready()
    process.finished.emit(0, 0)
    assert events["stderr"][0] == "warn "
    assert events["stderr"][-1] == "�", "A truncated tail is replaced, not dropped silently"
    assert events["finished"] == [0] and transport.state() == TransportState.DISCONNECTED


def test_stdout_and_stderr_when_no_process_or_no_data_are_ignored(qt, paths):
    transport, events = make(paths)
    transport._on_stdout_ready()
    transport._on_stderr_ready()
    transport.start()
    transport._on_stdout_ready()
    transport._on_stderr_ready()
    assert events["message"] == [] and events["stderr"] == []


@pytest.mark.parametrize("code,name", [(0, "FailedToStart"), (1, "Crashed"), (2, "Timedout"),
                                       (3, "WriteError"), (4, "ReadError"), (5, "UnknownError"), (42, "Unknown(42)")])
def test_process_error_when_signalled_sets_error_without_restart(qt, paths, code, name):
    transport, events = make(paths)
    transport.start()
    qt.instances[-1].errorOccurred.emit(code)
    assert events["error"][-1] == "Process error: %s" % name
    assert transport.state() == TransportState.ERROR
    assert len(qt.instances) == 1, "Recovery belongs to the client; no automatic restart"


def test_start_when_process_has_legacy_error_signal_connects_it(qt, paths, monkeypatch):
    class Legacy(FakeProcess):
        def __init__(self, parent=None):
            super().__init__(parent)
            del self.errorOccurred
            self.error = Signal()

    monkeypatch.setattr(transport_module, "QProcess", Legacy)
    transport, events = make(paths)
    transport.start()
    qt.instances[-1].error.emit(1)
    assert events["error"] == ["Process error: Crashed"]


def test_request_reconnect_when_called_backs_off_and_caps_attempts(qt, paths):
    transport, events = make(paths)
    transport.start()
    delays = []
    for _ in range(3):
        transport.request_reconnect()
        delays.append(transport._reconnect_timer.intervals[-1])
        transport._do_reconnect()
        assert transport.is_connected()
    assert delays == [1000, 2000, 4000]
    transport.request_reconnect()
    assert "Max reconnect attempts (3) exceeded" in events["error"][-1]
    transport.reset_reconnect_count()
    transport.request_reconnect()
    assert transport._reconnect_count == 1


def test_do_reconnect_when_not_requested_does_nothing(qt, paths):
    transport, _ = make(paths)
    transport._do_reconnect()
    assert qt.instances == []


def test_do_reconnect_when_start_fails_reports(qt, paths):
    transport, events = make(paths)
    transport.start()
    transport.request_reconnect()
    qt.started_ok = False
    transport._do_reconnect()
    assert events["error"][-1].startswith("Reconnect failed:")


def test_debug_when_enabled_uses_callback_or_print(qt, paths, capsys):
    transport, _ = make(paths)
    lines = []
    transport.enable_debug(lines.append)
    transport.start()
    assert any("Starting process" in line for line in lines)
    transport.enable_debug()
    transport.stop()
    assert "[ACPTransport]" in capsys.readouterr().out
    transport.disable_debug()
    transport._debug("silent")
    assert capsys.readouterr().out == ""


def test_set_state_when_transition_invalid_is_logged_but_applied(qt, paths):
    transport, events = make(paths)
    lines = []
    transport.enable_debug(lines.append)
    transport._set_state(TransportState.CONNECTED)
    assert transport.state() == TransportState.CONNECTED
    assert any("Invalid state transition" in line for line in lines)


def test_set_paths_when_called_updates_launch_target(qt, paths, tmp_path):
    transport, _ = make((None, None))
    assert transport.start()[0] is False
    transport._set_state(TransportState.DISCONNECTED)
    transport.set_paths(*paths)
    assert transport.start() == (True, None)


@pytest.mark.parametrize("graceful", [True, False])
def test_stop_when_final_wait_fails_retains_child_and_blocks_restart(qt, paths, monkeypatch, graceful):
    transport, events = make(paths)
    transport.start()
    process = qt.instances[-1]
    monkeypatch.setattr(process, "waitForFinished", lambda timeout: False)
    assert transport.stop(graceful=graceful) is False
    assert transport._process is process, "Uncertain child must remain owned"
    assert transport.state() == TransportState.ERROR
    assert not transport._stopping
    assert "unknown" in events["error"][-1].lower()
    assert transport.start()[0] is False
    monkeypatch.setattr(process, "waitForFinished", lambda timeout: True)
    assert transport.stop() is True
    assert transport._process is None


def test_scheduled_reconnect_when_stop_uncertain_does_not_schedule(qt, paths, monkeypatch):
    transport, events = make(paths)
    transport.start()
    process = qt.instances[-1]
    monkeypatch.setattr(process, "waitForFinished", lambda timeout: False)
    transport.request_reconnect()
    assert transport._process is process
    assert not transport._reconnect_requested
    assert transport._reconnect_timer is None


def test_stop_when_finished_signal_arrives_during_false_wait_accepts_exit(qt, paths, monkeypatch):
    transport, events = make(paths)
    transport.start()
    process = qt.instances[-1]

    def wait(timeout):
        process.finished.emit(0)
        return False

    monkeypatch.setattr(process, "waitForFinished", wait)
    assert transport.stop(graceful=False) is True
    assert transport._process is None
    assert transport.state() == TransportState.DISCONNECTED


def test_stop_when_late_finished_arrives_reconciles_retained_child(qt, paths, monkeypatch):
    transport, events = make(paths)
    transport.start()
    process = qt.instances[-1]
    monkeypatch.setattr(process, "waitForFinished", lambda timeout: False)
    assert transport.stop(graceful=False) is False
    process.finished.emit(0)
    assert transport._process is None
    assert transport.state() == TransportState.DISCONNECTED
    assert transport.start()[0] is True


def test_stop_when_finished_observer_restarts_refuses_until_stop_returns(qt, paths, monkeypatch):
    transport, events = make(paths)
    transport.start()
    process = qt.instances[-1]
    starts = []
    transport.processFinished.connect(lambda code: starts.append(transport.start()))

    def wait(timeout):
        process.finished.emit(0)
        return True

    monkeypatch.setattr(process, "waitForFinished", wait)
    assert transport.stop() is True
    assert starts and starts[0][0] is False, "Stop must not discard a replacement process"
    assert len(qt.instances) == 1
    assert transport.start()[0] is True
