# this_file: src/fontlab_aidus_agentus/plugin/transport.py
# Copyright 2025 Fontlab Ltd. All rights reserved.
"""QProcess transport: stdio pipe between the Plugin and the Core process.

The Core (fontlab_aidus_agentus.core) runs as a child process launched via QProcess.
Messages are newline-delimited JSON written to the child's stdin and read
from its stdout. This module owns that pipe.

State machine (4 states):
    DISCONNECTED → CONNECTING → CONNECTED
                             ↕
                           ERROR → DISCONNECTED

Explicit standalone reconnection uses exponential backoff, max 3 attempts.
The embedded client owns reconnect/start/initialize/session negotiation; no
automatic process restart or replay is performed after a failure.

Buffer handling:
    QProcess delivers data in chunks. The transport accumulates bytes in an
    internal buffer and only dispatches complete lines (terminated by ``\\n``).
    Lines exceeding 64 KB are chunked on write to avoid QProcess pipe stalls.

All methods must be called from the Qt main thread. Signals are emitted
synchronously on the main thread via Qt's event loop.
"""

from __future__ import annotations

import codecs
import json
import os
import time
from typing import TYPE_CHECKING, Any, Callable, List

if TYPE_CHECKING:
    from typing import Protocol

    class SignalType(Protocol):
        def emit(self, *args: Any) -> None: ...
        def connect(self, slot: Callable[..., Any]) -> None: ...


try:
    import PythonQt
except ModuleNotFoundError as exc:
    if exc.name != "PythonQt":
        raise
    PythonQt = None

if PythonQt is not None:
    from PythonQt.QtCore import QProcess, QProcessEnvironment, QTimer, Signal
    try:
        from PythonQt.QtCore import QObject
    except ImportError:
        from PythonQt.private import QObject
else:

    class _StubSignal:
        def __init__(self, *args: Any) -> None:
            pass

        def emit(self, *args: Any) -> None:
            pass

        def connect(self, slot: Callable[..., Any]) -> None:
            pass

    class QObject:  # type: ignore[no-redef]
        pass

    class QProcessEnvironment:
        @classmethod
        def systemEnvironment(cls):
            return cls()

        def insert(self, name, value):
            pass

    class QProcess:  # type: ignore[no-redef]
        NotRunning = 0
        Starting = 1
        Running = 2
        SeparateChannels = 0
        MergedChannels = 1
        FailedToStart = 0
        Crashed = 1
        Timedout = 2
        WriteError = 3
        ReadError = 4
        UnknownError = 5

        def __init__(self, parent: Any = None) -> None:
            self.readyReadStandardOutput: _StubSignal = _StubSignal()
            self.readyReadStandardError: _StubSignal = _StubSignal()
            self.finished: _StubSignal = _StubSignal()
            self.errorOccurred: _StubSignal = _StubSignal()
            self.error: _StubSignal = _StubSignal()

        def start(self, program: str, args: List[str]) -> None:
            pass

        def waitForStarted(self, timeout: int = 3000) -> bool:
            return True

        def write(self, data: bytes) -> None:
            pass

        def readAllStandardOutput(self) -> bytes:
            return b""

        def readAllStandardError(self) -> bytes:
            return b""

        def setProcessChannelMode(self, mode: int) -> None:
            pass

        def setWorkingDirectory(self, directory: str) -> None:
            pass

        def setProcessEnvironment(self, environment) -> None:
            pass

        def kill(self) -> None:
            pass

        def terminate(self) -> None:
            pass

        def waitForFinished(self, timeout: int = -1) -> bool:
            return True

        def state(self) -> int:
            return QProcess.NotRunning

        def exitCode(self) -> int:
            return 0

    class QTimer:  # type: ignore[no-redef]
        def __init__(self, parent: Any = None) -> None:
            self.timeout: _StubSignal = _StubSignal()

        def start(self, interval: int) -> None:
            pass

        def stop(self) -> None:
            pass

        def setInterval(self, interval: int) -> None:
            pass

    Signal = _StubSignal  # type: ignore[misc, assignment]


# ============================================================================
# E3.17: Transport State Machine
# ============================================================================


class TransportState:
    """
    Transport connection states (E3.17).

    State transitions:
    DISCONNECTED -> CONNECTING -> CONNECTED -> DISCONNECTED
                             |-> ERROR -> DISCONNECTED
    """

    DISCONNECTED = "disconnected"
    CONNECTING = "connecting"
    CONNECTED = "connected"
    ERROR = "error"


VALID_STATE_TRANSITIONS = {
    TransportState.DISCONNECTED: {TransportState.CONNECTING},
    TransportState.CONNECTING: {TransportState.CONNECTED, TransportState.ERROR},
    TransportState.CONNECTED: {TransportState.DISCONNECTED, TransportState.ERROR},
    TransportState.ERROR: {TransportState.DISCONNECTED},
}


# ============================================================================
# E3.18: Large Message Constants
# ============================================================================

# Maximum chunk size for large message handling (64KB)
MAX_CHUNK_SIZE = 65536

# Default timeout for process heartbeat (seconds)
DEFAULT_TIMEOUT_SECONDS = 30


# ============================================================================
# Main Transport Class
# ============================================================================


class ACPTransport(QObject):  # type: ignore[misc]
    """
    Transport layer for ACP communication via QProcess.

    Uses newline-delimited JSON over stdio to communicate with the
    AgentPool server process.

    Signals:
        messageReceived(dict): Emitted when a complete JSON message is received.
        stderrReceived(str): Emitted when stderr output is received.
        stateChanged(str): Emitted when connection state changes.
        processError(str): Emitted when a process error occurs.
        processFinished(int): Emitted when process terminates with exit code.
    """

    # E3.7: Signal emitted when a complete JSON message is received
    messageReceived = Signal(dict)

    # E3.4: Signal emitted when stderr output is received
    stderrReceived = Signal(str)

    # E3.17: Signal emitted when state changes
    stateChanged = Signal(str)

    # E3.10: Signal emitted when an error occurs
    processError = Signal(str)

    # E3.9: Signal emitted when process finishes
    processFinished = Signal(int)

    def __init__(self, python_exe=None, boot_script=None, timeout_seconds=None, working_dir=None, environment=None):
        """
        Initialize the transport.

        Args:
            python_exe: Path to Python executable (validated in start()).
            boot_script: Path to boot.py script (validated in start()).
            timeout_seconds: Timeout for heartbeat detection (E3.16).
            working_dir: Working directory for the spawned process.
        """
        super(ACPTransport, self).__init__()
        self._python_exe = python_exe
        self._boot_script = boot_script
        self._working_dir = working_dir
        self._environment = dict(environment or {})
        self._process = None
        self._stopping = False

        # E3.5: JSON-line protocol buffer
        self._buffer = ""
        self._stdout_decoder = codecs.getincrementaldecoder("utf-8")()
        self._stderr_decoder = codecs.getincrementaldecoder("utf-8")(errors="replace")
        self._stdout_failed = False
        self._pending = {}

        # E3.17: State machine
        self._state = TransportState.DISCONNECTED

        # E3.16: Timeout detection
        self._timeout_seconds = timeout_seconds or DEFAULT_TIMEOUT_SECONDS
        self._timeout_timer = None

        # E3.19: Debug logging hooks
        self._debug_enabled = False
        self._debug_callback = None

        # E3.13: Reconnect state
        self._reconnect_requested = False
        self._reconnect_count = 0
        self._max_reconnects = 3
        self._reconnect_timer = None

    # ========================================================================
    # E3.19: Debug Logging Hooks
    # ========================================================================

    def enable_debug(self, callback=None):
        """
        Enable debug logging.

        Args:
            callback: Optional callable for debug messages. If None, uses print.
        """
        self._debug_enabled = True
        self._debug_callback = callback

    def disable_debug(self):
        """Disable debug logging."""
        self._debug_enabled = False
        self._debug_callback = None

    def _debug(self, message):
        """
        Log a debug message if debugging is enabled.

        Args:
            message: Debug message string.
        """
        if not self._debug_enabled:
            return

        formatted = "[ACPTransport] %s" % message
        if self._debug_callback is not None:
            self._debug_callback(formatted)
        else:
            print(formatted)

    # ========================================================================
    # E3.17: State Machine
    # ========================================================================

    def state(self):
        """
        Get the current transport state.

        Returns:
            str: One of TransportState values.
        """
        return self._state

    def _set_state(self, new_state):
        """
        Update transport state and emit signal.

        Args:
            new_state: New TransportState value.

        Validates transition against VALID_STATE_TRANSITIONS (E6.21).
        Invalid transitions are logged but allowed to prevent deadlock.
        """
        if self._state == new_state:
            return

        valid_next = VALID_STATE_TRANSITIONS.get(self._state, set())
        if new_state not in valid_next:
            self._debug(
                "Invalid state transition: %s -> %s (expected one of %s)"
                % (self._state, new_state, valid_next)
            )

        old_state = self._state
        self._state = new_state
        self._debug("State: %s -> %s" % (old_state, new_state))
        self.stateChanged.emit(new_state)

    def is_connected(self):
        """
        Check if transport is in connected state.

        Returns:
            bool: True if connected.
        """
        return self._state == TransportState.CONNECTED

    # ========================================================================
    # E3.11 & E3.12: Path Validation
    # ========================================================================

    def _validate_python_path(self, python_exe):
        """
        Validate that Python executable exists and is executable (E3.11).

        Args:
            python_exe: Path to Python executable.

        Returns:
            tuple: (is_valid, error_message or None)
        """
        if python_exe is None:
            return (False, "Python executable path is None")

        if not os.path.exists(python_exe):
            return (False, "Python executable not found: %s" % python_exe)

        if not os.path.isfile(python_exe):
            return (False, "Python path is not a file: %s" % python_exe)

        if not os.access(python_exe, os.X_OK):
            return (False, "Python executable not executable: %s" % python_exe)

        return (True, None)

    def _validate_boot_script(self, boot_script):
        """
        Validate that boot script exists and is readable (E3.12).

        Args:
            boot_script: Path to boot.py script.

        Returns:
            tuple: (is_valid, error_message or None)
        """
        if boot_script is None:
            return (False, "Boot script path is None")

        if not os.path.exists(boot_script):
            return (False, "Boot script not found: %s" % boot_script)

        if not os.path.isfile(boot_script):
            return (False, "Boot script is not a file: %s" % boot_script)

        if not os.access(boot_script, os.R_OK):
            return (False, "Boot script not readable: %s" % boot_script)

        return (True, None)

    def set_paths(self, python_exe, boot_script):
        """
        Set Python executable and boot script paths.

        Args:
            python_exe: Path to Python executable.
            boot_script: Path to boot.py script.
        """
        self._python_exe = python_exe
        self._boot_script = boot_script

    # ========================================================================
    # E3.1: QProcess Spawn with Args
    # ========================================================================

    def start(self, extra_args=None):
        """
        Start the AgentPool server process (E3.1).

        Args:
            extra_args: Optional list of additional command-line arguments.

        Returns:
            tuple: (success, error_message or None)
        """
        if self._stopping or self._state != TransportState.DISCONNECTED:
            return (False, "Transport already active (state: %s)" % self._state)

        # E3.11: Validate Python path
        valid, error = self._validate_python_path(self._python_exe)
        if not valid:
            self._set_state(TransportState.ERROR)
            self.processError.emit(error)
            return (False, error)

        # E3.12: Validate boot script path
        valid, error = self._validate_boot_script(self._boot_script)
        if not valid:
            self._set_state(TransportState.ERROR)
            self.processError.emit(error)
            return (False, error)

        self._set_state(TransportState.CONNECTING)
        self._reset_protocol()

        self._process = QProcess(self)
        if self._environment:
            environment = QProcessEnvironment.systemEnvironment()
            for name, value in self._environment.items():
                environment.insert(name, value)
            self._process.setProcessEnvironment(environment)

        if self._working_dir:
            self._process.setWorkingDirectory(str(self._working_dir))

        # E3.2: Set channel mode to separate stdout and stderr
        self._process.setProcessChannelMode(QProcess.SeparateChannels)

        # E3.3: Connect stdout signal
        self._process.readyReadStandardOutput.connect(self._on_stdout_ready)

        # E3.4: Connect stderr signal
        self._process.readyReadStandardError.connect(self._on_stderr_ready)

        # E3.9: Connect finished signal
        self._process.finished.connect(self._on_finished)

        # E3.10: Connect error signal (different attribute names in Qt versions)
        if hasattr(self._process, "errorOccurred"):
            self._process.errorOccurred.connect(self._on_error)
        elif hasattr(self._process, "error") and callable(
            getattr(self._process.error, "connect", None)
        ):
            self._process.error.connect(self._on_error)

        # Build command arguments
        python_path: str = str(self._python_exe)
        boot_path: str = str(self._boot_script)
        args: List[str] = [boot_path]
        if extra_args:
            args.extend(extra_args)

        self._debug("Starting process: %s %s" % (python_path, " ".join(args)))

        # Start process
        process = self._process
        process.start(python_path, args)
        if not process.waitForStarted(3000) or self._process is not process or self._state == TransportState.ERROR:
            error = "Core process failed to start"
            self._set_state(TransportState.ERROR)
            self.processError.emit(error)
            return (False, error)

        # E3.16: Start timeout detection timer
        self._start_timeout_timer()

        # Transition to connected state (actual confirmation would come from init message)
        self._set_state(TransportState.CONNECTED)
        return (True, None)

    # ========================================================================
    # E3.14: Graceful Shutdown
    # ========================================================================

    def stop(self, graceful=True, timeout_ms=5000):
        """
        Stop the server process; return False if termination remains unknown.

        Args:
            graceful: If True, try terminate() before kill().
            timeout_ms: Timeout in milliseconds to wait for graceful shutdown.
        """
        self._stop_timeout_timer()
        self._reconnect_requested = False
        self._stopping = True

        if self._process is None:
            self._reset_protocol()
            self._set_state(TransportState.DISCONNECTED)
            self._stopping = False
            return True

        process = self._process
        self._debug("Stopping process (graceful=%s)" % graceful)

        finished = False
        if graceful:
            # Closing ACP stdin lets AgentPool unwind native MCP children.
            # Retain a local QProcess reference: finished can reenter stop.
            if callable(getattr(process, "closeWriteChannel", None)):
                process.closeWriteChannel()
                finished = process.waitForFinished(timeout_ms)
            else:
                finished = False
            if not finished:
                process.terminate()
                finished = process.waitForFinished(1000)
        if not finished:
            process.kill()
            finished = process.waitForFinished(1000)
        if not finished and self._process is process:
            self._stopping = False
            self._set_state(TransportState.ERROR)
            self.processError.emit("Brain termination outcome unknown; process retained, reconnect refused")
            return False

        self._process = None
        self._reset_protocol()
        self._set_state(TransportState.DISCONNECTED)
        self._stopping = False
        return True

    # ========================================================================
    # E3.13: Reconnect Logic
    # ========================================================================

    def request_reconnect(self):
        """
        Request a reconnection attempt with exponential backoff (E3.13, E8.14).

        The actual reconnection is performed asynchronously after a delay.
        Delay: 1s, 2s, 4s for attempts 1, 2, 3.
        """
        if self._reconnect_count >= self._max_reconnects:
            self._debug("Max reconnect attempts reached")
            self.processError.emit("Max reconnect attempts (%d) exceeded" % self._max_reconnects)
            return

        self._reconnect_count += 1

        delay_ms = 1000 * (2 ** (self._reconnect_count - 1))
        self._debug(
            "Reconnect scheduled in %dms (attempt %d/%d)"
            % (delay_ms, self._reconnect_count, self._max_reconnects)
        )

        if self.stop(graceful=False, timeout_ms=1000) is False:
            return
        self._reconnect_requested = True

        if self._reconnect_timer is None:
            self._reconnect_timer = QTimer(self)
            self._reconnect_timer.timeout.connect(self._do_reconnect)

        self._reconnect_timer.start(delay_ms)

    def _do_reconnect(self):
        """Execute the actual reconnection after backoff delay (E8.14)."""
        if self._reconnect_timer is not None:
            self._reconnect_timer.stop()

        if not self._reconnect_requested:
            return

        self._debug("Executing reconnect attempt %d" % self._reconnect_count)
        success, error = self.start()
        if not success:
            self.processError.emit("Reconnect failed: %s" % error)

    def reset_reconnect_count(self):
        """Reset the reconnect counter (call after successful stable connection)."""
        self._reconnect_count = 0

    # ========================================================================
    # E3.16: Timeout Detection
    # ========================================================================

    def _start_timeout_timer(self):
        """Check outstanding request deadlines; an idle connection has no deadline."""
        if self._timeout_timer is None:
            self._timeout_timer = QTimer(self)
            self._timeout_timer.timeout.connect(self._check_timeout)

        # Check every second
        self._timeout_timer.start(1000)

    def _stop_timeout_timer(self):
        """Stop the request deadline timer."""
        if self._timeout_timer is not None:
            self._timeout_timer.stop()

    def _check_timeout(self):
        """Check if the process has been unresponsive."""
        if self._state != TransportState.CONNECTED or not self._pending:
            return

        elapsed = time.monotonic() - min(value[0] for value in self._pending.values())
        if elapsed > self._timeout_seconds:
            self._debug("Process timeout detected (%.1f seconds)" % elapsed)
            self._set_state(TransportState.ERROR)
            self.processError.emit(
                "Request unresponsive for %.1f seconds; outcome unknown" % elapsed
            )

    def _reset_protocol(self):
        """Discard connection-local framing and outstanding work, without replay."""
        self._buffer = ""
        self._stdout_decoder.reset()
        self._stderr_decoder.reset()
        self._stdout_failed = False
        self._pending.clear()

    def _record_progress(self, message):
        """Correlate responses and ACP session progress before emitting callbacks."""
        if "method" not in message and ("result" in message or "error" in message):
            self._pending.pop(message.get("id"), None)
        elif message.get("method") in ("session/update", "session.update"):
            session = message.get("params", {}).get("sessionId")
            for request_id, (_, method, request_session) in list(self._pending.items()):
                if session is not None and session == request_session and method in (
                    "session/prompt", "session.prompt"
                ):
                    self._pending[request_id] = (time.monotonic(), method, session)

    # ========================================================================
    # E3.8: Send Method with JSON Encoding
    # ========================================================================

    def send(self, message):
        """
        Send a JSON message to the server (E3.8).

        Args:
            message: Dictionary to send as JSON.

        Returns:
            bool: True if message was sent successfully.
        """
        if self._process is None:
            self._debug("Cannot send: process is None")
            return False

        if self._state != TransportState.CONNECTED:
            self._debug("Cannot send: not connected (state: %s)" % self._state)
            return False

        try:
            # E3.15: UTF-8 encoding
            data = json.dumps(message, ensure_ascii=False) + "\n"
            encoded = data.encode("utf-8")
            if "id" in message and "method" in message:
                self._pending[message["id"]] = (
                    time.monotonic(), message["method"],
                    message.get("params", {}).get("sessionId")
                )

            # E3.18: Handle large messages
            if len(encoded) > MAX_CHUNK_SIZE:
                self._debug("Sending large message (%d bytes) in chunks" % len(encoded))
                self._send_chunked(encoded)
            else:
                self._process.write(encoded)

            self._debug("Sent: %s" % (data[:100] + "..." if len(data) > 100 else data.strip()))
            return True

        except (ValueError, TypeError) as e:
            self._debug("JSON encode error: %s" % str(e))
            self.processError.emit("Failed to encode message: %s" % str(e))
            return False

    def _send_chunked(self, encoded_data: bytes) -> None:
        """Send large data in chunks (E3.18)."""
        if self._process is None:
            return
        offset = 0
        while offset < len(encoded_data):
            chunk = encoded_data[offset : offset + MAX_CHUNK_SIZE]
            self._process.write(chunk)
            offset += MAX_CHUNK_SIZE

    # ========================================================================
    # E3.3: readyReadStandardOutput Handler
    # ========================================================================

    def _on_stdout_ready(self):
        """Handle incoming data from stdout (E3.3)."""
        if self._process is None:
            return

        data = self._process.readAllStandardOutput()
        if hasattr(data, "data"):
            data = data.data()
        if not data or self._stdout_failed:
            return

        # E3.15: UTF-8 decoding
        try:
            text = self._stdout_decoder.decode(data)
        except UnicodeDecodeError:
            self._stdout_failed = True
            self._set_state(TransportState.ERROR)
            self.processError.emit("Invalid UTF-8 in ACP stdout; request outcome unknown")
            return

        # E3.5 & E3.18: Add to buffer (handles large messages split across reads)
        self._buffer += text

        # E3.6: Process complete lines
        self._process_buffer()

    def _process_buffer(self):
        """
        Process the buffer to extract complete JSON messages (E3.5, E3.6).

        Handles messages that may be split across multiple reads (E3.18).
        """
        while "\n" in self._buffer:
            line, self._buffer = self._buffer.split("\n", 1)
            line = line.strip()

            if not line:
                continue

            try:
                # E3.6: Parse JSON
                message = json.loads(line)
                self._record_progress(message)

                # E3.7: Emit signal
                self._debug("Received: %s" % (line[:100] + "..." if len(line) > 100 else line))
                self.messageReceived.emit(message)

            except ValueError:
                # JSON decode error - log but don't crash
                self._debug(
                    "JSON parse error: %s" % (line[:50] + "..." if len(line) > 50 else line)
                )

    # ========================================================================
    # E3.4: readyReadStandardError Handler
    # ========================================================================

    def _on_stderr_ready(self):
        """Handle incoming data from stderr (E3.4)."""
        if self._process is None:
            return

        data = self._process.readAllStandardError()
        if hasattr(data, "data"):
            data = data.data()
        if not data:
            return

        # E3.15: UTF-8 decoding
        text = self._stderr_decoder.decode(data)

        self._debug("stderr: %s" % text.strip())
        self.stderrReceived.emit(text)

    # ========================================================================
    # E3.9: Finished Signal Handler
    # ========================================================================

    def _on_finished(self, exit_code, exit_status=None):
        """
        Handle process termination (E3.9).

        Args:
            exit_code: Process exit code.
        """
        self._stop_timeout_timer()
        if not self._stdout_failed:
            try:
                self._buffer += self._stdout_decoder.decode(b"", final=True)
                if self._buffer.strip():
                    raise ValueError("Incomplete ACP frame")
            except (UnicodeDecodeError, ValueError):
                self.processError.emit("Incomplete ACP stdout at EOF; request outcome unknown")
        stderr_tail = self._stderr_decoder.decode(b"", final=True)
        if stderr_tail:
            self.stderrReceived.emit(stderr_tail)
        self._reset_protocol()
        self._debug("Process finished with exit code: %d" % exit_code)

        self._process = None
        self._set_state(TransportState.DISCONNECTED)

        self.processFinished.emit(exit_code)

    # ========================================================================
    # E3.10: Error Signal Handler
    # ========================================================================

    def _on_error(self, error):
        """
        Handle process errors (E3.10).

        Args:
            error: QProcess.ProcessError value.
        """
        error_messages = {
            0: "FailedToStart",
            1: "Crashed",
            2: "Timedout",
            3: "WriteError",
            4: "ReadError",
            5: "UnknownError",
        }
        error_name = error_messages.get(error, "Unknown(%d)" % error)
        self._debug("Process error: %s" % error_name)

        self._set_state(TransportState.ERROR)
        self.processError.emit("Process error: %s" % error_name)

        # Recovery is client-owned: never restart without a new ACP session.
