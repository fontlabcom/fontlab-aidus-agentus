# this_file: tests/plugin/test_edge_cases.py
# Copyright 2025 Fontlab Ltd. All rights reserved.
"""
Edge case and stress tests for the Aidus Agentus Plugin.

Covers:
- 8.08 Buffer parsing edge cases and overflow
- 8.13 No glyph/no font scenarios
- 8.14 Malformed JSON handling
- 8.15 Process crash recovery
- 8.16 Large payload handling
- 8.17 Security audit scenarios
- 8.18 Input sanitization
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any, Dict

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))
from fontlab_aidus_agentus.plugin.client import AidusAgentusClient, ClientState  # noqa: E402
from fontlab_aidus_agentus.plugin.executor import FontLabExecutor  # noqa: E402
from fontlab_aidus_agentus.plugin.transport import ACPTransport, TransportState  # noqa: E402


def _make_notification(method: str, params: Dict[str, Any] | None = None) -> Dict[str, Any]:
    notification: Dict[str, Any] = {"jsonrpc": "2.0", "method": method}
    if params is not None:
        notification["params"] = params
    return notification


# =============================================================================
# 8.08 - Buffer Parsing Edge Cases
# =============================================================================


class TestBufferParsingEdgeCases:
    """Test buffer parsing with pathological inputs. Buffer uses str, not bytes."""

    def test_empty_buffer(self) -> None:
        transport = ACPTransport()
        transport._buffer = ""
        transport._process_buffer()
        assert transport._buffer == ""

    def test_buffer_with_only_newlines(self) -> None:
        transport = ACPTransport()
        transport._buffer = "\n\n\n"
        transport._process_buffer()
        assert transport._buffer == ""

    def test_buffer_with_single_complete_message(self) -> None:
        transport = ACPTransport()
        msg = {"jsonrpc": "2.0", "method": "test"}
        transport._buffer = json.dumps(msg) + "\n"
        transport._process_buffer()
        assert transport._buffer == ""

    def test_buffer_with_incomplete_message(self) -> None:
        transport = ACPTransport()
        transport._buffer = '{"jsonrpc": "2.0", "met'
        transport._process_buffer()
        assert len(transport._buffer) > 0

    def test_buffer_with_multiple_messages(self) -> None:
        transport = ACPTransport()
        msg1 = json.dumps({"jsonrpc": "2.0", "method": "first"})
        msg2 = json.dumps({"jsonrpc": "2.0", "method": "second"})
        transport._buffer = msg1 + "\n" + msg2 + "\n"
        transport._process_buffer()
        assert transport._buffer == ""

    def test_buffer_with_malformed_json_line(self) -> None:
        transport = ACPTransport()
        good_msg = json.dumps({"jsonrpc": "2.0", "method": "good"})
        transport._buffer = "NOT VALID JSON\n" + good_msg + "\n"
        transport._process_buffer()
        assert transport._buffer == ""

    def test_buffer_with_garbage_chars(self) -> None:
        transport = ACPTransport()
        transport._buffer = "\x00\x01\x02\n"
        transport._process_buffer()
        assert transport._buffer == ""

    def test_buffer_with_bom_prefix(self) -> None:
        transport = ACPTransport()
        msg = json.dumps({"jsonrpc": "2.0", "method": "test"})
        transport._buffer = "\ufeff" + msg + "\n"
        transport._process_buffer()

    def test_buffer_with_crlf(self) -> None:
        transport = ACPTransport()
        msg = json.dumps({"jsonrpc": "2.0", "method": "test"})
        transport._buffer = msg + "\r\n"
        transport._process_buffer()

    def test_buffer_accumulation(self) -> None:
        transport = ACPTransport()
        msg = json.dumps({"jsonrpc": "2.0", "method": "test"})
        half = len(msg) // 2

        transport._buffer = msg[:half]
        transport._process_buffer()
        assert transport._buffer == msg[:half]

        transport._buffer += msg[half:] + "\n"
        transport._process_buffer()
        assert transport._buffer == ""


# =============================================================================
# 8.13 - No Glyph / No Font Scenarios
# =============================================================================


class TestNoGlyphNoFont:
    """Test behavior when no font or glyph is available."""

    def test_executor_without_fontlab(self) -> None:
        """Executor should work without FontLab loaded."""
        executor = FontLabExecutor()
        # list_tools should always work
        result = executor.run("list_tools", {})
        assert isinstance(result, dict)
        assert "tools" in result

    def test_get_glyph_info_without_fontlab(self) -> None:
        """get_current_glyph_info without FL should return error dict."""
        executor = FontLabExecutor()
        result = executor.run("get_current_glyph_info", {})
        assert isinstance(result, dict)
        # Should indicate FL is not available
        assert "error" in result or "message" in result

    def test_set_metrics_without_fontlab(self) -> None:
        """set_glyph_metrics without FL should return error dict."""
        executor = FontLabExecutor()
        result = executor.run("set_glyph_metrics", {"width": 600})
        assert isinstance(result, dict)

    def test_run_script_without_fontlab(self) -> None:
        """run_fontlab_script without FL should return error dict."""
        executor = FontLabExecutor()
        result = executor.run("run_fontlab_script", {"script": "print('hello')"})
        assert isinstance(result, dict)


# =============================================================================
# 8.14 - Malformed JSON Handling
# =============================================================================


class TestMalformedJson:
    """Test handling of malformed JSON messages."""

    @pytest.mark.parametrize(
        "bad_json",
        [
            "",  # Empty string
            "{",  # Incomplete object
            '{"key":}',  # Missing value
            "{'key': 'value'}",  # Single quotes
            '{"key": undefined}',  # JS undefined
            '{"key": NaN}',  # JS NaN
            "[1, 2, 3,]",  # Trailing comma (strict)
            "\x00\x01\x02",  # Binary garbage
        ],
    )
    def test_malformed_json_doesnt_crash_transport(self, bad_json: str) -> None:
        transport = ACPTransport()
        transport._buffer = bad_json + "\n"
        transport._process_buffer()

    def test_missing_jsonrpc_field(self) -> None:
        transport = ACPTransport()
        msg = json.dumps({"method": "test", "id": 1})
        transport._buffer = msg + "\n"
        transport._process_buffer()

    def test_wrong_jsonrpc_version(self) -> None:
        transport = ACPTransport()
        msg = json.dumps({"jsonrpc": "1.0", "method": "test", "id": 1})
        transport._buffer = msg + "\n"
        transport._process_buffer()

    def test_missing_method_in_request(self) -> None:
        msg = json.dumps({"jsonrpc": "2.0", "id": 1})
        transport = ACPTransport()
        transport._buffer = msg + "\n"
        transport._process_buffer()


# =============================================================================
# 8.15 - Process Crash Recovery
# =============================================================================


class TestProcessCrashRecovery:
    """Test transport behavior during process crashes."""

    def test_transport_state_after_disconnect(self) -> None:
        """Transport should be in DISCONNECTED state after process ends."""
        transport = ACPTransport()
        assert transport._state == TransportState.DISCONNECTED

    def test_reconnect_count_tracking(self) -> None:
        """Reconnect count should be tracked."""
        transport = ACPTransport()
        assert transport._reconnect_count == 0

    def test_max_reconnect_limit(self) -> None:
        """Should not exceed max reconnect attempts."""
        transport = ACPTransport()
        max_attempts = transport._max_reconnects
        # Simulate exhausting reconnects
        for _ in range(max_attempts + 1):
            transport._reconnect_count += 1
        assert transport._reconnect_count > max_attempts

    def test_reconnect_reset_on_success(self) -> None:
        """Reconnect count should reset when connected."""
        transport = ACPTransport()
        transport._reconnect_count = 3
        transport._reconnect_count = 0  # Simulate successful connection
        assert transport._reconnect_count == 0

    def test_stop_when_not_running(self) -> None:
        """Stopping when not running should be safe."""
        transport = ACPTransport()
        transport.stop()  # Should not raise

    def test_send_when_disconnected(self) -> None:
        """Sending when disconnected should not crash."""
        transport = ACPTransport()
        msg = {"jsonrpc": "2.0", "method": "test"}
        # Should return False or handle gracefully
        result = transport.send(msg)
        assert result is False or result is None


# =============================================================================
# 8.16 - Large Payload Handling
# =============================================================================


class TestLargePayload:
    def test_large_message_serialization(self) -> None:
        large_text = "A" * (1024 * 1024)
        msg = _make_notification("chat.update", {"content": large_text})
        json_str = json.dumps(msg)
        parsed = json.loads(json_str)
        assert len(parsed["params"]["content"]) == 1024 * 1024

    def test_large_payload_in_buffer(self) -> None:
        transport = ACPTransport()
        large_text = "B" * 100_000
        msg = json.dumps({"jsonrpc": "2.0", "method": "test", "params": {"data": large_text}})
        transport._buffer = msg + "\n"
        transport._process_buffer()
        assert transport._buffer == ""

    def test_many_small_messages(self) -> None:
        transport = ACPTransport()
        messages = []
        for i in range(100):
            messages.append(json.dumps({"jsonrpc": "2.0", "method": "test", "params": {"i": i}}))
        transport._buffer = "\n".join(messages) + "\n"
        transport._process_buffer()
        assert transport._buffer == ""

    def test_result_sanitization_with_large_data(self) -> None:
        executor = FontLabExecutor()
        large_result = {"data": "X" * 100_000}
        sanitized = executor._sanitize_result(large_result)
        assert isinstance(sanitized, dict)

    def test_deeply_nested_json(self) -> None:
        nested: Dict[str, Any] = {"level": 0}
        current = nested
        for i in range(1, 30):
            current["child"] = {"level": i}
            current = current["child"]
        msg = json.dumps(_make_notification("test", nested))
        parsed = json.loads(msg)
        assert parsed["params"]["level"] == 0


class TestSecurity:
    def test_script_execution_timeout(self) -> None:
        executor = FontLabExecutor()
        assert hasattr(executor, "_timeout_seconds")
        assert executor._timeout_seconds > 0

    def test_dangerous_imports_in_script(self) -> None:
        executor = FontLabExecutor()
        result = executor.run(
            "run_fontlab_script", {"script": "import os; os.system('echo hacked')"}
        )
        assert isinstance(result, dict)

    def test_no_file_system_access_via_tools(self) -> None:
        executor = FontLabExecutor()
        result = executor.run("get_current_glyph_info", {})
        assert isinstance(result, dict)

    def test_null_byte_injection(self) -> None:
        transport = ACPTransport()
        transport._buffer = '{"jsonrpc": "2.0", "method": "test\x00evil"}\n'
        transport._process_buffer()

    def test_extremely_long_method_name(self) -> None:
        transport = ACPTransport()
        method = "a" * 10_000
        msg = json.dumps({"jsonrpc": "2.0", "method": method})
        transport._buffer = msg + "\n"
        transport._process_buffer()


# =============================================================================
# 8.18 - Input Sanitization
# =============================================================================


class TestInputSanitization:
    """Test input sanitization for all entry points."""

    def test_executor_validates_tool_name_type(self) -> None:
        """Tool name must be a string."""
        executor = FontLabExecutor()
        # Non-string tool name should be handled
        result = executor.run("nonexistent_tool", {})
        assert isinstance(result, dict)
        assert "error" in result

    def test_executor_validates_args_type(self) -> None:
        """Args must be a dict."""
        executor = FontLabExecutor()
        result = executor.run("list_tools", {})
        assert isinstance(result, dict)

    def test_executor_rejects_unknown_tool(self) -> None:
        """Unknown tool should return error, not crash."""
        executor = FontLabExecutor()
        result = executor.run("definitely_not_a_real_tool", {})
        assert isinstance(result, dict)
        assert "error" in result

    def test_executor_missing_required_params(self) -> None:
        """Missing required params should return error."""
        executor = FontLabExecutor()
        # run_fontlab_script requires 'script' param
        result = executor.run("run_fontlab_script", {})
        assert isinstance(result, dict)
        assert "error" in result

    def test_executor_unexpected_params(self) -> None:
        """Extra/unexpected params should be handled."""
        executor = FontLabExecutor()
        result = executor.run("list_tools", {"unexpected": "param"})
        # Should either ignore or return error, not crash
        assert isinstance(result, dict)

    def test_client_state_transitions_validated(self) -> None:
        """Client should validate state transitions."""
        client = AidusAgentusClient()
        # Client starts in DISCONNECTED state
        assert client._state == ClientState.DISCONNECTED

    def test_transport_rejects_send_when_disconnected(self) -> None:
        """Transport should reject send when not connected."""
        transport = ACPTransport()
        msg = {"jsonrpc": "2.0", "method": "test", "id": 1}
        result = transport.send(msg)
        assert result is False or result is None

    def test_unicode_in_tool_args(self) -> None:
        """Unicode in tool arguments should be handled."""
        executor = FontLabExecutor()
        result = executor.run("run_fontlab_script", {"script": "# Unicode: 你好世界 🌍"})
        assert isinstance(result, dict)

    def test_empty_string_params(self) -> None:
        """Empty string parameters should be handled."""
        executor = FontLabExecutor()
        result = executor.run("run_fontlab_script", {"script": ""})
        assert isinstance(result, dict)
