# this_file: tests/core/test_mcp_roundtrip.py
"""Exercise production boot, AgentPool, SDK MCP and the plugin's ACP client."""

import asyncio
import os
import sys
from pathlib import Path
from unittest.mock import Mock

import pytest
from fontlab_aidus_agentus.plugin.client import AidusAgentusClient, ClientState

from fontlab_aidus_agentus.core import fontlab_mcp

FIXTURES = Path(__file__).parent / "fixtures"


@pytest.fixture
def mcp_bridge(tmp_path, monkeypatch):
    bridge = tmp_path / "FontLab fixture bridge"
    bridge.write_text("#!" + sys.executable + "\n" + (FIXTURES / "mcp_server.py").read_text())
    bridge.chmod(0o755)
    monkeypatch.setenv("AIDUS_FONTLAB_MCP_COMMAND", str(bridge))
    monkeypatch.setenv("AIDUS_MCP_TEST_LOG", str(tmp_path / "calls.txt"))
    return bridge


@pytest.mark.asyncio
async def test_production_boot_when_no_mcp_handshakes_and_exits_on_eof():
    import json

    env = {
        **os.environ,
        "AIDUS_FONTLAB_MCP": "off",
        "OPENAI_API_KEY": "sk-test",
        "ANTHROPIC_API_KEY": "sk-ant-test",
    }
    env.pop("PYTEST_CURRENT_TEST", None)
    process = await asyncio.create_subprocess_exec(
        sys.executable,
        "-m",
        "fontlab_aidus_agentus.core.boot",
        env=env,
        stdin=asyncio.subprocess.PIPE,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
        limit=4 * 1024 * 1024,
    )
    stderr_task = asyncio.create_task(process.stderr.read())
    try:
        for request in [
            {
                "jsonrpc": "2.0",
                "id": 1,
                "method": "initialize",
                "params": {"protocolVersion": 1, "clientCapabilities": {}},
            },
            {
                "jsonrpc": "2.0",
                "id": 2,
                "method": "session/new",
                "params": {"cwd": os.getcwd(), "mcpServers": []},
            },
        ]:
            process.stdin.write((json.dumps(request) + "\n").encode())
            async with asyncio.timeout(10):
                while True:
                    line = await process.stdout.readline()
                    assert line, "Production Core exited before handshake completed"
                    response = json.loads(line)
                    if "method" in response and "id" in response:
                        reply = {
                            "jsonrpc": "2.0",
                            "id": response["id"],
                            "error": {"code": -32601, "message": "Unsupported client request"},
                        }
                        process.stdin.write((json.dumps(reply) + "\n").encode())
                        continue
                    if response.get("id") == request["id"]:
                        assert "result" in response, response
                        break
        process.stdin.close()
        await asyncio.wait_for(process.wait(), timeout=5)
        assert process.returncode == 0, "Core should exit successfully when the plugin pipe closes"
    finally:
        if process.returncode is None:
            process.terminate()
            await process.wait()
        stderr = (await stderr_task).decode()
        assert "startup_failed" not in stderr, stderr[-4000:]
        if process.returncode != 0:
            pytest.fail(stderr[-5000:])


@pytest.mark.asyncio
async def test_probe_when_real_stdio_server_discovers_schemas(mcp_bridge):
    tools = await fontlab_mcp.probe_tools(str(mcp_bridge))
    assert {tool.name for tool in tools} == {"list_fonts", "run_python"}
    assert next(tool for tool in tools if tool.name == "run_python").inputSchema["required"] == [
        "code"
    ]


@pytest.mark.asyncio
async def test_probe_when_server_hangs_times_out_and_cleans_up(tmp_path, monkeypatch):
    bridge = tmp_path / "hung-bridge"
    bridge.write_text("#!" + sys.executable + "\nimport time\ntime.sleep(60)\n")
    bridge.chmod(0o755)
    monkeypatch.setattr(fontlab_mcp, "PROBE_TIMEOUT", 0.2)
    with pytest.raises((TimeoutError, ExceptionGroup)):
        await asyncio.wait_for(fontlab_mcp.probe_tools(str(bridge)), timeout=5)


@pytest.mark.asyncio
@pytest.mark.parametrize("backend", ["mcp", "plugin"])
async def test_roundtrip_when_backend_selected_executes_once_and_streams_result(
    mcp_bridge, backend
):
    env = {**os.environ, "AIDUS_FONTLAB_MCP": "auto" if backend == "mcp" else "off"}
    env.pop("PYTEST_CURRENT_TEST", None)
    process = await asyncio.create_subprocess_exec(
        sys.executable,
        str(FIXTURES / "acp_core.py"),
        env=env,
        stdin=asyncio.subprocess.PIPE,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
        limit=4 * 1024 * 1024,
    )
    stderr_task = asyncio.create_task(process.stderr.read())
    transport = Mock()

    def send(message):
        import json

        process.stdin.write((json.dumps(message) + "\n").encode())
        return True

    transport.send.side_effect = send
    executor = Mock()
    executor.run.return_value = {"width": 600, "name": "A"}
    client = AidusAgentusClient(transport=transport, executor=executor)
    client.chatUpdate = Mock()

    async def read_until_ready():
        import json

        async with asyncio.timeout(20):
            while client.state() != ClientState.READY:
                line = await process.stdout.readline()
                assert line, "Core exited before completing ACP exchange"
                client._handle_message(json.loads(line))

    try:
        assert client.initialize()
        await read_until_ready()
        assert client.send_user_prompt(
            "List the fonts" if backend == "mcp" else "Inspect the current glyph"
        )
        await read_until_ready()
        texts = [
            call.args[1]
            for call in client.chatUpdate.emit.call_args_list
            if call.args[0] == "assistant"
        ]
        assert "Roundtrip complete" in "".join(texts), client.chatUpdate.emit.call_args_list
        if backend == "mcp":
            executor.run.assert_not_called()
            assert Path(env["AIDUS_MCP_TEST_LOG"]).read_text() == "list_fonts called"
        else:
            executor.run.assert_called_once_with("get_current_glyph_info", {})
            assert not Path(env["AIDUS_MCP_TEST_LOG"]).exists()
    finally:
        if process.returncode is None:
            process.stdin.close()
        try:
            await asyncio.wait_for(process.wait(), timeout=15)
        except TimeoutError:
            process.kill()
            await process.wait()
            raise
        stderr = (await stderr_task).decode()
        if (
            '"level": "error"' in stderr
            or "Traceback" in stderr
            or process.returncode not in (0, -15)
        ):
            pytest.fail(stderr[-6000:])


def test_server_config_when_generated_then_launches_the_mcp_relay_module():
    config = fontlab_mcp.server_config("other", "/fontlab-mcp", [])
    assert config["command"] == sys.executable
    assert config["args"] == ["-m", "fontlab_remopy.mcp.relay", "/fontlab-mcp"]


def test_server_config_when_relay_module_named_then_it_is_importable():
    import importlib.util

    module = fontlab_mcp.server_config("other", "/fontlab-mcp", [])["args"][1]
    assert module == "fontlab_remopy.mcp.relay"
    assert importlib.util.find_spec(module) is not None, "Remopy >= 1.2.0 must provide the relay"
