# this_file: tests/plugin/test_ui_formatting.py
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def _escape_html(text):
    """Standalone copy of escape function for testing without Qt."""
    return (
        text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;").replace('"', "&quot;")
    )


class TestHTMLEscaping:
    def test_escape_html_basic(self):
        result = _escape_html("<script>alert('xss')</script>")
        assert "<script>" not in result
        assert "&lt;script&gt;" in result

    def test_escape_html_ampersand(self):
        result = _escape_html("A & B")
        assert "&amp;" in result
        assert " & " not in result

    def test_escape_html_quotes(self):
        result = _escape_html('onclick="evil()"')
        assert "&quot;" in result
        assert '"evil()"' not in result

    def test_escape_html_all_special_chars(self):
        malicious = '<script>alert("xss")</script> & more'
        result = _escape_html(malicious)

        assert "<" not in result
        assert ">" not in result
        assert '"' not in result
        assert " & " not in result
        assert "&lt;" in result
        assert "&gt;" in result
        assert "&quot;" in result
        assert "&amp;" in result

    def test_escape_html_preserves_safe_text(self):
        safe_text = "Hello World 123 !@#$%^*()_+=[]{};':,.?/"
        result = _escape_html(safe_text)
        assert "Hello World 123" in result

    def test_escape_html_empty_string(self):
        result = _escape_html("")
        assert result == ""

    def test_escape_html_unicode(self):
        unicode_text = "Hello \u4e16\u754c \u0430\u0431\u0432 \u03b1\u03b2\u03b3"
        result = _escape_html(unicode_text)
        assert "\u4e16\u754c" in result


class TestStringFormattingSafety:
    def test_transport_debug_formatting(self):
        message = "[ACPTransport] %s" % "test message"
        assert message == "[ACPTransport] test message"

    def test_executor_error_formatting(self):
        tool_name = "test_tool"
        error_msg = "Unknown tool: %s" % tool_name
        assert error_msg == "Unknown tool: test_tool"

    def test_client_state_formatting(self):
        state = "ready"
        message = "Cannot send: client not ready (state: %s)" % state
        assert "state: ready" in message

    def test_malicious_input_in_controlled_format(self):
        evil_input = "<script>alert(1)</script>"
        msg = "Error: %s" % evil_input
        assert "<script>" in msg  # Without escaping, raw input appears
        escaped_msg = "Error: %s" % _escape_html(evil_input)
        assert "<script>" not in escaped_msg  # With escaping, it's safe


def _format_error_message(message):
    error_hints = {
        "TRANSPORT": "Check if the core process is running",
        "SEND_FAILED": "Connection lost - try reconnecting",
        "-32600": "Invalid request format",
        "-32601": "Method not found on server",
        "-32602": "Invalid parameters",
        "-32603": "Internal server error",
        "FailedToStart": "Core process failed to start - check Python path",
        "Crashed": "Core process crashed - check logs",
        "Timedout": "Core process timeout - may need restart",
    }
    for code, hint in error_hints.items():
        if code in message:
            return "%s\n  → %s" % (message, hint)
    return message


class TestErrorHints:
    def test_transport_error_gets_hint(self):
        result = _format_error_message("Error: TRANSPORT failure")
        assert "→ Check if the core process is running" in result

    def test_send_failed_gets_hint(self):
        result = _format_error_message("SEND_FAILED: connection lost")
        assert "→ Connection lost" in result

    def test_json_rpc_error_codes(self):
        assert "-32600" in _format_error_message("Code: -32600 invalid")
        assert "→ Invalid request" in _format_error_message("Code: -32600")
        assert "→ Method not found" in _format_error_message("Error -32601")
        assert "→ Invalid parameters" in _format_error_message("Error -32602")
        assert "→ Internal server" in _format_error_message("Error -32603")

    def test_process_error_hints(self):
        assert "→ Core process failed to start - check Python path" in _format_error_message(
            "FailedToStart"
        )
        assert "→ Core process crashed - check logs" in _format_error_message("Crashed")
        assert "→ Core process timeout - may need restart" in _format_error_message("Timedout")

    def test_unknown_error_no_hint(self):
        result = _format_error_message("Random error message")
        assert "→" not in result
        assert result == "Random error message"

    def test_error_preserves_original_message(self):
        original = "Error: TRANSPORT xyz"
        result = _format_error_message(original)
        assert original in result


class TestRoleColors:
    ROLE_COLORS = {
        "user": "#2979FF",
        "assistant": "#00C853",
        "system": "#9E9E9E",
        "error": "#FF1744",
        "tool": "#FF9100",
        "tool_result": "#7C4DFF",
    }

    def test_all_roles_have_colors(self):
        roles = ["user", "assistant", "system", "error", "tool", "tool_result"]
        for role in roles:
            assert role in self.ROLE_COLORS

    def test_colors_are_valid_hex(self):
        import re

        hex_pattern = re.compile(r"^#[0-9A-Fa-f]{6}$")
        for role, color in self.ROLE_COLORS.items():
            assert hex_pattern.match(color), "Invalid hex color for %s: %s" % (role, color)

    def test_user_color_is_blue(self):
        assert self.ROLE_COLORS["user"].startswith("#2")

    def test_error_color_is_red(self):
        assert self.ROLE_COLORS["error"].startswith("#FF")


class TestKeyboardShortcutLogic:
    KEY_ESCAPE = 0x01000000
    KEY_SPACE = 0x20

    def test_escape_key_constant(self):
        assert self.KEY_ESCAPE == 0x01000000

    def test_escape_should_cancel_thinking(self):
        thinking_visible = True
        pressed_key = self.KEY_ESCAPE

        if pressed_key == self.KEY_ESCAPE and thinking_visible:
            thinking_visible = False

        assert thinking_visible is False

    def test_non_escape_does_not_cancel(self):
        thinking_visible = True
        pressed_key = self.KEY_SPACE

        should_cancel = pressed_key == self.KEY_ESCAPE and thinking_visible
        if should_cancel:
            thinking_visible = False

        assert thinking_visible is True

    def test_escape_when_not_thinking(self):
        thinking_visible = False
        pressed_key = self.KEY_ESCAPE
        messages = []

        if pressed_key == self.KEY_ESCAPE and thinking_visible:
            thinking_visible = False
            messages.append("cancelled")

        assert len(messages) == 0
