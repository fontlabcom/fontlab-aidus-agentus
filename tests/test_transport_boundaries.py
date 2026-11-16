# this_file: tests/test_transport_boundaries.py
import json
from unittest.mock import Mock

import pytest
from fontlab_aidus_agentus.plugin.transport import ACPTransport, TransportState


def connected(monkeypatch):
    clock = [100.0]
    monkeypatch.setattr("fontlab_aidus_agentus.plugin.transport.time.monotonic", lambda: clock[0])
    transport = ACPTransport(timeout_seconds=30)
    transport._state = TransportState.CONNECTED
    transport._process = Mock()
    transport.messageReceived = Mock()
    transport.processError = Mock()
    return transport, clock


def receive(transport, data):
    transport._process.readAllStandardOutput.return_value = data
    transport._on_stdout_ready()


def test_idle_ready_then_new_request_gets_full_deadline(monkeypatch):
    transport, clock = connected(monkeypatch)
    clock[0] += 1000
    transport._check_timeout()
    assert transport.is_connected()
    assert transport.send({"id":1, "method":"session/prompt", "params":{"sessionId":"s"}})
    clock[0] += 29
    transport._check_timeout()
    assert transport.is_connected()
    clock[0] += 2
    transport._check_timeout()
    assert transport.state() == TransportState.ERROR
    transport.processError.emit.assert_called_once()


def test_response_and_cancel_notification_do_not_leave_idle_deadline(monkeypatch):
    transport, clock = connected(monkeypatch)
    transport.send({"id":1,"method":"session/prompt","params":{"sessionId":"s"}})
    transport.send({"method":"session/cancel","params":{"sessionId":"s"}})
    clock[0] += 29
    transport._check_timeout()
    assert transport.is_connected()
    receive(transport, b'{"id":1,"result":{"stopReason":"cancelled"}}\n')
    clock[0] += 1000
    transport._check_timeout()
    assert transport.is_connected()


def test_unacknowledged_cancel_preserves_unknown_outcome_deadline(monkeypatch):
    transport, clock = connected(monkeypatch)
    transport.send({"id":1,"method":"session/prompt","params":{"sessionId":"s"}})
    clock[0] += 29
    transport.send({"method":"session/cancel","params":{"sessionId":"s"}})
    clock[0] += 2
    transport._check_timeout()
    assert transport.state() == TransportState.ERROR


def test_session_progress_renews_only_matching_pending_prompt(monkeypatch):
    transport, clock = connected(monkeypatch)
    transport.send({"id":1,"method":"session/prompt","params":{"sessionId":"s"}})
    clock[0] += 29
    receive(transport, b'{"method":"session/update","params":{"sessionId":"s","update":{}}}\n')
    clock[0] += 29
    transport._check_timeout()
    assert transport.is_connected()
    receive(transport, b'{"method":"session/update","params":{"sessionId":"other","update":{}}}\n')
    clock[0] += 2
    transport._check_timeout()
    assert transport.state() == TransportState.ERROR


def test_server_request_and_stderr_do_not_extend_request_deadline(monkeypatch):
    transport, clock = connected(monkeypatch)
    transport.send({"id":1,"method":"initialize"})
    clock[0] += 29
    receive(transport, b'{"id":1,"method":"fontlab/tool","params":{}}\n')
    transport.send({"id":1,"result":{}})
    transport._process.readAllStandardError.return_value = b"still logging"
    transport._on_stderr_ready()
    clock[0] += 2
    transport._check_timeout()
    assert transport.state() == TransportState.ERROR


@pytest.mark.parametrize("character", ["ą", "€", "😀"])
def test_all_utf8_splits_and_multiple_frames_preserve_protocol(character):
    expected = {"result":{"text":character}}
    frame = (json.dumps(expected, ensure_ascii=False)+"\n").encode()
    for split in range(1, len(frame)):
        transport = ACPTransport()
        transport._process = Mock()
        transport.messageReceived = Mock()
        receive(transport, frame[:split])
        receive(transport, frame[split:]+frame)
        assert transport.messageReceived.emit.call_args_list == [((expected,),), ((expected,),)]


def test_incomplete_utf8_eof_reports_error_and_restart_resets_decoder(monkeypatch):
    transport, clock = connected(monkeypatch)
    receive(transport, b'{"result":"\xf0\x9f')
    transport._process.readAllStandardOutput.return_value = b""
    transport._process.readAllStandardError.return_value = b""
    transport._on_finished(0)
    transport.processError.emit.assert_called_once()
    transport._process = Mock()
    receive(transport, b'{"result":"clean"}\n')
    transport.messageReceived.emit.assert_called_once_with({"result":"clean"})


def test_invalid_utf8_never_emits_replacement_protocol_data(monkeypatch):
    transport, _ = connected(monkeypatch)
    receive(transport, b'{"result":"\xff"}\n')
    transport.messageReceived.emit.assert_not_called()
    assert transport.state() == TransportState.ERROR
    transport.processError.emit.assert_called_once()


def test_incomplete_ascii_frame_eof_reports_error(monkeypatch):
    transport, _ = connected(monkeypatch)
    receive(transport, b'{"result":"unfinished"}')
    transport._on_finished(0)
    transport.processError.emit.assert_called_once()
    transport.messageReceived.emit.assert_not_called()


def test_stop_discards_decoder_and_pending_state(monkeypatch):
    transport, _ = connected(monkeypatch)
    transport.send({"id":1,"method":"initialize"})
    receive(transport, b'\xf0\x9f')
    transport.stop()
    assert not transport._pending
    transport._process = Mock()
    receive(transport, b'{"result":"new connection"}\n')
    transport.messageReceived.emit.assert_called_once_with({"result":"new connection"})


def test_new_request_does_not_postpone_other_pending_request(monkeypatch):
    transport, clock = connected(monkeypatch)
    transport.send({"id":1,"method":"initialize"})
    clock[0] += 29
    transport.send({"id":2,"method":"session/new"})
    clock[0] += 2
    transport._check_timeout()
    assert transport.state() == TransportState.ERROR
