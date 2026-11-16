# this_file: src/fontlab_aidus_agentus/core/acp_server.py
"""Use AgentPool's ACP implementation without unrelated model discovery at startup."""

from __future__ import annotations

import asyncio
from functools import partial
from typing import TYPE_CHECKING

from acp import NewSessionRequest, NewSessionResponse, StreamTransport, serve
from acp.stdio import StdinStream, StdoutStream
from agentpool_server.acp_server.acp_agent import AgentPoolACPAgent
from anyio import EndOfStream

if TYPE_CHECKING:
    from typing import BinaryIO

    from agentpool.agents.base_agent import BaseAgent


class ShutdownStdinStream(StdinStream):
    """Signal SDK server shutdown when the plugin closes stdin."""

    def __init__(self, shutdown: asyncio.Event) -> None:
        self.shutdown = shutdown

    async def receive(self, max_bytes: int = 65536) -> bytes:
        try:
            return await super().receive(max_bytes)
        except EndOfStream:
            self.shutdown.set()
            raise


class ProtocolStdoutStream(StdoutStream):
    """Keep the protocol pipe separate from third-party print output."""

    def __init__(self, output: BinaryIO) -> None:
        self.output = output

    def _write(self, data: bytes) -> None:
        self.output.write(data)
        self.output.flush()


async def serve_stdio(agent: BaseAgent, output: BinaryIO) -> None:
    """Let the SDK own framing and dispatch while bounding its process lifetime."""
    shutdown = asyncio.Event()
    transport = StreamTransport(
        reader=ShutdownStdinStream(shutdown), writer=ProtocolStdoutStream(output)
    )
    factory = partial(AidusACPAgent, default_agent=agent, load_skills=False)
    await serve(factory, transport=transport, shutdown_event=shutdown)


class AidusACPAgent(AgentPoolACPAgent):
    """Aidus selects its models in agents.yml, with no model-picker UI."""

    async def new_session(self, params: NewSessionRequest) -> NewSessionResponse:
        """Create the SDK session without fetching global model catalogues."""
        if not self._initialized:
            raise RuntimeError("Agent not initialized")
        session_id = await self.session_manager.create_session(
            agent=self.default_agent,
            cwd=params.cwd,
            client=self.client,
            acp_agent=self,
            mcp_servers=params.mcp_servers,
            client_capabilities=self.client_capabilities,
            client_info=self.client_info,
        )
        return NewSessionResponse(session_id=session_id)
