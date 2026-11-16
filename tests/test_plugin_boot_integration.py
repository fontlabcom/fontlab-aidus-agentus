# this_file: tests/test_plugin_boot_integration.py
"""Real bootstrap wiring (config, executor, transport, client, dock) with fake FontLab/Qt.

Only the QProcess and PythonQt widgets are faked. The ACP exchange below is
what the brain sends; the fallback tool request runs the real executor against
a fake `fontlab` glyph.
"""

import json
import stat
from types import SimpleNamespace

import pytest

from fontlab_aidus_agentus.plugin import client as client_module, executor as executor_module, main, transport as transport_module


class Signal:
    def __init__(self, *args):
        self.slots = []

    def connect(self, slot):
        self.slots.append(slot)

    def emit(self, *args):
        for slot in list(self.slots):
            slot(*args)


class Process:
    SeparateChannels = 0
    last = None

    def __init__(self, parent=None):
        self.readyReadStandardOutput, self.readyReadStandardError = Signal(), Signal()
        self.finished, self.errorOccurred = Signal(), Signal()
        self.written, self.stdout, self.program = b"", b"", None
        Process.last = self

    def setProcessChannelMode(self, mode):
        pass

    def setWorkingDirectory(self, path):
        self.cwd = path

    def setProcessEnvironment(self, env):
        self.env = env

    def start(self, program, args):
        self.program, self.args = program, args

    def waitForStarted(self, timeout):
        return True

    def write(self, data):
        self.written += data

    def readAllStandardOutput(self):
        data, self.stdout = self.stdout, b""
        return data

    stderr = b""

    def readAllStandardError(self):
        data, self.stderr = self.stderr, b""
        return data

    def closeWriteChannel(self):
        self.finished.emit(0, 0)

    def waitForFinished(self, timeout):
        return True

    def requests(self):
        return [json.loads(line) for line in self.written.decode("utf-8").splitlines()]

    def reply(self, message):
        self.stdout = (json.dumps(message) + "\n").encode("utf-8")
        self.readyReadStandardOutput.emit()


class Timer:
    def __init__(self, parent=None):
        self.timeout = Signal()

    def start(self, interval):
        pass

    def stop(self):
        pass


@pytest.fixture
def booted(fake_qt, monkeypatch, tmp_path):
    fake_qt("fontlab_aidus_agentus.plugin.ui")
    monkeypatch.setattr(transport_module, "QProcess", Process)
    monkeypatch.setattr(transport_module, "QTimer", Timer)
    # Stub signals are inert; give the real classes working ones for this test.
    for cls, names in ((transport_module.ACPTransport, ("messageReceived", "stderrReceived", "stateChanged",
                                                        "processError", "processFinished")),
                       (client_module.AidusAgentusClient, ("chatUpdate", "stateChanged", "errorOccurred"))):
        original_init = cls.__init__

        def init(self, *args, __original=original_init, __names=names, **kwargs):
            for name in __names:
                setattr(self, name, Signal())
            __original(self, *args, **kwargs)

        monkeypatch.setattr(cls, "__init__", init)
    python = tmp_path / "python"
    python.write_text("#!/bin/sh\n")
    python.chmod(python.stat().st_mode | stat.S_IXUSR)
    monkeypatch.setenv("AIDUS_PYTHON", str(python))
    glyph = SimpleNamespace(name="A", width=600, lsb=50, rsb=50, unicode=65, layers=[1])
    monkeypatch.setattr(executor_module, "FL_AVAILABLE", True)
    monkeypatch.setattr(executor_module, "fl", SimpleNamespace(CurrentFont=lambda: object(), CurrentGlyph=lambda: glyph))
    monkeypatch.setattr(main, "_dock", None)
    dock = main.bootstrap()
    return SimpleNamespace(dock=dock, process=Process.last, glyph=glyph, python=str(python))


def test_boot_when_brain_answers_reaches_ready_and_runs_fallback_tool(booted):
    process, dock = booted.process, booted.dock
    assert process.program == booted.python and process.args[0].endswith("core_launcher.py")
    initialize = process.requests()[0]
    assert initialize["method"] == "initialize" and initialize["params"]["protocolVersion"] == 1
    process.reply({"jsonrpc": "2.0", "id": initialize["id"], "result": {"protocolVersion": 1}})
    new_session = process.requests()[1]
    assert new_session["method"] == "session/new"
    process.reply({"jsonrpc": "2.0", "id": new_session["id"], "result": {"sessionId": "S"}})
    assert dock._status_label.text_value == "● Connected"
    assert any("Session ready" in row for row in dock._chat_display.html)

    dock._input_field.value = "Make A wider"
    dock._on_submit()
    prompt = process.requests()[2]
    assert prompt["method"] == "session/prompt" and dock._thinking_label.visible is True

    process.reply({"jsonrpc": "2.0", "id": 77, "method": "_fontlab/tool",
                   "params": {"sessionId": "S", "name": "set_glyph_metrics", "arguments": {"width": 640}}})
    tool_reply = process.requests()[3]
    assert tool_reply["id"] == 77 and tool_reply["result"]["success"] is True
    assert booted.glyph.width == 640, "The fallback tool edited the (fake) glyph exactly once"

    process.reply({"method": "session/update", "params": {"sessionId": "S", "update": {
        "sessionUpdate": "agent_message_chunk", "content": {"type": "text", "text": "Done: A is 640."}}}})
    process.reply({"jsonrpc": "2.0", "id": prompt["id"], "result": {"stopReason": "end_turn"}})
    assert "Done: A is 640." in dock._chat_display.html[-1]
    assert dock._thinking_label.visible is False

    main.shutdown()
    assert main.get_dock() is None


def test_boot_when_brain_exits_mid_prompt_reports_and_resets(booted):
    process, dock = booted.process, booted.dock
    process.reply({"jsonrpc": "2.0", "id": process.requests()[0]["id"], "result": {"protocolVersion": 1}})
    process.reply({"jsonrpc": "2.0", "id": process.requests()[1]["id"], "result": {"sessionId": "S"}})
    dock._input_field.value = "hello"
    dock._on_submit()
    process.stdout = b'{"partial": '
    process.readyReadStandardOutput.emit()
    process.finished.emit(1, 1)
    assert any("Incomplete ACP stdout" in row for row in dock._chat_display.html)
    assert dock.get_client().state() == "disconnected"
    assert dock._status_label.text_value == "● Disconnected"


def test_boot_when_brain_fails_shows_its_last_stderr_lines(booted, capsys):
    process, dock = booted.process, booted.dock
    process.stderr = b'{"level": "info", "event": "starting"}\nTraceback (most recent call last):\nImportError: No module named agentpool\n'
    process.readyReadStandardError.emit()
    process.finished.emit(1, 1)
    assert "ImportError: No module named agentpool" in dock._chat_display.html[-1]
    assert "Brain exited with code 1" in dock._chat_display.html[-1]
    assert "[Aidus brain] ImportError: No module named agentpool" in capsys.readouterr().out
