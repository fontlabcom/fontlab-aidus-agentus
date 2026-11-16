# this_file: tests/plugin/conftest.py
"""
Shared test fixtures for the Aidus Agentus Plugin test suite.

This module provides common fixtures for testing the plugin components
without requiring FontLab or the actual Core process.
"""

from __future__ import annotations

import sys
from typing import Any, Callable, Dict, List, Optional

import pytest

# =============================================================================
# Mock FontLab Module
# =============================================================================


class MockFlGlyph:
    """Mock FontLab glyph object."""

    def __init__(self, name: str = "A", unicode_val: int = 65):
        self.name = name
        self.unicode = unicode_val
        self._width = 600
        self._lsb = 50
        self._rsb = 50

    @property
    def width(self) -> int:
        return self._width

    @width.setter
    def width(self, value: int) -> None:
        self._width = value

    @property
    def lsb(self) -> int:
        return self._lsb

    @lsb.setter
    def lsb(self, value: int) -> None:
        self._lsb = value

    @property
    def rsb(self) -> int:
        return self._rsb

    @rsb.setter
    def rsb(self, value: int) -> None:
        self._rsb = value


class MockFlLayer:
    """Mock FontLab layer object."""

    def __init__(self):
        self.name = "master"


class MockFlFont:
    """Mock FontLab font object."""

    def __init__(self, path: str = "/path/to/font.vfc"):
        self.path = path
        self.family = "Test Family"
        self._glyphs: Dict[str, MockFlGlyph] = {"A": MockFlGlyph()}

    def glyph(self, name: str) -> Optional[MockFlGlyph]:
        return self._glyphs.get(name)

    def addGlyph(self, glyph: MockFlGlyph) -> None:
        self._glyphs[glyph.name] = glyph


class MockFlWorkspace:
    """Mock FontLab workspace singleton."""

    def __init__(self):
        self._fonts: List[MockFlFont] = []
        self._current_font_index: int = -1
        self._current_glyph: Optional[MockFlGlyph] = None

    @property
    def fonts(self) -> List[MockFlFont]:
        return self._fonts

    def addFont(self, font: MockFlFont) -> None:
        self._fonts.append(font)
        if self._current_font_index < 0:
            self._current_font_index = 0

    @property
    def currentFont(self) -> Optional[MockFlFont]:
        if 0 <= self._current_font_index < len(self._fonts):
            return self._fonts[self._current_font_index]
        return None

    @property
    def currentGlyph(self) -> Optional[MockFlGlyph]:
        return self._current_glyph

    @currentGlyph.setter
    def currentGlyph(self, glyph: Optional[MockFlGlyph]) -> None:
        self._current_glyph = glyph


class MockFlModule:
    """
    Mock 'fl' module that simulates FontLab's embedded Python environment.

    This allows testing plugin code outside of FontLab.
    """

    def __init__(self):
        self._workspace = MockFlWorkspace()
        self.flGlyph = MockFlGlyph
        self.flFont = MockFlFont
        self.flLayer = MockFlLayer

    @property
    def workspace(self) -> MockFlWorkspace:
        return self._workspace

    def Update(self) -> None:
        """Simulate UI update."""
        pass

    def output(self, message: str) -> None:
        """Simulate output panel."""
        print(f"[FL Output] {message}")


@pytest.fixture
def mock_fl() -> MockFlModule:
    """Provide a mock fl module for testing."""
    return MockFlModule()


@pytest.fixture
def mock_fl_with_font(mock_fl: MockFlModule) -> MockFlModule:
    """Provide a mock fl module with a font loaded."""
    font = MockFlFont()
    mock_fl.workspace.addFont(font)
    return mock_fl


@pytest.fixture
def mock_fl_with_glyph(mock_fl_with_font: MockFlModule) -> MockFlModule:
    """Provide a mock fl module with a font and current glyph."""
    glyph = MockFlGlyph(name="B", unicode_val=66)
    font = mock_fl_with_font.workspace.currentFont
    if font is not None:
        font.addGlyph(glyph)
    mock_fl_with_font.workspace.currentGlyph = glyph
    return mock_fl_with_font


@pytest.fixture
def inject_mock_fl(mock_fl: MockFlModule) -> Callable[[], None]:
    """
    Fixture that returns a function to inject mock fl into sys.modules.

    Usage:
        def test_something(inject_mock_fl):
            inject_mock_fl()
            # Now 'import fl' works
    """

    def _inject() -> None:
        sys.modules["fl"] = mock_fl  # type: ignore

    return _inject


@pytest.fixture(autouse=True)
def cleanup_fl_module():
    """Ensure fl module is cleaned up after each test."""
    yield
    if "fl" in sys.modules:
        del sys.modules["fl"]


# =============================================================================
# Mock Transport Fixtures
# =============================================================================


class MockProcess:
    """Mock QProcess for testing transport."""

    def __init__(self):
        self.state_value = 0  # NotRunning
        self.program: Optional[str] = None
        self.arguments: List[str] = []
        self.stdin_data: List[bytes] = []
        self.stdout_data: bytes = b""
        self.stderr_data: bytes = b""
        self._started = False

    def state(self) -> int:
        return self.state_value

    def start(self) -> None:
        self._started = True
        self.state_value = 2  # Running

    def write(self, data: bytes) -> int:
        self.stdin_data.append(data)
        return len(data)

    def waitForBytesWritten(self, timeout: int = -1) -> bool:
        return True

    def terminate(self) -> None:
        self.state_value = 0

    def kill(self) -> None:
        self.state_value = 0

    def waitForFinished(self, timeout: int = -1) -> bool:
        return True

    def readAllStandardOutput(self) -> bytes:
        data = self.stdout_data
        self.stdout_data = b""
        return data

    def readAllStandardError(self) -> bytes:
        data = self.stderr_data
        self.stderr_data = b""
        return data


@pytest.fixture
def mock_process() -> MockProcess:
    """Provide a mock QProcess."""
    return MockProcess()


# =============================================================================
# JSON-RPC Test Helpers
# =============================================================================


def make_jsonrpc_request(
    method: str,
    params: Optional[Dict[str, Any]] = None,
    id: Optional[int] = None,
) -> Dict[str, Any]:
    """Create a JSON-RPC 2.0 request."""
    request: Dict[str, Any] = {
        "jsonrpc": "2.0",
        "method": method,
    }
    if params is not None:
        request["params"] = params
    if id is not None:
        request["id"] = id
    return request


def make_jsonrpc_response(
    id: int,
    result: Optional[Any] = None,
    error: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """Create a JSON-RPC 2.0 response."""
    response: Dict[str, Any] = {
        "jsonrpc": "2.0",
        "id": id,
    }
    if error is not None:
        response["error"] = error
    else:
        response["result"] = result
    return response


def make_jsonrpc_notification(
    method: str,
    params: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """Create a JSON-RPC 2.0 notification (no id)."""
    notification: Dict[str, Any] = {
        "jsonrpc": "2.0",
        "method": method,
    }
    if params is not None:
        notification["params"] = params
    return notification


@pytest.fixture
def jsonrpc_request() -> Callable[..., Dict[str, Any]]:
    """Fixture providing JSON-RPC request builder."""
    return make_jsonrpc_request


@pytest.fixture
def jsonrpc_response() -> Callable[..., Dict[str, Any]]:
    """Fixture providing JSON-RPC response builder."""
    return make_jsonrpc_response


@pytest.fixture
def jsonrpc_notification() -> Callable[..., Dict[str, Any]]:
    """Fixture providing JSON-RPC notification builder."""
    return make_jsonrpc_notification


# =============================================================================
# Test Data Generators
# =============================================================================


@pytest.fixture
def large_payload() -> str:
    """Generate a large payload for stress testing."""
    # 1MB of data
    return "x" * (1024 * 1024)


@pytest.fixture
def malformed_json_samples() -> List[str]:
    """Provide various malformed JSON samples for edge case testing."""
    return [
        "",  # Empty
        "{",  # Incomplete object
        '{"key":}',  # Missing value
        "{'key': 'value'}",  # Single quotes (invalid JSON)
        '{"key": undefined}',  # JavaScript undefined
        '{"key": NaN}',  # JavaScript NaN
        '{"key": Infinity}',  # JavaScript Infinity
        "[1, 2, 3,]",  # Trailing comma
        '{"a": 1, "a": 2}',  # Duplicate keys
        "\x00\x01\x02",  # Binary garbage
        "null\x00extra",  # Null byte injection
        '{"\\u0000": "value"}',  # Null character in key
    ]


@pytest.fixture
def valid_jsonrpc_messages() -> List[Dict[str, Any]]:
    """Provide valid JSON-RPC messages for testing."""
    return [
        make_jsonrpc_request("initialize", {"protocolVersion": "2025-03-26"}, 1),
        make_jsonrpc_response(1, {"name": "test", "version": "1.0"}),
        make_jsonrpc_notification("chat.update", {"content": "Hello"}),
        make_jsonrpc_request("tools.call", {"name": "test_tool", "args": {}}, 2),
        make_jsonrpc_response(2, {"success": True}),
    ]


@pytest.fixture
def unicode_test_data() -> Dict[str, str]:
    """Provide unicode test strings."""
    return {
        "ascii": "Hello World",
        "latin1": "Héllo Wörld",
        "cyrillic": "Привет мир",
        "japanese": "こんにちは世界",
        "chinese": "你好世界",
        "arabic": "مرحبا بالعالم",
        "emoji": "Hello 👋 World 🌍",
        "mixed": "Test: é中文🎉",
        "rtl": "שלום עולם",
        "zalgo": "H̸̡̪̯ẻ̶̬̲l̴̨̟̋l̶̲̇̔o̶͖̊",
    }


# =============================================================================
# Performance Testing Fixtures
# =============================================================================


@pytest.fixture
def message_burst() -> Callable[[int], List[Dict[str, Any]]]:
    """Generate a burst of messages for stress testing."""

    def _generate(count: int) -> List[Dict[str, Any]]:
        return [make_jsonrpc_notification("test.event", {"index": i}) for i in range(count)]

    return _generate


# =============================================================================
# State Machine Testing
# =============================================================================


@pytest.fixture
def state_transitions() -> Dict[str, Dict[str, List[str]]]:
    """Define valid state transitions for testing state machines."""
    return {
        "transport": {
            "DISCONNECTED": ["CONNECTING"],
            "CONNECTING": ["CONNECTED", "ERROR", "DISCONNECTED"],
            "CONNECTED": ["DISCONNECTED", "ERROR"],
            "ERROR": ["DISCONNECTED", "CONNECTING"],
        },
        "client": {
            "DISCONNECTED": ["INITIALIZING"],
            "INITIALIZING": ["INITIALIZED", "ERROR"],
            "INITIALIZED": ["SESSION_PENDING", "ERROR"],
            "SESSION_PENDING": ["READY", "ERROR"],
            "READY": ["WAITING", "DISCONNECTED", "ERROR"],
            "WAITING": ["READY", "ERROR"],
            "ERROR": ["DISCONNECTED"],
        },
    }
