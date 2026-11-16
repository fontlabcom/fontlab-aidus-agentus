# this_file: tests/test_client_protocol.py
"""AidusAgentusClient ACP state machine: full handshake, legacy paths, errors, tools, reconnect."""

import pytest

from fontlab_aidus_agentus.plugin.client import AidusAgentusClient, ClientState


class Signal:
    def __init__(self):
        self.slots = []

    def connect(self, slot):
        self.slots.append(slot)

    def emit(self, *args):
        for slot in list(self.slots):
            slot(*args)


class Transport:
    def __init__(self, send_ok=True, start=(True, None)):
        self.messageReceived, self.processError, self.processFinished = Signal(), Signal(), Signal()
        self.sent, self.send_ok, self.start_result, self.calls = [], send_ok, start, []

    def send(self, message):
        self.sent.append(message)
        return self.send_ok

    def start(self):
        self.calls.append("start")
        return self.start_result

    def stop(self):
        self.calls.append("stop")


class Executor:
    def __init__(self, result=None, error=None):
        self.result, self.error, self.calls = result or {"ok": True}, error, []

    def run(self, name, arguments):
        self.calls.append((name, arguments))
        if self.error:
            raise self.error
        return self.result


def make(transport=None, executor=None):
    client = AidusAgentusClient(transport=transport, executor=executor)
    client.chatUpdate, client.stateChanged, client.errorOccurred = Signal(), Signal(), Signal()
    rows, states, errors = [], [], []
    client.chatUpdate.connect(lambda role, text: rows.append((role, text)))
    client.stateChanged.connect(states.append)
    client.errorOccurred.connect(lambda code, text: errors.append((code, text)))
    return client, rows, states, errors


def reply(transport, result, index=-1):
    request = transport.sent[index]
    transport.messageReceived.emit({"jsonrpc": "2.0", "id": request["id"], "result": result})


def ready_client(executor=None, protocol=1):
    transport = Transport()
    client, rows, states, errors = make(transport, executor)
    assert client.initialize()
    reply(transport, {"protocolVersion": protocol, "serverInfo": {"version": "1.0.0"}})
    reply(transport, {"sessionId": "s1"})
    return client, transport, rows, states, errors


def test_handshake_when_modern_server_reaches_ready_with_slash_methods():
    client, transport, rows, states, _ = ready_client()
    assert [m["method"] for m in transport.sent] == ["initialize", "session/new"]
    assert transport.sent[1]["params"]["mcpServers"] == []
    assert states == ["initializing", "initialized", "session_pending", "ready"]
    assert client.has_session() and client.session_id() == "s1"
    assert ("system", "Session ready") in rows


def test_prompt_when_chunks_stream_renders_one_assistant_row():
    client, transport, rows, states, _ = ready_client()
    assert client.send_user_prompt("Hello ✓")
    prompt = transport.sent[-1]
    assert prompt["method"] == "session/prompt"
    assert prompt["params"]["prompt"] == [{"type": "text", "text": "Hello ✓"}]
    for piece in ("Hi", " there", ""):
        transport.messageReceived.emit({"method": "session/update", "params": {
            "sessionId": "s1", "update": {"sessionUpdate": "agent_message_chunk",
                                         "content": {"type": "text", "text": piece}}}})
    reply(transport, {"stopReason": "end_turn"})
    assert rows[-1] == ("assistant", "Hi there") and client.state() == ClientState.READY


def test_tool_notifications_when_received_show_without_executing():
    executor = Executor()
    client, transport, rows, _, _ = ready_client(executor)
    for update in ({"sessionUpdate": "tool_call", "title": "list_fonts"},
                   {"sessionUpdate": "tool_call_update", "status": "completed"},
                   {"sessionUpdate": "tool_call_update"}):
        transport.messageReceived.emit({"method": "session/update", "params": {"update": update}})
    assert rows[-3:] == [("tool", "list_fonts"), ("tool", "completed"), ("tool", "Tool update")]
    assert executor.calls == []


def test_legacy_server_when_string_protocol_uses_dot_methods_and_warns_on_major_mismatch():
    transport = Transport()
    client, rows, _, _ = make(transport)
    client.initialize()
    reply(transport, {"protocolVersion": "2025-03-26", "serverInfo": {"version": "2.0.0"}})
    assert transport.sent[-1]["method"] == "session.new" and transport.sent[-1]["params"] == {}
    assert any("may be incompatible" in text for _, text in rows)
    reply(transport, {"sessionId": "legacy"})
    client.send_user_prompt("hi")
    assert transport.sent[-1]["params"]["messages"][0]["content"][0]["text"] == "hi"
    client.cleanup()
    assert transport.sent[-1]["method"] == "session.end", "Legacy servers get an explicit end"


def test_legacy_server_when_compatible_version_does_not_warn():
    transport = Transport()
    client, rows, _, _ = make(transport)
    client.initialize()
    reply(transport, {"protocolVersion": "2025-03-26", "serverInfo": {"version": "1.5.0"}})
    assert not any("incompatible" in text for _, text in rows)


def test_legacy_update_when_content_and_tool_calls_executes_and_reports():
    executor = Executor(result={"width": 600})
    client, transport, rows, _, _ = ready_client(executor)
    transport.messageReceived.emit({"method": "session.update", "params": {
        "content": [{"type": "text", "text": "Checking"}, {"type": "image"}, {"type": "text", "text": ""}],
        "toolCall": {"id": "t1", "name": "get_current_glyph_info", "arguments": {}},
        "toolCalls": [{"id": "t2", "name": "a", "arguments": {"x": 1}}, {"id": "t3", "name": "b"}]}})
    assert ("assistant", "Checking") in rows
    assert executor.calls == [("get_current_glyph_info", {}), ("a", {"x": 1}), ("b", {})]
    single, batch = transport.sent[-2], transport.sent[-1]
    assert single["params"]["toolId"] == "t1" and single["params"]["result"] == {"width": 600}
    assert [r["toolId"] for r in batch["params"]["results"]] == ["t2", "t3"]
    assert any(role == "tool_result" and "[get_current_glyph_info]" in text for role, text in rows)


def test_tool_result_when_not_json_serialisable_falls_back_to_str():
    executor = Executor(result={"value": {1, 2}})
    client, transport, rows, _, _ = ready_client(executor)
    client._handle_tool_call({"id": "t", "name": "x"})
    assert any(role == "tool_result" and "{1, 2}" in text for role, text in rows)


def test_execute_tool_when_executor_missing_or_raising_returns_error_dict():
    client, *_ = make(Transport())
    assert client._execute_tool_safely("x", {}) == {"error": "No executor configured"}
    client._executor = Executor(error=RuntimeError("boom"))
    assert client._execute_tool_safely("x", {}) == {"error": "boom"}


def test_server_request_when_fallback_tool_for_current_session_executes_once():
    executor = Executor(result={"done": 1})
    client, transport, _, _, _ = ready_client(executor)
    transport.messageReceived.emit({"jsonrpc": "2.0", "id": 99, "method": "_fontlab/tool",
                                    "params": {"sessionId": "s1", "name": "run_fontlab_script",
                                               "arguments": {"code": "1"}}})
    assert executor.calls == [("run_fontlab_script", {"code": "1"})]
    assert transport.sent[-1] == {"jsonrpc": "2.0", "id": 99, "result": {"done": 1}}


@pytest.mark.parametrize("method,session", [("_fontlab/tool", "other"), ("fs/read_text_file", "s1")])
def test_server_request_when_foreign_session_or_unknown_method_is_refused(method, session):
    executor = Executor()
    client, transport, _, _, _ = ready_client(executor)
    transport.messageReceived.emit({"id": 5, "method": method, "params": {"sessionId": session}})
    assert executor.calls == []
    assert transport.sent[-1]["error"]["code"] == -32601


@pytest.mark.parametrize(
    "state,expected",
    [(ClientState.INITIALIZING, ClientState.ERROR), (ClientState.SESSION_PENDING, ClientState.INITIALIZED),
     (ClientState.WAITING, ClientState.READY), (ClientState.READY, ClientState.READY)],
)
def test_error_response_when_in_state_moves_to_recovery_state(state, expected):
    transport = Transport()
    client, rows, _, errors = make(transport)
    client._state = state
    client._pending_requests[3] = "session.prompt"
    client._assistant_chunks = ["partial"]
    transport.messageReceived.emit({"id": 3, "error": {"code": -32603, "message": "Internal"}})
    assert client.state() == expected
    assert errors == [("-32603", "Internal")]
    assert rows[0] == ("assistant", "partial"), "Streamed text is kept before the error"
    assert rows[-1] == ("error", "[session.prompt] -32603: Internal")


def test_error_response_when_unknown_id_and_shape_uses_defaults():
    client, rows, _, errors = make(Transport())
    client._handle_message({"id": None, "error": {}})
    assert errors == [("UNKNOWN", "Unknown error")] and rows[-1][1].startswith("[unknown]")


def test_send_user_prompt_when_not_ready_or_no_session_refuses():
    client, rows, _, _ = make(Transport())
    assert client.send_user_prompt("x") is False
    assert "not ready" in rows[-1][1]
    client._state = ClientState.READY
    assert client.send_user_prompt("x") is False
    assert rows[-1] == ("error", "Cannot send: no active session")


def test_send_user_prompt_when_transport_rejects_returns_to_ready():
    client, transport, rows, _, _ = ready_client()
    transport.send_ok = False
    assert client.send_user_prompt("x") is False
    assert client.state() == ClientState.READY and rows[-1] == ("error", "Failed to send message")


def test_initialize_when_send_fails_or_wrong_state():
    client, _, _, errors = make(Transport(send_ok=False))
    assert client.initialize() is False
    assert client.state() == ClientState.ERROR and errors[-1][0] == "SEND_FAILED"
    client._state = ClientState.READY
    assert client.initialize() is False


def test_client_without_transport_cannot_send_or_reconnect():
    client, *_ = make(None)
    assert client._send_request("initialize") is False
    assert client.reconnect() is False and client.transport is None


def test_request_session_when_not_initialized_is_refused():
    client, *_ = make(Transport())
    assert client._request_session() is False


def test_reconnect_when_start_succeeds_reinitializes_without_replay():
    client, transport, _, _, _ = ready_client()
    client.send_user_prompt("pending edit")
    sent_before = len(transport.sent)
    assert client.reconnect() is True
    assert transport.calls == ["stop", "start"]
    assert transport.sent[sent_before]["method"] == "initialize"
    assert all(m.get("method") != "session/prompt" for m in transport.sent[sent_before:]), "No replay"
    assert client.session_id() is None


def test_reconnect_when_start_fails_reports_transport_error():
    transport = Transport(start=(False, None))
    client, rows, _, errors = make(transport)
    assert client.reconnect() is False
    assert errors[-1] == ("TRANSPORT", "Reconnect failed") and client.state() == ClientState.ERROR


def test_process_finished_when_child_exits_resets_session():
    client, transport, _, _, _ = ready_client()
    transport.processFinished.emit(0)
    assert client.state() == ClientState.DISCONNECTED and not client.has_session()


def test_transport_error_when_emitted_reports_error_row():
    client, transport, rows, _, errors = ready_client()
    transport.processError.emit("pipe closed")
    assert rows[-1] == ("error", "Transport error: pipe closed") and errors[-1][0] == "TRANSPORT"


def test_messages_when_unroutable_are_ignored():
    client, transport, rows, _, _ = ready_client()
    before = list(rows)
    for message in ({}, {"id": 1}, {"method": "unknown/notification", "params": {}},
                    {"id": 12345, "result": {"unexpected": True}}):
        transport.messageReceived.emit(message)
    assert rows == before and client.state() == ClientState.READY


def test_client_reconnect_when_stop_uncertain_keeps_session_and_does_not_start(monkeypatch):
    transport = Transport()
    client = AidusAgentusClient(transport=transport, executor=Executor())
    client._session_id = "owned-session"
    client._pending_requests[3] = "session/prompt"
    monkeypatch.setattr(transport, "stop", lambda: False)
    assert client.reconnect() is False
    assert client._session_id == "owned-session"
    assert client._pending_requests == {3: "session/prompt"}
    assert transport.calls == []
