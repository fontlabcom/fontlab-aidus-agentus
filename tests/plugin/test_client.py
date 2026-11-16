# this_file: tests/plugin/test_client.py
# Copyright 2025 Fontlab Ltd. All rights reserved.
"""Tests for ACP Client (E4.20)."""

from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from fontlab_aidus_agentus.plugin.client import AidusAgentusClient, ClientState


class TestClientState:
    """Tests for ClientState constants."""

    def test_all_states_are_strings(self) -> None:
        states = [
            ClientState.DISCONNECTED,
            ClientState.INITIALIZING,
            ClientState.INITIALIZED,
            ClientState.SESSION_PENDING,
            ClientState.READY,
            ClientState.WAITING,
            ClientState.ERROR,
        ]
        for state in states:
            assert isinstance(state, str)

    def test_all_states_are_distinct(self) -> None:
        states = [
            ClientState.DISCONNECTED,
            ClientState.INITIALIZING,
            ClientState.INITIALIZED,
            ClientState.SESSION_PENDING,
            ClientState.READY,
            ClientState.WAITING,
            ClientState.ERROR,
        ]
        assert len(states) == len(set(states))


class TestClientInit:
    """Tests for AidusAgentusClient initialization."""

    def test_init_with_defaults(self) -> None:
        client = AidusAgentusClient()
        assert client._transport is None
        assert client._executor is None
        assert client._request_id == 0
        assert client._session_id is None
        assert client.state() == ClientState.DISCONNECTED

    def test_init_with_mock_transport(self) -> None:
        class MockTransport:
            messageReceived = type("Signal", (), {"connect": lambda self, x: None})()
            processError = type("Signal", (), {"connect": lambda self, x: None})()
            processFinished = type("Signal", (), {"connect": lambda self, x: None})()

        transport = MockTransport()
        client = AidusAgentusClient(transport=transport)
        assert client._transport is transport


class TestRequestIdGeneration:
    """Tests for request ID generation."""

    def test_request_id_starts_at_zero(self) -> None:
        client = AidusAgentusClient()
        assert client._request_id == 0

    def test_request_id_increments(self) -> None:
        client = AidusAgentusClient()
        id1 = client._next_request_id()
        id2 = client._next_request_id()
        assert id1 == 1
        assert id2 == 2

    def test_request_ids_are_unique(self) -> None:
        client = AidusAgentusClient()
        ids = [client._next_request_id() for _ in range(100)]
        assert len(ids) == len(set(ids))


class TestRequestBuilder:
    """Tests for JSON-RPC request building."""

    def test_build_request_basic(self) -> None:
        client = AidusAgentusClient()
        request = client._build_request("initialize")
        assert request["jsonrpc"] == "2.0"
        assert request["method"] == "initialize"
        assert request["id"] == 1
        assert "params" not in request

    def test_build_request_with_params(self) -> None:
        client = AidusAgentusClient()
        params = {"key": "value"}
        request = client._build_request("test.method", params)
        assert request["params"] == params

    def test_build_request_increments_id(self) -> None:
        client = AidusAgentusClient()
        req1 = client._build_request("method1")
        req2 = client._build_request("method2")
        assert req1["id"] < req2["id"]


class TestStateMachine:
    """Tests for client state machine."""

    def test_initial_state_is_disconnected(self) -> None:
        client = AidusAgentusClient()
        assert client.state() == ClientState.DISCONNECTED

    def test_is_ready_false_initially(self) -> None:
        client = AidusAgentusClient()
        assert not client.is_ready()

    def test_has_session_false_initially(self) -> None:
        client = AidusAgentusClient()
        assert not client.has_session()
        assert client.session_id() is None


class TestInitializeProtocol:
    """Tests for protocol initialization."""

    def test_initialize_fails_without_transport(self) -> None:
        client = AidusAgentusClient()
        result = client.initialize()
        assert result is False
        assert client.state() == ClientState.ERROR

    def test_initialize_changes_state_to_initializing(self) -> None:
        class MockTransport:
            messageReceived = type("Signal", (), {"connect": lambda self, x: None})()
            processError = type("Signal", (), {"connect": lambda self, x: None})()
            processFinished = type("Signal", (), {"connect": lambda self, x: None})()

            def send(self, msg: dict) -> bool:
                return True

        client = AidusAgentusClient(transport=MockTransport())
        result = client.initialize()
        assert result is True
        assert client.state() == ClientState.INITIALIZING


class TestSendUserPrompt:
    """Tests for send_user_prompt method."""

    def test_send_fails_when_not_ready(self) -> None:
        client = AidusAgentusClient()
        result = client.send_user_prompt("hello")
        assert result is False

    def test_send_fails_without_session(self) -> None:
        client = AidusAgentusClient()
        client._state = ClientState.READY
        result = client.send_user_prompt("hello")
        assert result is False


class TestMessageRouting:
    """Tests for message routing."""

    def test_handle_response_with_result(self) -> None:
        client = AidusAgentusClient()
        client._pending_requests[1] = "initialize"
        client._state = ClientState.INITIALIZING
        client._handle_message({"id": 1, "result": {"protocolVersion": "2025-03-26"}})
        assert client.state() == ClientState.SESSION_PENDING

    def test_handle_notification(self) -> None:
        client = AidusAgentusClient()
        client._state = ClientState.READY
        client._session_id = "test-session"
        # Should not raise
        client._handle_message({"method": "session.update", "params": {"content": []}})


class TestToolExecution:
    """Tests for tool execution."""

    def test_execute_tool_safely_without_executor(self) -> None:
        client = AidusAgentusClient()
        result = client._execute_tool_safely("test", {})
        assert "error" in result

    def test_execute_tool_safely_with_mock_executor(self) -> None:
        class MockExecutor:
            def run(self, name: str, args: dict) -> dict:
                return {"success": True}

        client = AidusAgentusClient(executor=MockExecutor())
        result = client._execute_tool_safely("test", {})
        assert result == {"success": True}


class TestErrorHandling:
    """Tests for error handling."""

    def test_handle_error_response(self) -> None:
        client = AidusAgentusClient()
        client._state = ClientState.WAITING
        client._pending_requests[1] = "session.prompt"
        client._handle_error_response({"id": 1, "error": {"code": 123, "message": "Test error"}})
        assert client.state() == ClientState.READY


class TestCleanup:
    """Tests for cleanup and reset."""

    def test_cleanup_clears_session(self) -> None:
        client = AidusAgentusClient()
        client._session_id = "test-session"
        client._pending_requests[1] = "test"
        client.cleanup()
        assert client._session_id is None
        assert len(client._pending_requests) == 0
        assert client.state() == ClientState.DISCONNECTED

    def test_reset_clears_all_state(self) -> None:
        client = AidusAgentusClient()
        client._session_id = "test"
        client._request_id = 50
        client._pending_requests[1] = "test"
        client.reset()
        assert client._session_id is None
        assert client._request_id == 0
        assert len(client._pending_requests) == 0
        assert client.state() == ClientState.DISCONNECTED
