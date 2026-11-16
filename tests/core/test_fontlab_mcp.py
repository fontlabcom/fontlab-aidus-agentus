# this_file: tests/core/test_fontlab_mcp.py
"""Verify discovery, role isolation and real AgentPool configuration."""

from pathlib import Path
from unittest.mock import AsyncMock

import pytest
from mcp.types import Tool

from fontlab_aidus_agentus.core import fontlab_mcp
from fontlab_aidus_agentus.core.boot import get_config_path


def test_find_bridge_when_explicit_path_has_spaces(monkeypatch, tmp_path):
    bridge = tmp_path / "FontLab 9" / "fontlab-mcp"
    bridge.parent.mkdir()
    bridge.write_text("#!/bin/sh\n")
    bridge.chmod(0o755)
    monkeypatch.setenv("AIDUS_FONTLAB_MCP_COMMAND", str(bridge))
    assert fontlab_mcp.find_bridge() == str(bridge)


def test_find_bridge_when_override_missing_does_not_use_other_build(monkeypatch):
    monkeypatch.setenv("AIDUS_FONTLAB_MCP_COMMAND", "/missing/fontlab-mcp")
    assert fontlab_mcp.find_bridge() is None


@pytest.mark.asyncio
async def test_discovery_when_disabled_does_not_spawn(monkeypatch):
    monkeypatch.setenv("AIDUS_FONTLAB_MCP", "off")
    probe = AsyncMock()
    monkeypatch.setattr(fontlab_mcp, "probe_tools", probe)
    assert await fontlab_mcp.discover_server() is None
    probe.assert_not_called()


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "failure", [OSError("missing"), TimeoutError(), ExceptionGroup("rpc", [ValueError("auth")])]
)
async def test_discovery_when_unavailable_returns_legacy_backend(monkeypatch, failure):
    monkeypatch.setattr(fontlab_mcp, "find_bridge", lambda: "/bridge")
    monkeypatch.setattr(fontlab_mcp, "probe_tools", AsyncMock(side_effect=failure))
    assert await fontlab_mcp.discover_server() is None


@pytest.mark.asyncio
async def test_discovery_when_active_returns_catalogue(monkeypatch):
    tools = [Tool(name="list_fonts", inputSchema={"type": "object"})]
    monkeypatch.setattr(fontlab_mcp, "find_bridge", lambda: "/bridge")
    monkeypatch.setattr(fontlab_mcp, "probe_tools", AsyncMock(return_value=tools))
    assert await fontlab_mcp.discover_server() == ("/bridge", tools)


def test_runtime_manifest_when_active_scopes_tools_and_resolves_prompt():
    from agentpool.models.manifest import AgentsManifest

    tools = [
        Tool(name=name, inputSchema={"type": "object"})
        for name in [
            "list_fonts",
            "get_glyph",
            "set_glyph_metrics",
            "run_python",
            "future_mutation",
        ]
    ]
    manifest = fontlab_mcp.build_manifest(Path(get_config_path()), ("/bridge", tools))
    parsed = AgentsManifest.model_validate(manifest)
    copilot = parsed.agents["fontlab_copilot"]
    assert copilot.tools == [], "Legacy tools must not shadow MCP schemas"
    assert copilot.mcp_servers[0].enabled_tools is None, "Copilot must use the full catalogue"
    assert parsed.agents["fontlab_analyst"].mcp_servers[0].enabled_tools == [
        "list_fonts",
        "get_glyph",
    ]
    assert "run_python" in parsed.agents["fontlab_coder"].mcp_servers[0].enabled_tools
    assert "set_glyph_metrics" not in parsed.agents["fontlab_coder"].mcp_servers[0].enabled_tools
    assert "FontLab MCP" in copilot.system_prompt


def test_runtime_manifest_when_inactive_registers_plugin_tools():
    from agentpool.models.manifest import AgentsManifest

    parsed = AgentsManifest.model_validate(
        fontlab_mcp.build_manifest(Path(get_config_path()), None)
    )
    agent = parsed.agents["fontlab_copilot"]
    assert agent.mcp_servers == []
    assert [tool.name for tool in agent.tools] == [
        "get_current_glyph_info",
        "set_glyph_metrics",
        "run_fontlab_script",
    ]
