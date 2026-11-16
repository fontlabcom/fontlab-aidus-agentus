# this_file: tests/plugin/test_transport.py
# Copyright 2025 Fontlab Ltd. All rights reserved.
"""Tests for ACP Transport Layer (E3.20)."""

from __future__ import annotations

import json
import os
import sys
import tempfile

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from fontlab_aidus_agentus.plugin.transport import VALID_STATE_TRANSITIONS, ACPTransport, TransportState


class TestTransportState:
    """Tests for TransportState constants."""

    def test_state_values_are_strings(self) -> None:
        assert isinstance(TransportState.DISCONNECTED, str)
        assert isinstance(TransportState.CONNECTING, str)
        assert isinstance(TransportState.CONNECTED, str)
        assert isinstance(TransportState.ERROR, str)

    def test_state_values_are_distinct(self) -> None:
        states = [
            TransportState.DISCONNECTED,
            TransportState.CONNECTING,
            TransportState.CONNECTED,
            TransportState.ERROR,
        ]
        assert len(states) == len(set(states))


class TestACPTransportInit:
    """Tests for ACPTransport initialization."""

    def test_init_with_defaults(self) -> None:
        transport = ACPTransport()
        assert transport._python_exe is None
        assert transport._boot_script is None
        assert transport._buffer == ""
        assert transport.state() == TransportState.DISCONNECTED

    def test_init_with_paths(self) -> None:
        transport = ACPTransport(python_exe="/usr/bin/python3", boot_script="/path/to/boot.py")
        assert transport._python_exe == "/usr/bin/python3"
        assert transport._boot_script == "/path/to/boot.py"

    def test_init_with_timeout(self) -> None:
        transport = ACPTransport(timeout_seconds=60)
        assert transport._timeout_seconds == 60

    def test_init_with_working_dir(self) -> None:
        transport = ACPTransport(working_dir="/path/to/core")
        assert transport._working_dir == "/path/to/core"

    def test_init_working_dir_defaults_to_none(self) -> None:
        transport = ACPTransport()
        assert transport._working_dir is None


class TestPathValidation:
    """Tests for Python executable and boot script path validation."""

    def test_validate_python_path_none(self) -> None:
        transport = ACPTransport()
        valid, error = transport._validate_python_path(None)
        assert not valid
        assert "None" in error

    def test_validate_python_path_not_exists(self) -> None:
        transport = ACPTransport()
        valid, error = transport._validate_python_path("/nonexistent/python")
        assert not valid
        assert "not found" in error

    def test_validate_python_path_valid(self) -> None:
        transport = ACPTransport()
        valid, error = transport._validate_python_path(sys.executable)
        assert valid
        assert error is None

    def test_validate_boot_script_none(self) -> None:
        transport = ACPTransport()
        valid, error = transport._validate_boot_script(None)
        assert not valid
        assert "None" in error

    def test_validate_boot_script_not_exists(self) -> None:
        transport = ACPTransport()
        valid, error = transport._validate_boot_script("/nonexistent/boot.py")
        assert not valid
        assert "not found" in error

    def test_validate_boot_script_valid(self) -> None:
        with tempfile.NamedTemporaryFile(suffix=".py", delete=False) as f:
            f.write(b"# test\n")
            script_path = f.name
        try:
            transport = ACPTransport()
            valid, error = transport._validate_boot_script(script_path)
            assert valid
            assert error is None
        finally:
            os.unlink(script_path)


class TestTransportStateMachine:
    """Tests for transport state machine."""

    def test_initial_state_is_disconnected(self) -> None:
        transport = ACPTransport()
        assert transport.state() == TransportState.DISCONNECTED

    def test_is_connected_returns_false_initially(self) -> None:
        transport = ACPTransport()
        assert not transport.is_connected()

    def test_set_paths(self) -> None:
        transport = ACPTransport()
        transport.set_paths("/usr/bin/python3", "/path/boot.py")
        assert transport._python_exe == "/usr/bin/python3"
        assert transport._boot_script == "/path/boot.py"

    def test_valid_state_transitions_defined(self) -> None:
        all_states = {
            TransportState.DISCONNECTED,
            TransportState.CONNECTING,
            TransportState.CONNECTED,
            TransportState.ERROR,
        }
        for state in all_states:
            assert state in VALID_STATE_TRANSITIONS

    def test_disconnected_can_only_go_to_connecting(self) -> None:
        valid = VALID_STATE_TRANSITIONS[TransportState.DISCONNECTED]
        assert valid == {TransportState.CONNECTING}

    def test_connecting_can_go_to_connected_or_error(self) -> None:
        valid = VALID_STATE_TRANSITIONS[TransportState.CONNECTING]
        assert valid == {TransportState.CONNECTED, TransportState.ERROR}

    def test_connected_can_go_to_disconnected_or_error(self) -> None:
        valid = VALID_STATE_TRANSITIONS[TransportState.CONNECTED]
        assert valid == {TransportState.DISCONNECTED, TransportState.ERROR}

    def test_error_can_only_go_to_disconnected(self) -> None:
        valid = VALID_STATE_TRANSITIONS[TransportState.ERROR]
        assert valid == {TransportState.DISCONNECTED}


class TestStartStop:
    """Tests for start/stop functionality."""

    def test_start_fails_with_invalid_python(self) -> None:
        transport = ACPTransport(python_exe="/nonexistent/python", boot_script="/tmp/boot.py")
        success, error = transport.start()
        assert not success
        assert "not found" in error
        assert transport.state() == TransportState.ERROR

    def test_start_fails_with_invalid_boot_script(self) -> None:
        transport = ACPTransport(python_exe=sys.executable, boot_script="/nonexistent/boot.py")
        success, error = transport.start()
        assert not success
        assert "not found" in error
        assert transport.state() == TransportState.ERROR

    def test_stop_when_not_running(self) -> None:
        transport = ACPTransport()
        transport.stop()
        assert transport.state() == TransportState.DISCONNECTED


class TestDebugLogging:
    """Tests for debug logging hooks."""

    def test_debug_disabled_by_default(self) -> None:
        transport = ACPTransport()
        assert not transport._debug_enabled

    def test_enable_debug(self) -> None:
        transport = ACPTransport()
        transport.enable_debug()
        assert transport._debug_enabled

    def test_disable_debug(self) -> None:
        transport = ACPTransport()
        transport.enable_debug()
        transport.disable_debug()
        assert not transport._debug_enabled

    def test_debug_with_callback(self) -> None:
        messages: list[str] = []
        transport = ACPTransport()
        transport.enable_debug(callback=messages.append)
        transport._debug("test message")
        assert len(messages) == 1
        assert "test message" in messages[0]


class TestReconnectLogic:
    """Tests for reconnect logic skeleton."""

    def test_reconnect_count_starts_at_zero(self) -> None:
        transport = ACPTransport()
        assert transport._reconnect_count == 0

    def test_reset_reconnect_count(self) -> None:
        transport = ACPTransport()
        transport._reconnect_count = 2
        transport.reset_reconnect_count()
        assert transport._reconnect_count == 0

    def test_max_reconnects_default(self) -> None:
        transport = ACPTransport()
        assert transport._max_reconnects == 3


class TestBufferProcessing:
    """Tests for JSON-line buffer processing (buffer logic only, signals require real Qt)."""

    def test_empty_buffer_no_change(self) -> None:
        transport = ACPTransport()
        transport._buffer = ""
        transport._process_buffer()
        assert transport._buffer == ""

    def test_single_complete_message_clears_buffer(self) -> None:
        transport = ACPTransport()
        msg = {"jsonrpc": "2.0", "id": 1}
        transport._buffer = json.dumps(msg) + "\n"
        transport._process_buffer()
        assert transport._buffer == ""

    def test_incomplete_message_stays_in_buffer(self) -> None:
        transport = ACPTransport()
        transport._buffer = '{"jsonrpc": "2.0"'
        transport._process_buffer()
        assert transport._buffer == '{"jsonrpc": "2.0"'

    def test_multiple_messages_clears_buffer(self) -> None:
        transport = ACPTransport()
        msg1 = {"id": 1}
        msg2 = {"id": 2}
        transport._buffer = json.dumps(msg1) + "\n" + json.dumps(msg2) + "\n"
        transport._process_buffer()
        assert transport._buffer == ""

    def test_partial_buffer_preserved(self) -> None:
        transport = ACPTransport()
        transport._buffer = '{"id": 1}\n{"id":'
        transport._process_buffer()
        assert transport._buffer == '{"id":'

    def test_malformed_json_skipped_buffer_cleared(self) -> None:
        transport = ACPTransport()
        transport._buffer = "not json\n" + '{"valid": true}\n'
        transport._process_buffer()
        assert transport._buffer == ""


class TestSendMethod:
    """Tests for send() method."""

    def test_send_returns_false_when_not_connected(self) -> None:
        transport = ACPTransport()
        result = transport.send({"test": "message"})
        assert not result

    def test_send_returns_false_when_process_is_none(self) -> None:
        transport = ACPTransport()
        transport._state = TransportState.CONNECTED
        result = transport.send({"test": "message"})
        assert not result


class TestLargePayloads:
    """Tests for handling large message payloads (E8.12)."""

    def test_large_payload_buffer_processing(self) -> None:
        """Test that 1MB+ payloads can be processed correctly."""
        transport = ACPTransport()
        one_mb_data = "x" * (1024 * 1024)
        msg = {"jsonrpc": "2.0", "id": 1, "result": {"data": one_mb_data}}
        transport._buffer = json.dumps(msg) + "\n"

        transport._process_buffer()

        assert transport._buffer == ""

    def test_multiple_large_messages(self) -> None:
        """Test that multiple large messages are handled correctly."""
        transport = ACPTransport()
        hundred_kb_data = "y" * (100 * 1024)
        msg1 = {"jsonrpc": "2.0", "id": 1, "result": {"chunk": hundred_kb_data}}
        msg2 = {"jsonrpc": "2.0", "id": 2, "result": {"chunk": hundred_kb_data}}

        transport._buffer = json.dumps(msg1) + "\n" + json.dumps(msg2) + "\n"
        transport._process_buffer()

        assert transport._buffer == ""

    def test_large_payload_with_partial(self) -> None:
        """Test large complete message followed by partial message."""
        transport = ACPTransport()
        half_mb_data = "z" * (512 * 1024)
        msg = {"jsonrpc": "2.0", "id": 1, "result": {"data": half_mb_data}}
        partial = '{"jsonrpc": "2.0", "id": 2'

        transport._buffer = json.dumps(msg) + "\n" + partial
        transport._process_buffer()

        assert transport._buffer == partial

    def test_deeply_nested_large_payload(self) -> None:
        """Test deeply nested JSON structures."""
        transport = ACPTransport()
        nested: dict = {"level": 0}
        current = nested
        for i in range(50):
            current["child"] = {"level": i + 1, "data": "a" * 1000}
            current = current["child"]

        msg = {"jsonrpc": "2.0", "id": 1, "result": nested}
        transport._buffer = json.dumps(msg) + "\n"
        transport._process_buffer()

        assert transport._buffer == ""

    def test_unicode_large_payload(self) -> None:
        """Test large payloads with unicode characters."""
        transport = ACPTransport()
        unicode_data = "Hello " * 10000 + "World " * 10000
        msg = {"jsonrpc": "2.0", "id": 1, "result": {"text": unicode_data}}

        transport._buffer = json.dumps(msg, ensure_ascii=False) + "\n"
        transport._process_buffer()

        assert transport._buffer == ""
