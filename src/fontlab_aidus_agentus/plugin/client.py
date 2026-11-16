# this_file: src/fontlab_aidus_agentus/plugin/client.py
# Copyright 2025 Fontlab Ltd. All rights reserved.
"""ACP client: manages the JSON-RPC session between the Plugin and the Core.

The Plugin (running inside FontLab's PythonQt) uses this client to talk to
the Core process over a QProcess stdio pipe. The wire format is newline-
delimited JSON (JSON-RPC 2.0).

State machine (7 states):
    DISCONNECTED → INITIALIZING → INITIALIZED → SESSION_PENDING → READY
                                                                  ↕
                                                               WAITING
                                                               ↕
                                                            ERROR → DISCONNECTED

Signals emitted (connect these in the UI layer):
    chatUpdate(role, content)   — streamed LLM tokens and tool results
    stateChanged(new_state)     — so the UI can show connection status
    errorOccurred(code, msg)    — surfaced to the user as actionable hints

All calls into FontLab's sandbox go through the Executor, not through this
client. This client only handles the ACP wire protocol.
"""

from __future__ import annotations

import json
import os
from typing import TYPE_CHECKING, Any, Callable, Dict, List, Optional

if TYPE_CHECKING:
    from fontlab_aidus_agentus.plugin.transport import ACPTransport

try:
    import PythonQt
except ModuleNotFoundError as exc:
    if exc.name != "PythonQt":
        raise
    PythonQt = None

if PythonQt is not None:
    from PythonQt.QtCore import Signal
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

    Signal = _StubSignal  # type: ignore[misc, assignment]


class ClientState:
    """Client state machine states (E4.17)."""

    DISCONNECTED = "disconnected"
    INITIALIZING = "initializing"
    INITIALIZED = "initialized"
    SESSION_PENDING = "session_pending"
    READY = "ready"
    WAITING = "waiting"
    ERROR = "error"


class AidusAgentusClient(QObject):  # type: ignore[misc]
    """
    ACP client that manages communication with the AgentPool server.

    Implements JSON-RPC 2.0 protocol for:
    - Protocol initialization and negotiation
    - Session lifecycle (create, prompt, cleanup)
    - Message routing and parsing
    - Tool call dispatch and result handling
    """

    # E4.16: Chat update signal (role, content)
    # Roles: user, assistant, system, error, tool, tool_result
    chatUpdate = Signal(str, str)

    # E4.17: State change signal
    stateChanged = Signal(str)

    # E4.15: Error signal
    errorOccurred = Signal(str, str)  # (error_code, error_message)

    def __init__(
        self,
        transport: Optional[ACPTransport] = None,
        executor: Optional[Any] = None,
    ) -> None:
        """Initialize the ACP client."""
        super(AidusAgentusClient, self).__init__()
        self._transport = transport
        self._executor = executor
        self._request_id = 0
        self._session_id: Optional[str] = None
        self._modern_acp = True
        self._assistant_chunks = []

        # E4.17: State machine
        self._state = ClientState.DISCONNECTED

        # E4.15: Pending requests for response correlation
        self._pending_requests: Dict[int, str] = {}

        # E4.19: Batch tool call accumulator
        self._pending_tool_results: List[Dict[str, Any]] = []
        self._batch_mode = False

        # Connect transport message signal if available
        if self._transport is not None:
            self._transport.messageReceived.connect(self._handle_message)
            self._transport.processError.connect(self._handle_transport_error)
            self._transport.processFinished.connect(self._handle_process_finished)

    # ==========================================================================
    # E4.17: State Machine
    # ==========================================================================

    @property
    def transport(self) -> Optional[ACPTransport]:
        """Expose the transport without requiring UI access to private state."""
        return self._transport

    def reconnect(self) -> bool:
        """Start a fresh ACP session; discard pending requests without replay."""
        if self._transport is None:
            return False
        if self._transport.stop() is False:
            return False
        self.reset()
        success, error = self._transport.start()
        if not success:
            self._handle_transport_error(error or "Reconnect failed")
            return False
        return self.initialize()

    def _handle_process_finished(self, exit_code: int) -> None:
        """An ended child cannot retain a live ACP session."""
        self.reset()

    def state(self) -> str:
        return self._state

    def _set_state(self, new_state: str) -> None:
        if self._state != new_state:
            self._state = new_state
            self.stateChanged.emit(new_state)

    def is_ready(self) -> bool:
        return self._state == ClientState.READY

    # ==========================================================================
    # E4.05: Request ID Generation
    # ==========================================================================

    def _next_request_id(self) -> int:
        self._request_id += 1
        return self._request_id

    # ==========================================================================
    # E4.14: JSON-RPC Request Builder
    # ==========================================================================

    def _build_request(
        self, method: str, params: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Build a JSON-RPC 2.0 request."""
        request_id = self._next_request_id()
        request: Dict[str, Any] = {
            "jsonrpc": "2.0",
            "id": request_id,
            "method": method.replace("session.", "session/") if self._modern_acp else method,
        }
        if params is not None:
            request["params"] = params
        return request

    def _send_request(self, method: str, params: Optional[Dict[str, Any]] = None) -> bool:
        """Send a JSON-RPC 2.0 request to the server."""
        if self._transport is None:
            return False

        request = self._build_request(method, params)
        self._pending_requests[request["id"]] = method
        return self._transport.send(request)

    # ==========================================================================
    # E4.02: Initialize Protocol
    # ==========================================================================

    def initialize(self) -> bool:
        """Send ACP initialization request (E4.02)."""
        if self._state not in (ClientState.DISCONNECTED, ClientState.ERROR):
            return False

        self._set_state(ClientState.INITIALIZING)

        success = self._send_request(
            "initialize",
            {
                "protocolVersion": 1,
                "clientInfo": {"name": "aidus-agentus-plugin", "version": "0.1.0"},
                "clientCapabilities": {
                    "fs": {"readTextFile": False, "writeTextFile": False},
                    "terminal": False,
                },
            },
        )

        if not success:
            self._set_state(ClientState.ERROR)
            self.errorOccurred.emit("SEND_FAILED", "Failed to send initialize request")

        return success

    # ==========================================================================
    # E4.03 & E4.04: Session Management
    # ==========================================================================

    def _request_session(self) -> bool:
        """Request a new session after initialization (E4.03)."""
        if self._state != ClientState.INITIALIZED:
            return False

        self._set_state(ClientState.SESSION_PENDING)
        params = {"cwd": os.getcwd(), "mcpServers": []} if self._modern_acp else {}
        return self._send_request("session.new", params)

    def session_id(self) -> Optional[str]:
        """Get current session ID (E4.04)."""
        return self._session_id

    def has_session(self) -> bool:
        """Check if a session is active."""
        return self._session_id is not None

    # ==========================================================================
    # E4.05: Send User Prompt
    # ==========================================================================

    def send_user_prompt(self, text: str) -> bool:
        """Send a user prompt to the agent (E4.05)."""
        if self._state != ClientState.READY:
            self.chatUpdate.emit(
                "error", "Cannot send: client not ready (state: %s)" % self._state
            )
            return False

        if self._session_id is None:
            self.chatUpdate.emit("error", "Cannot send: no active session")
            return False

        self.chatUpdate.emit("user", text)
        self._assistant_chunks = []
        self._set_state(ClientState.WAITING)

        params = {"sessionId": self._session_id}
        if self._modern_acp:
            params["prompt"] = [{"type": "text", "text": text}]
        else:
            params["messages"] = [{"role": "user", "content": [{"type": "text", "text": text}]}]
        success = self._send_request("session.prompt", params)

        if not success:
            self._set_state(ClientState.READY)
            self.chatUpdate.emit("error", "Failed to send message")

        return success

    # ==========================================================================
    # E4.06: Message Routing
    # ==========================================================================

    def _handle_message(self, message: Dict[str, Any]) -> None:
        """Route incoming messages from the server (E4.06)."""
        if "method" in message and "id" in message:
            self._handle_server_request(message)
            return
        # Handle RPC responses
        if "id" in message and "result" in message:
            self._handle_response(message)
            return

        # Handle RPC errors
        if "id" in message and "error" in message:
            self._handle_error_response(message)
            return

        # Handle notifications (no id)
        if "method" in message and "id" not in message:
            self._handle_notification(message)
            return

    # ==========================================================================
    # E4.07 & E4.08: Response Handlers
    # ==========================================================================

    def _handle_response(self, message: Dict[str, Any]) -> None:
        """Handle successful RPC responses (E4.07, E4.08)."""
        msg_id = message.get("id")
        result = message.get("result", {})

        # Get the original method for this request
        method = self._pending_requests.pop(msg_id, None) if msg_id is not None else None

        # E4.07: Initialize response with version check (E7.15)
        if method == "initialize" and "protocolVersion" in result:
            self._modern_acp = isinstance(result["protocolVersion"], int)
            if not self._modern_acp:
                server_info = result.get("serverInfo", {})
                core_version = server_info.get("version", "0.0.0")
                self._check_version_compatibility(core_version)
            self._set_state(ClientState.INITIALIZED)
            self._request_session()
            return

        # E4.08: Session response
        if method == "session.new" and "sessionId" in result:
            self._session_id = result["sessionId"]
            self._set_state(ClientState.READY)
            self.chatUpdate.emit("system", "Session ready")
            return

        # Prompt response (agent done thinking)
        if method == "session.prompt":
            self._flush_assistant_chunks()
            self._set_state(ClientState.READY)
            return

    def _check_version_compatibility(self, core_version: str) -> None:
        """Check if core version is compatible with plugin (E7.15)."""
        try:
            from fontlab_aidus_agentus.plugin import __version__ as plugin_version
            from fontlab_aidus_agentus.plugin import is_compatible
        except ImportError:
            return

        if not is_compatible(core_version):
            self.chatUpdate.emit(
                "system",
                "Warning: Core version %s may be incompatible with plugin %s"
                % (core_version, plugin_version),
            )

    # ==========================================================================
    # E4.09: Notification Handler
    # ==========================================================================

    def _handle_notification(self, message: Dict[str, Any]) -> None:
        """Handle server notifications (E4.09)."""
        method = message.get("method", "")
        params = message.get("params", {})

        if method in ("session.update", "session/update"):
            self._handle_update(params)

    def _handle_server_request(self, message: Dict[str, Any]) -> None:
        """Execute fallback tools via the ACP extension, never MCP notifications."""
        method = message["method"]
        params = message.get("params", {})
        response = {"jsonrpc": "2.0", "id": message["id"]}
        if (
            method == "_fontlab/tool"
            and self._session_id is not None
            and params.get("sessionId") == self._session_id
        ):
            response["result"] = self._execute_tool_safely(
                params.get("name", ""), params.get("arguments", {})
            )
        else:
            response["error"] = {
                "code": -32601,
                "message": "Unsupported client request: " + method,
            }
        if self._transport is not None:
            self._transport.send(response)

    def _flush_assistant_chunks(self) -> None:
        """Render a complete assistant message instead of a chat row per token."""
        if self._assistant_chunks:
            self.chatUpdate.emit("assistant", "".join(self._assistant_chunks))
            self._assistant_chunks = []

    # ==========================================================================
    # E4.10 & E4.11: Update Content Parsing
    # ==========================================================================

    def _handle_update(self, params: Dict[str, Any]) -> None:
        """Handle session update notifications (E4.10, E4.11)."""
        update = params.get("update", {})
        if update.get("sessionUpdate") == "agent_message_chunk":
            content = update.get("content", {})
            if content.get("type") == "text" and content.get("text"):
                self._assistant_chunks.append(content["text"])
        if update.get("sessionUpdate") in ("tool_call", "tool_call_update"):
            self.chatUpdate.emit("tool", update.get("title", update.get("status", "Tool update")))
        # E4.10: Text content
        if "content" in params:
            for item in params["content"]:
                if item.get("type") == "text":
                    text = item.get("text", "")
                    if text:
                        self.chatUpdate.emit("assistant", text)

        # E4.11: Tool calls
        if "toolCall" in params:
            self._handle_tool_call(params["toolCall"])

        # E4.19: Batch tool calls
        if "toolCalls" in params:
            self._handle_batch_tool_calls(params["toolCalls"])

    # ==========================================================================
    # E4.12 & E4.13: Tool Dispatch and Results
    # ==========================================================================

    def _handle_tool_call(self, tool_call: Dict[str, Any]) -> None:
        """Dispatch a single tool call (E4.12)."""
        tool_name = tool_call.get("name", "")
        arguments = tool_call.get("arguments", {})
        tool_id = tool_call.get("id", "")

        self.chatUpdate.emit("tool", "Executing: %s" % tool_name)

        result = self._execute_tool_safely(tool_name, arguments)

        self._send_tool_result(tool_id, tool_name, result)

    def _execute_tool_safely(self, tool_name: str, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Execute tool with error handling."""
        if self._executor is None:
            return {"error": "No executor configured"}

        try:
            return self._executor.run(tool_name, arguments)
        except Exception as e:
            return {"error": str(e)}

    def _send_tool_result(self, tool_id: str, tool_name: str, result: Dict[str, Any]) -> None:
        """Send tool result back to server (E4.13)."""
        try:
            result_text = json.dumps(result, ensure_ascii=False)
        except (TypeError, ValueError):
            result_text = str(result)

        self.chatUpdate.emit("tool_result", "[%s] %s" % (tool_name, result_text[:200]))

        self._send_request(
            "session.toolResult",
            {
                "sessionId": self._session_id,
                "toolId": tool_id,
                "result": result,
            },
        )

    # ==========================================================================
    # E4.19: Batch Tool Calls
    # ==========================================================================

    def _handle_batch_tool_calls(self, tool_calls: List[Dict[str, Any]]) -> None:
        """Handle batch tool calls (E4.19)."""
        results: List[Dict[str, Any]] = []

        for tool_call in tool_calls:
            tool_name = tool_call.get("name", "")
            arguments = tool_call.get("arguments", {})
            tool_id = tool_call.get("id", "")

            self.chatUpdate.emit("tool", "Executing: %s" % tool_name)
            result = self._execute_tool_safely(tool_name, arguments)

            results.append({"toolId": tool_id, "result": result})

        # Send all results at once
        self._send_request(
            "session.toolResults",
            {"sessionId": self._session_id, "results": results},
        )

    # ==========================================================================
    # E4.15: Error Handling
    # ==========================================================================

    def _handle_error_response(self, message: Dict[str, Any]) -> None:
        """Handle RPC error responses (E4.15)."""
        self._flush_assistant_chunks()
        msg_id = message.get("id")
        error = message.get("error", {})
        code = str(error.get("code", "UNKNOWN"))
        error_msg = error.get("message", "Unknown error")

        # Clear pending request
        method = self._pending_requests.pop(msg_id, "unknown") if msg_id is not None else "unknown"

        self.errorOccurred.emit(code, error_msg)
        self.chatUpdate.emit("error", "[%s] %s: %s" % (method, code, error_msg))

        # Transition to appropriate state based on error
        if self._state == ClientState.INITIALIZING:
            self._set_state(ClientState.ERROR)
        elif self._state == ClientState.SESSION_PENDING:
            self._set_state(ClientState.INITIALIZED)
        elif self._state == ClientState.WAITING:
            self._set_state(ClientState.READY)

    def _handle_transport_error(self, error_msg: str) -> None:
        """Handle transport-level errors."""
        self._set_state(ClientState.ERROR)
        self.errorOccurred.emit("TRANSPORT", error_msg)
        self.chatUpdate.emit("error", "Transport error: %s" % error_msg)

    # ==========================================================================
    # E4.18: Session Cleanup
    # ==========================================================================

    def cleanup(self) -> None:
        """Clean up session resources (E4.18)."""
        if self._session_id is not None and not self._modern_acp:
            self._send_request("session.end", {"sessionId": self._session_id})

        self._session_id = None
        self._assistant_chunks = []
        self._pending_requests.clear()
        self._pending_tool_results.clear()
        self._set_state(ClientState.DISCONNECTED)

    def reset(self) -> None:
        """Reset client to initial state."""
        self._session_id = None
        self._assistant_chunks = []
        self._request_id = 0
        self._pending_requests.clear()
        self._pending_tool_results.clear()
        self._set_state(ClientState.DISCONNECTED)
