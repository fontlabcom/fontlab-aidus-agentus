# this_file: tests/plugin/test_mcp_acp_client.py
"""ACP SDK compatibility without executing native MCP tools in the plugin."""

from unittest.mock import Mock

from fontlab_aidus_agentus.plugin.client import AidusAgentusClient, ClientState


def make_client():
    transport = Mock()
    transport.send.return_value = True
    return AidusAgentusClient(transport=transport, executor=Mock()), transport


def test_initialize_when_modern_uses_integer_protocol_and_session_schema():
    client, transport = make_client()
    assert client.initialize()
    request = transport.send.call_args.args[0]
    assert request["params"]["protocolVersion"] == 1
    client._handle_message({"id": request["id"], "result": {"protocolVersion": 1}})
    session = transport.send.call_args.args[0]
    assert session["method"] == "session/new"
    assert session["params"]["mcpServers"] == []
    assert session["params"]["cwd"].startswith("/")


def test_prompt_when_modern_uses_prompt_content_blocks():
    client, transport = make_client()
    client._session_id = "test"
    client._state = ClientState.READY
    assert client.send_user_prompt("Inspect A")
    request = transport.send.call_args.args[0]
    assert request["method"] == "session/prompt"
    assert request["params"]["prompt"] == [{"type": "text", "text": "Inspect A"}]


def test_update_when_mcp_tool_notification_does_not_execute_again():
    client, _ = make_client()
    client._handle_message(
        {
            "method": "session/update",
            "params": {
                "update": {
                    "sessionUpdate": "tool_call",
                    "toolCallId": "mcp1",
                    "title": "set_glyph_metrics",
                    "rawInput": {"width": 500},
                }
            },
        }
    )
    client._executor.run.assert_not_called()


def test_extension_when_fallback_executes_once_and_returns_rpc_response():
    client, transport = make_client()
    client._session_id = "test"
    client._executor.run.return_value = {"width": 600}
    client._handle_message(
        {
            "id": 44,
            "method": "_fontlab/tool",
            "params": {"sessionId": "test", "name": "get_current_glyph_info", "arguments": {}},
        }
    )
    client._executor.run.assert_called_once_with("get_current_glyph_info", {})
    assert transport.send.call_args.args[0] == {
        "jsonrpc": "2.0",
        "id": 44,
        "result": {"width": 600},
    }


def test_extension_when_wrong_session_rejects_without_executing():
    client, transport = make_client()
    client._session_id = "test"
    client._handle_message({"id": 44, "method": "_fontlab/tool", "params": {"sessionId": "other"}})
    client._executor.run.assert_not_called()
    assert transport.send.call_args.args[0]["error"]["code"] == -32601


def test_update_when_modern_text_reaches_chat():
    client, _ = make_client()
    client.chatUpdate = Mock()
    client._handle_message(
        {
            "method": "session/update",
            "params": {
                "update": {
                    "sessionUpdate": "agent_message_chunk",
                    "content": {"type": "text", "text": "Hello"},
                }
            },
        }
    )
    client.chatUpdate.emit.assert_not_called()
    client._assistant_chunks.append(" world")
    client._pending_requests[10] = "session.prompt"
    client._handle_message({"id": 10, "result": {"stopReason": "end_turn"}})
    client.chatUpdate.emit.assert_called_once_with("assistant", "Hello world")
