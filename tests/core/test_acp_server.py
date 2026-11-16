# this_file: tests/core/test_acp_server.py
"""Aidus ACP stdio server: shutdown on stdin EOF, clean protocol pipe, catalogue-free sessions."""

from __future__ import annotations

import asyncio
import io
import sys
from types import SimpleNamespace

import pytest
from acp import NewSessionRequest
from anyio import EndOfStream

from fontlab_aidus_agentus.core import acp_server


@pytest.mark.asyncio
async def test_shutdown_stdin_when_data_then_passthrough_and_event_clear(monkeypatch):
    monkeypatch.setattr(sys, "stdin", SimpleNamespace(buffer=io.BytesIO(b"hello")))
    shutdown = asyncio.Event()
    stream = acp_server.ShutdownStdinStream(shutdown)
    assert await stream.receive() == b"hello"
    assert not shutdown.is_set()


@pytest.mark.asyncio
async def test_shutdown_stdin_when_eof_then_event_set_and_end_of_stream(monkeypatch):
    monkeypatch.setattr(sys, "stdin", SimpleNamespace(buffer=io.BytesIO(b"")))
    shutdown = asyncio.Event()
    stream = acp_server.ShutdownStdinStream(shutdown)
    with pytest.raises(EndOfStream):
        await stream.receive()
    assert shutdown.is_set()


@pytest.mark.asyncio
async def test_protocol_stdout_when_send_then_bytes_go_to_given_pipe_not_stdout(monkeypatch, capfd):
    pipe = io.BytesIO()
    await acp_server.ProtocolStdoutStream(pipe).send(b'{"jsonrpc":"2.0"}\n')
    assert pipe.getvalue() == b'{"jsonrpc":"2.0"}\n'
    assert capfd.readouterr().out == ""


@pytest.mark.asyncio
async def test_serve_stdio_when_called_then_sdk_gets_bounded_transport_and_aidus_agent(monkeypatch):
    captured = {}

    async def fake_serve(factory, *, transport, shutdown_event):
        captured.update(factory=factory, transport=transport, shutdown=shutdown_event)

    class Recorder:
        def __init__(self, client, **kwargs):
            self.client, self.kwargs = client, kwargs

    monkeypatch.setattr(acp_server, "serve", fake_serve)
    monkeypatch.setattr(acp_server, "AidusACPAgent", Recorder)
    output = io.BytesIO()

    await acp_server.serve_stdio("AGENT", output)

    transport = captured["transport"]
    assert isinstance(transport.reader, acp_server.ShutdownStdinStream)
    assert transport.reader.shutdown is captured["shutdown"]
    assert transport.writer.output is output
    built = captured["factory"]("CLIENT")
    assert built.client == "CLIENT"
    assert built.kwargs == {"default_agent": "AGENT", "load_skills": False}


def _agent(initialized: bool):
    agent = object.__new__(acp_server.AidusACPAgent)
    created = {}

    class Sessions:
        async def create_session(self, **kwargs):
            created.update(kwargs)
            return "session-1"

    agent._initialized = initialized
    agent.session_manager = Sessions()
    agent.default_agent = "DEFAULT"
    agent.client = "CLIENT"
    agent.client_capabilities = "CAPS"
    agent.client_info = "INFO"
    return agent, created


@pytest.mark.asyncio
async def test_new_session_when_not_initialized_then_runtime_error():
    agent, created = _agent(False)
    with pytest.raises(RuntimeError, match="not initialized"):
        await agent.new_session(NewSessionRequest(cwd="/tmp", mcp_servers=[]))
    assert created == {}


@pytest.mark.asyncio
async def test_new_session_when_initialized_then_session_uses_default_agent_without_catalogue():
    agent, created = _agent(True)
    response = await agent.new_session(NewSessionRequest(cwd="/work", mcp_servers=[]))
    assert response.session_id == "session-1"
    assert created == {
        "agent": "DEFAULT", "cwd": "/work", "client": "CLIENT", "acp_agent": agent,
        "mcp_servers": [], "client_capabilities": "CAPS", "client_info": "INFO",
    }
