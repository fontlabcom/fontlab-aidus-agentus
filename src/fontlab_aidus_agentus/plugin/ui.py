# this_file: src/fontlab_aidus_agentus/plugin/ui.py
# Copyright 2025 Fontlab Ltd. All rights reserved.
"""Aidus Agentus Plugin UI - PythonQt dock widget for FontLab (Epoch 6)."""

from __future__ import annotations

import json
import os
import re
import time
from typing import TYPE_CHECKING, Any, Callable, Optional

if TYPE_CHECKING:
    from fontlab_aidus_agentus.plugin.client import AidusAgentusClient

try:
    from PythonQt.QtCore import Qt
    from PythonQt.QtGui import (
        QDockWidget,
        QFont,
        QHBoxLayout,
        QLabel,
        QLineEdit,
        QPalette,
        QPushButton,
        QTextEdit,
        QVBoxLayout,
        QWidget,
    )
except ImportError:
    # Mock for development outside FontLab
    from typing import Any

    class _StubSignal:
        def connect(self, slot: Callable[..., Any]) -> None:
            pass

        def emit(self, *args: Any) -> None:
            pass

    class QPalette:  # type: ignore[no-redef]
        Window = 1

        def color(self, role: int) -> Any:
            return self

        def lightness(self) -> int:
            return 0

    class QWidget:  # type: ignore[no-redef]
        def __init__(self, parent: Any = None) -> None:
            pass

        def setWindowTitle(self, title: str) -> None:
            pass

        def setMinimumWidth(self, width: int) -> None:
            pass

        def palette(self) -> QPalette:
            return QPalette()

        def emit(self, *args: Any) -> None:
            pass

        def connect(self, slot: Callable[..., Any]) -> None:
            pass

        def setLayout(self, layout: Any) -> None:
            pass

        def setMinimumSize(self, w: int, h: int) -> None:
            pass

    class Qt:  # type: ignore[no-redef]
        LeftDockWidgetArea = 1
        RightDockWidgetArea = 2
        Key_Escape = 0x01000000

    class QDockWidget:  # type: ignore[no-redef]
        def __init__(self, title: str = "", parent: Any = None) -> None:
            pass

        def setObjectName(self, name: str) -> None:
            pass

        def setWidget(self, widget: Any) -> None:
            pass

        def setAllowedAreas(self, areas: int) -> None:
            pass

        def setMinimumSize(self, w: int, h: int) -> None:
            pass

    class QTextEdit:  # type: ignore[no-redef]
        def __init__(self, parent: Any = None) -> None:
            self.textChanged: _StubSignal = _StubSignal()

        def setReadOnly(self, ro: bool) -> None:
            pass

        def setPlaceholderText(self, text: str) -> None:
            pass

        def setFont(self, font: Any) -> None:
            pass

        def append(self, text: str) -> None:
            pass

        def clear(self) -> None:
            pass

        def toPlainText(self) -> str:
            return ""

        def verticalScrollBar(self) -> Any:
            class _Scrollbar:
                def maximum(self) -> int:
                    return 0

                def setValue(self, v: int) -> None:
                    pass

            return _Scrollbar()

    class QLineEdit:  # type: ignore[no-redef]
        def __init__(self, parent: Any = None) -> None:
            self.returnPressed: _StubSignal = _StubSignal()

        def text(self) -> str:
            return ""

        def clear(self) -> None:
            pass

        def setPlaceholderText(self, text: str) -> None:
            pass

        def setEnabled(self, enabled: bool) -> None:
            pass

    class QVBoxLayout:  # type: ignore[no-redef]
        def __init__(self, parent: Any = None) -> None:
            pass

        def addWidget(self, widget: Any, stretch: int = 0) -> None:
            pass

        def addLayout(self, layout: Any, stretch: int = 0) -> None:
            pass

        def setContentsMargins(self, left: int, top: int, right: int, bottom: int) -> None:
            pass

        def setSpacing(self, s: int) -> None:
            pass

    class QHBoxLayout:  # type: ignore[no-redef]
        def __init__(self, parent: Any = None) -> None:
            pass

        def addWidget(self, widget: Any, stretch: int = 0) -> None:
            pass

        def addStretch(self, stretch: int = 0) -> None:
            pass

    class QPushButton:  # type: ignore[no-redef]
        def __init__(self, text: str = "", parent: Any = None) -> None:
            self.clicked: _StubSignal = _StubSignal()

        def setEnabled(self, enabled: bool) -> None:
            pass

    class QFont:  # type: ignore[no-redef]
        def __init__(self, family: str = "", size: int = 0) -> None:
            pass

    class QLabel:  # type: ignore[no-redef]
        def __init__(self, text: str = "", parent: Any = None) -> None:
            pass

        def setText(self, text: str) -> None:
            pass

        def setVisible(self, visible: bool) -> None:
            pass

        def isVisible(self) -> bool:
            return False

        def setStyleSheet(self, style: str) -> None:
            pass


# E6.09: Role colors for chat messages
ROLE_COLORS = {
    "user": "#2979FF",
    "assistant": "#00C853",
    "system": "#9E9E9E",
    "error": "#FF1744",
    "tool": "#FF9100",
    "tool_result": "#7C4DFF",
}

DEFAULT_COLOR = "#FFFFFF"


class AidusAgentusDock(QDockWidget):  # type: ignore[misc]
    """Main dock widget for Aidus Agentus plugin (E6.01)."""

    ROLE_COLORS_DARK = ROLE_COLORS
    ROLE_COLORS_LIGHT = ROLE_COLORS
    DEFAULT_COLOR_DARK = "#FFFFFF"
    DEFAULT_COLOR_LIGHT = "#000000"
    HISTORY_FILE = os.path.expanduser("~/.config/aidus_agentus/history.json")
    MAX_HISTORY = 500  # Chat rows kept in history.json and restored on start.
    MAX_MESSAGE_CHARS = 20000  # Longer messages are saved truncated.
    MAX_HISTORY_BYTES = 2000000  # history.json size cap; the oldest rows go first.

    def __init__(self, parent: Any = None, client: Optional[AidusAgentusClient] = None) -> None:
        super(AidusAgentusDock, self).__init__("Aidus Agentus", parent)

        # E6.01: Object name for state persistence
        self.setObjectName("AidusAgentusDock")

        # E6.01: Allowed dock areas
        self.setAllowedAreas(Qt.LeftDockWidgetArea | Qt.RightDockWidgetArea)

        # E6.01: Minimum size
        self.setMinimumSize(300, 200)

        # E6.01: Client reference
        self._client = client
        self._history_data = []

        # E6.02: Central widget with layout
        container = QWidget()
        layout = QVBoxLayout(container)
        layout.setContentsMargins(4, 4, 4, 4)
        layout.setSpacing(4)

        toolbar_layout = QHBoxLayout()

        self._status_label = QLabel("● Disconnected")
        self._status_label.setStyleSheet("color: #FF1744; font-weight: bold;")
        toolbar_layout.addWidget(self._status_label)

        toolbar_layout.addStretch(1)

        self._reconnect_btn = QPushButton("Reconnect")
        self._reconnect_btn.clicked.connect(self._on_reconnect)
        toolbar_layout.addWidget(self._reconnect_btn)

        self._clear_btn = QPushButton("Clear")
        self._clear_btn.clicked.connect(self.clear_chat)
        toolbar_layout.addWidget(self._clear_btn)

        layout.addLayout(toolbar_layout)

        # E6.02: Chat history display
        self._chat_display = QTextEdit()
        self._chat_display.setReadOnly(True)
        self._chat_display.setPlaceholderText("Chat messages will appear here...")
        self._chat_display.setFont(QFont("Menlo", 12))

        # E6.11: Thinking indicator
        self._thinking_label = QLabel("Thinking...")
        self._thinking_label.setStyleSheet("color: #9E9E9E; font-style: italic; padding: 4px;")
        self._thinking_label.setVisible(False)

        # E6.03: Input field
        self._input_field = QLineEdit()
        self._input_field.setPlaceholderText("Type a message...")
        self._input_field.returnPressed.connect(self._on_submit)

        # Build layout
        layout.addWidget(self._chat_display, 1)
        layout.addWidget(self._thinking_label, 0)
        layout.addWidget(self._input_field, 0)

        container.setLayout(layout)
        self.setWidget(container)

        # Connect to client if provided
        if self._client is not None:
            self._connect_client_signals()

        self._load_history()

    def set_client(self, client: AidusAgentusClient) -> None:
        """Set the client and connect signals."""
        self._client = client
        self._connect_client_signals()

    def _connect_client_signals(self) -> None:
        """Connect client signals to UI handlers."""
        if self._client is None:
            return
        self._client.chatUpdate.connect(self._on_chat_update)
        self._client.stateChanged.connect(self._on_state_changed)
        # Initial status update
        self._update_status_indicator("disconnected")  # Default start state

    def _on_reconnect(self, checked: bool = False) -> None:
        """Handle reconnect request."""
        if self._client and self._client.transport:
            self.append_text("system", "Reconnecting...")
            self._client.reconnect()
        else:
            self.show_error("No client transport available")

    def _update_status_indicator(self, state: str) -> None:
        """Update the connection status indicator (E6.14)."""
        if state in ("connected", "ready"):
            self._status_label.setText("● Connected")
            self._status_label.setStyleSheet("color: #00C853; font-weight: bold;")
            self._reconnect_btn.setEnabled(False)
        elif state == "disconnected" or state == "error":
            self._status_label.setText("● Disconnected")
            self._status_label.setStyleSheet("color: #FF1744; font-weight: bold;")
            self._reconnect_btn.setEnabled(True)
        elif state == "connecting":
            self._status_label.setText("● Connecting...")
            self._status_label.setStyleSheet("color: #FF9100; font-weight: bold;")
            self._reconnect_btn.setEnabled(False)

    # ==========================================================================
    # E6.05: Submit Handler
    # ==========================================================================

    def _on_submit(self) -> None:
        """Handle input submission."""
        value = self._input_field.text
        text = (value() if callable(value) else value).strip()
        if not text:
            return

        self._input_field.clear()

        if self._client is not None:
            self._client.send_user_prompt(text)
        else:
            self.append_text("error", "No client connected")

    # ==========================================================================
    # E6.06 & E6.07: Message Display
    # ==========================================================================

    def append_text(self, role: str, text: str, save: bool = True) -> None:
        """Append a message to the chat display (E6.06)."""
        is_dark = self._detect_is_dark()
        colors = self.ROLE_COLORS_DARK if is_dark else self.ROLE_COLORS_LIGHT
        default_color = self.DEFAULT_COLOR_DARK if is_dark else self.DEFAULT_COLOR_LIGHT

        color = colors.get(role, default_color)
        timestamp = time.strftime("%H:%M:%S")

        body = self._format_message(text)

        text_color = "#EEEEEE" if is_dark else "#000000"
        time_color = "#666666" if is_dark else "#999999"

        html = (
            '<div style="margin-bottom: 8px;">'
            '<span style="color: %s; font-weight: bold;">%s</span> '
            '<span style="color: %s; font-size: 10px;">%s</span>'
            '<div style="margin-left: 12px; color: %s;">%s</div>'
            "</div>"
        ) % (color, role.upper(), time_color, timestamp, text_color, body)

        self._chat_display.append(html)
        self._scroll_to_bottom()

        if save:
            self._history_data.append({"role": role, "content": text, "timestamp": timestamp})
            self._save_history()

    def _detect_is_dark(self) -> bool:
        """Detect if the UI is in dark mode (E6.19)."""
        try:
            palette_value = self.palette
            palette = palette_value() if callable(palette_value) else palette_value
            # If window color is dark (<128 lightness), assume dark mode
            lightness = palette.color(QPalette.Window).lightness
            return (lightness() if callable(lightness) else lightness) < 128
        except Exception:
            # Fallback to dark mode if detection fails
            return True

    def _load_history(self) -> None:
        """Load chat history from file (E6.18)."""
        if not os.path.exists(self.HISTORY_FILE):
            return
        try:
            size = os.path.getsize(self.HISTORY_FILE)
        except OSError as e:
            self.append_text("system", "History file unavailable: %s" % e.__class__.__name__, save=False)
            return
        if size > 4 * self.MAX_HISTORY_BYTES:
            self.append_text("system", "History file too large (%d bytes); ignored" % size, save=False)
            return

        try:
            with open(self.HISTORY_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
                if isinstance(data, list):
                    rows = [
                        msg for msg in data
                        if isinstance(msg, dict) and "role" in msg and "content" in msg
                    ]
                    for msg in self._bounded(rows):
                        self.append_text(msg["role"], msg["content"], save=False)
                        # Restore internal list
                        self._history_data.append(msg)
        except Exception as e:
            self.append_text("system", f"Failed to load history: {e}", save=False)

    def _save_history(self) -> None:
        """Save chat history to file (E6.18)."""
        self._history_data = self._bounded(self._history_data)
        try:
            os.makedirs(os.path.dirname(self.HISTORY_FILE), exist_ok=True)
            with open(self.HISTORY_FILE, "w", encoding="utf-8") as f:
                json.dump(self._history_data, f)
        except Exception as e:
            print(f"Failed to save history: {e}")

    def _bounded(self, rows: list) -> list:
        """Newest rows within MAX_HISTORY rows and MAX_HISTORY_BYTES of compact JSON,
        each message cut to MAX_MESSAGE_CHARS."""
        kept, size = [], 2  # the enclosing brackets
        for msg in reversed(rows[-self.MAX_HISTORY:]):
            content = str(msg["content"])
            if len(content) > self.MAX_MESSAGE_CHARS:
                msg = dict(msg, content=content[: self.MAX_MESSAGE_CHARS] + " … [truncated]")
            row = len(json.dumps(msg).encode("utf-8")) + (2 if kept else 0)  # ", " separator
            if size + row > self.MAX_HISTORY_BYTES:
                break
            kept.append(msg)
            size += row
        return kept[::-1]

    def clear_chat(self, checked: bool = False) -> None:
        """Clear chat history."""
        self._chat_display.clear()
        self._history_data = []
        if os.path.exists(self.HISTORY_FILE):
            try:
                os.remove(self.HISTORY_FILE)
            except Exception:
                pass

    def _format_message(self, text: str) -> str:
        """Format text with markdown code blocks and HTML escaping (E6.17)."""
        text = self._escape_html(text)

        pattern = r"```(\w*)\n?(.*?)```"
        parts = re.split(pattern, text, flags=re.DOTALL)

        result = []
        i = 0
        while i < len(parts):
            normal_text = parts[i]
            normal_text = normal_text.replace("\n", "<br>")
            result.append(normal_text)

            if i + 2 < len(parts):
                _ = parts[i + 1]
                code = parts[i + 2]

                code_block = (
                    f'<pre style="background-color: #2b2b2b; color: #a9b7c6; '
                    f'padding: 8px; border-radius: 4px; overflow-x: auto; margin: 4px 0;">'
                    f"<code>{code}</code></pre>"
                )
                result.append(code_block)
                i += 3
            else:
                i += 1

        return "".join(result)

    def _escape_html(self, text: str) -> str:
        """Escape HTML special characters."""
        return (
            text.replace("&", "&amp;")
            .replace("<", "&lt;")
            .replace(">", "&gt;")
            .replace('"', "&quot;")
        )

    def _scroll_to_bottom(self) -> None:
        """Scroll chat to bottom."""
        scrollbar = self._chat_display.verticalScrollBar()
        maximum = scrollbar.maximum
        scrollbar.setValue(maximum() if callable(maximum) else maximum)

    # ==========================================================================
    # E6.11: Thinking Indicator
    # ==========================================================================

    def show_thinking(self) -> None:
        """Show the thinking indicator."""
        self._thinking_label.setVisible(True)
        self._input_field.setEnabled(False)

    def hide_thinking(self) -> None:
        """Hide the thinking indicator."""
        self._thinking_label.setVisible(False)
        self._input_field.setEnabled(True)

    # ==========================================================================
    # E6.10: Error Display
    # ==========================================================================

    def show_error(self, message: str) -> None:
        """Display an error message with enhanced formatting."""
        formatted = self._format_error_message(message)
        self.append_text("error", formatted)

    def _format_error_message(self, message: str) -> str:
        """Format error message with helpful context (E6.20)."""
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

    # ==========================================================================
    # Signal Handlers
    # ==========================================================================

    def keyPressEvent(self, event: Any) -> None:
        """Handle keyboard shortcuts (E6.16)."""
        key = event.key()

        if key == Qt.Key_Escape:
            if self._thinking_label.isVisible():
                self.hide_thinking()
                self.append_text("system", "Generation cancelled")

    def _on_chat_update(self, role: str, content: str) -> None:
        """Handle chat update from client."""
        self.append_text(role, content)

    def _on_state_changed(self, state: str) -> None:
        """Handle state change from client."""
        self._update_status_indicator(state)
        if state == "waiting":
            self.show_thinking()
        else:
            self.hide_thinking()

    # ==========================================================================
    # Utility Methods
    # ==========================================================================

    def get_client(self) -> Optional[AidusAgentusClient]:
        """Get the current client."""
        return self._client
