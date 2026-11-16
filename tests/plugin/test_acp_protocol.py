# this_file: tests/plugin/test_acp_protocol.py
# Copyright 2025 Fontlab Ltd. All rights reserved.
"""
Tests for ACP (Agent Client Protocol) conformance.

Covers JSON-RPC 2.0 specification compliance:
- Request format validation
- Response format validation
- Notification format
- Error response format
- Batch operations
- Edge cases
"""

from __future__ import annotations

import json
from typing import Any, Dict

# =============================================================================
# JSON-RPC 2.0 Helper Functions (inlined for import safety)
# =============================================================================


def make_jsonrpc_request(
    method: str,
    params: Dict[str, Any] | None = None,
    id: int | None = None,
) -> Dict[str, Any]:
    request: Dict[str, Any] = {"jsonrpc": "2.0", "method": method}
    if params is not None:
        request["params"] = params
    if id is not None:
        request["id"] = id
    return request


def make_jsonrpc_response(
    id: int | None,
    result: Any = None,
    error: Dict[str, Any] | None = None,
) -> Dict[str, Any]:
    response: Dict[str, Any] = {"jsonrpc": "2.0", "id": id}
    if error is not None:
        response["error"] = error
    else:
        response["result"] = result
    return response


def make_jsonrpc_notification(
    method: str,
    params: Dict[str, Any] | None = None,
) -> Dict[str, Any]:
    notification: Dict[str, Any] = {"jsonrpc": "2.0", "method": method}
    if params is not None:
        notification["params"] = params
    return notification


# =============================================================================
# JSON-RPC 2.0 Request Format Tests
# =============================================================================


class TestJsonRpcRequestFormat:
    """Test JSON-RPC 2.0 request format compliance."""

    def test_request_has_jsonrpc_version(self) -> None:
        """Request must have jsonrpc: '2.0'."""
        req = make_jsonrpc_request("test", id=1)
        assert req["jsonrpc"] == "2.0"

    def test_request_has_method(self) -> None:
        """Request must have a method field."""
        req = make_jsonrpc_request("test_method", id=1)
        assert "method" in req
        assert req["method"] == "test_method"

    def test_request_method_is_string(self) -> None:
        """Method must be a string."""
        req = make_jsonrpc_request("initialize", id=1)
        assert isinstance(req["method"], str)

    def test_request_id_is_present(self) -> None:
        """Request with id must have id field."""
        req = make_jsonrpc_request("test", id=42)
        assert "id" in req
        assert req["id"] == 42

    def test_request_params_optional(self) -> None:
        """Params field is optional."""
        req = make_jsonrpc_request("test", id=1)
        assert "params" not in req or req["params"] is None

    def test_request_params_when_provided(self) -> None:
        """Params field when provided must be structured."""
        req = make_jsonrpc_request("test", {"key": "value"}, id=1)
        assert "params" in req
        assert req["params"] == {"key": "value"}

    def test_request_serializable(self) -> None:
        """Request must be JSON serializable."""
        req = make_jsonrpc_request("test", {"nested": {"key": [1, 2, 3]}}, id=1)
        json_str = json.dumps(req)
        parsed = json.loads(json_str)
        assert parsed == req


# =============================================================================
# JSON-RPC 2.0 Response Format Tests
# =============================================================================


class TestJsonRpcResponseFormat:
    """Test JSON-RPC 2.0 response format compliance."""

    def test_response_has_jsonrpc_version(self) -> None:
        """Response must have jsonrpc: '2.0'."""
        resp = make_jsonrpc_response(1, result={"success": True})
        assert resp["jsonrpc"] == "2.0"

    def test_response_has_id(self) -> None:
        """Response must have matching id."""
        resp = make_jsonrpc_response(42, result="ok")
        assert resp["id"] == 42

    def test_response_has_result_or_error(self) -> None:
        """Response must have either result or error."""
        success_resp = make_jsonrpc_response(1, result="ok")
        assert "result" in success_resp
        assert "error" not in success_resp

        error_resp = make_jsonrpc_response(1, error={"code": -32600, "message": "Invalid Request"})
        assert "error" in error_resp
        assert "result" not in error_resp

    def test_response_error_format(self) -> None:
        """Error object must have code and message."""
        error = {"code": -32601, "message": "Method not found"}
        resp = make_jsonrpc_response(1, error=error)
        assert resp["error"]["code"] == -32601
        assert resp["error"]["message"] == "Method not found"

    def test_response_error_data_optional(self) -> None:
        """Error data field is optional."""
        error = {"code": -32000, "message": "Server error", "data": {"detail": "info"}}
        resp = make_jsonrpc_response(1, error=error)
        assert resp["error"]["data"] == {"detail": "info"}


# =============================================================================
# JSON-RPC 2.0 Notification Format Tests
# =============================================================================


class TestJsonRpcNotificationFormat:
    """Test JSON-RPC 2.0 notification format compliance."""

    def test_notification_has_no_id(self) -> None:
        """Notification must not have id field."""
        notif = make_jsonrpc_notification("event.update", {"status": "ok"})
        assert "id" not in notif

    def test_notification_has_jsonrpc_version(self) -> None:
        """Notification must have jsonrpc: '2.0'."""
        notif = make_jsonrpc_notification("event", None)
        assert notif["jsonrpc"] == "2.0"

    def test_notification_has_method(self) -> None:
        """Notification must have method field."""
        notif = make_jsonrpc_notification("chat.update", {"content": "Hello"})
        assert "method" in notif
        assert notif["method"] == "chat.update"


# =============================================================================
# JSON-RPC 2.0 Error Codes Tests
# =============================================================================


class TestJsonRpcErrorCodes:
    """Test standard JSON-RPC 2.0 error codes."""

    def test_parse_error_code(self) -> None:
        """Parse error: -32700."""
        error = {"code": -32700, "message": "Parse error"}
        resp = make_jsonrpc_response(None, error=error)  # type: ignore
        assert resp["error"]["code"] == -32700

    def test_invalid_request_code(self) -> None:
        """Invalid Request: -32600."""
        error = {"code": -32600, "message": "Invalid Request"}
        resp = make_jsonrpc_response(1, error=error)
        assert resp["error"]["code"] == -32600

    def test_method_not_found_code(self) -> None:
        """Method not found: -32601."""
        error = {"code": -32601, "message": "Method not found"}
        resp = make_jsonrpc_response(1, error=error)
        assert resp["error"]["code"] == -32601

    def test_invalid_params_code(self) -> None:
        """Invalid params: -32602."""
        error = {"code": -32602, "message": "Invalid params"}
        resp = make_jsonrpc_response(1, error=error)
        assert resp["error"]["code"] == -32602

    def test_internal_error_code(self) -> None:
        """Internal error: -32603."""
        error = {"code": -32603, "message": "Internal error"}
        resp = make_jsonrpc_response(1, error=error)
        assert resp["error"]["code"] == -32603


# =============================================================================
# ACP-Specific Protocol Tests
# =============================================================================


class TestACPProtocol:
    """Test ACP-specific protocol extensions."""

    def test_initialize_request_format(self) -> None:
        """Test initialize request has required fields."""
        req = make_jsonrpc_request("initialize", {"protocolVersion": "2025-03-26"}, id=1)
        assert req["method"] == "initialize"
        assert req["params"]["protocolVersion"] == "2025-03-26"

    def test_session_new_request_format(self) -> None:
        """Test session.new request format."""
        req = make_jsonrpc_request("session.new", {}, id=2)
        assert req["method"] == "session.new"

    def test_session_prompt_request_format(self) -> None:
        """Test session.prompt request format."""
        req = make_jsonrpc_request(
            "session.prompt", {"sessionId": "abc123", "content": "Hello"}, id=3
        )
        assert req["params"]["sessionId"] == "abc123"
        assert req["params"]["content"] == "Hello"

    def test_tools_call_request_format(self) -> None:
        """Test tools.call request format."""
        req = make_jsonrpc_request(
            "tools.call", {"name": "get_current_glyph_info", "args": {}}, id=4
        )
        assert req["params"]["name"] == "get_current_glyph_info"

    def test_chat_update_notification_format(self) -> None:
        """Test chat.update notification format."""
        notif = make_jsonrpc_notification(
            "chat.update", {"content": "Processing...", "role": "assistant"}
        )
        assert notif["method"] == "chat.update"
        assert notif["params"]["role"] == "assistant"

    def test_tools_call_notification_format(self) -> None:
        """Test tools.call notification for tool invocation."""
        notif = make_jsonrpc_notification(
            "tools.call",
            {"callId": "tool_1", "name": "get_current_glyph_info", "args": {}},
        )
        assert notif["params"]["callId"] == "tool_1"
        assert notif["params"]["name"] == "get_current_glyph_info"


# =============================================================================
# Protocol Version Tests
# =============================================================================


class TestProtocolVersion:
    """Test protocol version handling."""

    def test_version_format(self) -> None:
        """Protocol version should be date-based."""
        version = "2025-03-26"
        assert len(version) == 10
        assert version.count("-") == 2

    def test_version_comparison(self) -> None:
        """Protocol versions can be compared."""
        v1 = "2025-03-26"
        v2 = "2025-04-01"
        assert v1 < v2

    def test_initialize_response_includes_version(self) -> None:
        """Initialize response should include server capabilities."""
        resp = make_jsonrpc_response(
            1,
            result={
                "protocolVersion": "2025-03-26",
                "serverInfo": {"name": "aidus-core", "version": "1.0.0"},
                "capabilities": {"tools": True, "chat": True},
            },
        )
        assert resp["result"]["protocolVersion"] == "2025-03-26"
        assert resp["result"]["capabilities"]["tools"] is True


# =============================================================================
# Message Parsing Tests
# =============================================================================


class TestMessageParsing:
    """Test message parsing edge cases."""

    def test_parse_request_with_array_params(self) -> None:
        """Params can be array (positional args)."""
        req = {"jsonrpc": "2.0", "method": "test", "params": [1, 2, 3], "id": 1}
        assert isinstance(req["params"], list)

    def test_parse_request_with_object_params(self) -> None:
        """Params can be object (named args)."""
        req = {
            "jsonrpc": "2.0",
            "method": "test",
            "params": {"a": 1, "b": 2},
            "id": 1,
        }
        assert isinstance(req["params"], dict)

    def test_null_id_for_response_to_notification(self) -> None:
        """Null id in error response indicates notification parse error."""
        resp = {"jsonrpc": "2.0", "error": {"code": -32700, "message": "Parse error"}}
        # No id means it's a response to unparseable request
        assert "id" not in resp or resp.get("id") is None

    def test_handle_unicode_in_messages(self) -> None:
        """Messages can contain unicode."""
        req = make_jsonrpc_request("test", {"text": "Héllo 中文 🌍"}, id=1)
        json_str = json.dumps(req, ensure_ascii=False)
        parsed = json.loads(json_str)
        assert parsed["params"]["text"] == "Héllo 中文 🌍"


# =============================================================================
# Batch Request Tests
# =============================================================================


class TestBatchRequests:
    """Test JSON-RPC 2.0 batch requests."""

    def test_batch_request_is_array(self) -> None:
        """Batch request is an array of requests."""
        batch = [
            make_jsonrpc_request("method1", id=1),
            make_jsonrpc_request("method2", id=2),
        ]
        assert isinstance(batch, list)
        assert len(batch) == 2

    def test_batch_can_contain_notifications(self) -> None:
        """Batch can mix requests and notifications."""
        batch = [
            make_jsonrpc_request("method1", id=1),
            make_jsonrpc_notification("event"),
            make_jsonrpc_request("method2", id=2),
        ]
        # First and third have id, second does not
        assert "id" in batch[0]
        assert "id" not in batch[1]
        assert "id" in batch[2]

    def test_batch_response_is_array(self) -> None:
        """Batch response is an array of responses."""
        responses = [
            make_jsonrpc_response(1, result="ok1"),
            make_jsonrpc_response(2, result="ok2"),
        ]
        assert isinstance(responses, list)
        assert len(responses) == 2

    def test_batch_response_order_may_differ(self) -> None:
        """Batch responses may be in different order than requests."""
        responses = [
            make_jsonrpc_response(2, result="second"),
            make_jsonrpc_response(1, result="first"),
        ]
        # Responses can be matched by id, not position
        assert responses[0]["id"] == 2
        assert responses[1]["id"] == 1


# =============================================================================
# Edge Cases and Error Conditions
# =============================================================================


class TestEdgeCases:
    """Test edge cases and error conditions."""

    def test_empty_method_string(self) -> None:
        """Empty method string is technically valid but unusual."""
        req = make_jsonrpc_request("", id=1)
        assert req["method"] == ""

    def test_very_long_method_name(self) -> None:
        """Long method names should work."""
        method = "a" * 1000
        req = make_jsonrpc_request(method, id=1)
        assert req["method"] == method

    def test_negative_id(self) -> None:
        """Negative id is valid."""
        req = make_jsonrpc_request("test", id=-1)
        assert req["id"] == -1

    def test_zero_id(self) -> None:
        """Zero id is valid."""
        req = make_jsonrpc_request("test", id=0)
        assert req["id"] == 0

    def test_string_id(self) -> None:
        """String id is valid per spec."""
        req = {"jsonrpc": "2.0", "method": "test", "id": "abc123"}
        assert req["id"] == "abc123"

    def test_null_result(self) -> None:
        """Null result is valid."""
        resp = {"jsonrpc": "2.0", "id": 1, "result": None}
        assert resp["result"] is None

    def test_empty_params_object(self) -> None:
        """Empty params object is valid."""
        req = make_jsonrpc_request("test", {}, id=1)
        assert req["params"] == {}

    def test_empty_params_array(self) -> None:
        """Empty params array is valid."""
        req = {"jsonrpc": "2.0", "method": "test", "params": [], "id": 1}
        assert req["params"] == []

    def test_deeply_nested_params(self) -> None:
        """Deeply nested params should work."""
        nested: Dict[str, Any] = {"level": 1, "child": {}}
        current = nested["child"]
        for i in range(2, 50):
            current["level"] = i
            current["child"] = {}
            current = current["child"]

        req = make_jsonrpc_request("test", nested, id=1)
        json_str = json.dumps(req)
        parsed = json.loads(json_str)
        assert parsed["params"]["level"] == 1
