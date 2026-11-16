# this_file: tests/test_production_entrypoint.py
"""Installed production entrypoint with real AgentPool TestModel and ACP SDK."""
import asyncio
import json
import os
from pathlib import Path
import sys
import pytest
import yaml
from fontlab_aidus_agentus.core.boot import get_config_path

@pytest.mark.asyncio
async def test_production_entrypoint_initialize_session_prompt_eof(tmp_path):
    config = yaml.safe_load(Path(get_config_path()).read_text())
    for agent in config["agents"].values():
        agent["system_prompt"] = "Reply deterministically."
        agent["model"] = {"type": "test", "custom_output_text": "Installed production ACP complete", "call_tools": []}
        agent["tools"] = []
    cfg = tmp_path / "agents.yml"
    cfg.write_text(yaml.safe_dump(config))
    env = {**os.environ, "AIDUS_AGENTS_CONFIG": str(cfg), "AIDUS_FONTLAB_MCP": "off"}
    p = await asyncio.create_subprocess_exec(sys.executable, "-m", "fontlab_aidus_agentus.boot", env=env,
        stdin=asyncio.subprocess.PIPE, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE)
    errors = asyncio.create_task(p.stderr.read())
    updates = []
    async def request(id, method, params):
        p.stdin.write((json.dumps({"jsonrpc":"2.0", "id":id, "method":method, "params":params})+"\n").encode())
        async with asyncio.timeout(20):
            while True:
                line = await p.stdout.readline()
                assert line, "Production server exited before response"
                response = json.loads(line)
                if "method" in response:
                    updates.append(response)
                    if "id" in response:
                        p.stdin.write((json.dumps({"jsonrpc":"2.0", "id":response["id"], "error":{"code":-32601,"message":"unsupported"}})+"\n").encode())
                    continue
                if response.get("id") == id:
                    assert "result" in response, response
                    return response["result"]
    try:
        init = await request(1, "initialize", {"protocolVersion":1,"clientCapabilities":{}})
        assert init["protocolVersion"] == 1
        session = await request(2, "session/new", {"cwd":str(tmp_path),"mcpServers":[]})
        result = await request(3, "session/prompt", {"sessionId":session["sessionId"],"prompt":[{"type":"text","text":"Hello"}]})
        assert result["stopReason"] == "end_turn"
        text = "".join(u.get("params", {}).get("update", {}).get("content", {}).get("text", "") for u in updates)
        assert "Installed production ACP complete" in text
        p.stdin.close()
        await asyncio.wait_for(p.wait(),5)
        assert p.returncode == 0
    finally:
        if p.returncode is None:
            p.kill()
            await p.wait()
        stderr = (await errors).decode()
        assert "startup_failed" not in stderr, stderr[-5000:]
