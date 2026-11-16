# this_file: src/fontlab_aidus_agentus/core/fontlab_mcp.py
"""Select FontLab's authenticated MCP bridge when its tool catalogue is reachable."""

from __future__ import annotations

import asyncio
import os
import shutil
import sys
from pathlib import Path
from typing import TYPE_CHECKING, Any

import structlog
import yaml
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client
from mcp.types import PaginatedRequestParams

if TYPE_CHECKING:
    from mcp.types import Tool

PROBE_TIMEOUT = 8.0
READ_ONLY_TOOLS = frozenset(
    {
        "get_preferences",
        "list_aidus_files",
        "read_aidus_file",
        "list_fonts",
        "get_active_font",
        "get_font_info",
        "get_font_hinting",
        "list_glyphs",
        "get_current_glyphs",
        "get_active_glyphs",
        "explain",
        "get_glyph",
        "get_layer_hints",
        "get_glyph_nodes",
        "get_font_metrics",
        "get_glyph_metrics",
        "list_kerning_pairs",
        "get_kerning_pair",
        "list_kerning_classes",
        "list_actions",
        "get_python_output",
    }
)
CODER_TOOLS = READ_ONLY_TOOLS | {"run_python"}
MCP_PROMPT = """FontLab MCP is active. Use the discovered native tools and their schemas.
Resolve font, glyph and master IDs from live tool results; never reuse stale IDs.
Prefer dedicated MCP tools to run_python. run_python executes in FontLab's main
Python environment, not the plugin sandbox. Inspect results for errors and verify
edits. Do not retry mutations after a timeout: their outcome may be unknown.
For Python preference changes, prefer direct flPreferences attributes. Use
save()/load() dictionaries only when the needed preference has no direct attribute.
"""


def find_bridge() -> str | None:
    """Delegate executable discovery to the reusable remote-control package."""
    from fontlab_remopy import find_bridge as remote_find_bridge
    return remote_find_bridge(os.environ.get("AIDUS_FONTLAB_MCP_COMMAND"))


async def probe_tools(command: str) -> list[Tool]:
    """Delegate paginated SDK discovery and process cleanup to Remopy."""
    from fontlab_remopy import probe_tools as remote_probe_tools
    return await remote_probe_tools(command, timeout=PROBE_TIMEOUT)


async def discover_server() -> tuple[str, list[Tool]] | None:
    """Return an active bridge/catalogue or select the existing plugin tools."""
    if os.environ.get("AIDUS_FONTLAB_MCP", "auto").lower() == "off":
        return None
    command = find_bridge()
    if command is None:
        return None
    try:
        tools = await probe_tools(command)
    except Exception as exc:
        # SDK task groups wrap connection/RPC errors in ExceptionGroup.
        structlog.get_logger().info("fontlab_mcp_unavailable", reason=str(exc))
        return None
    return (command, tools) if tools else None


def bridge_parameters(command: str) -> StdioServerParameters:
    """Reuse Remopy's SDK relay for the external AgentPool process."""
    from fontlab_remopy import bridge_parameters as remote_parameters
    return remote_parameters(command)


def build_manifest(config_path: Path, server: tuple[str, list[Tool]] | None) -> dict[str, Any]:
    """Translate Aidus's configuration into the installed AgentPool schema."""
    config = yaml.safe_load(config_path.read_text(encoding="utf-8"))
    agents = {}
    for name, source in config["agents"].items():
        prompt = source["system_prompt"]
        if isinstance(prompt, dict):
            prompt = (config_path.parent / prompt["path"]).read_text(encoding="utf-8")
        agent: dict[str, Any] = {
            "type": source["type"],
            "model": source["model"] if isinstance(source["model"], dict) else {
                "type": "string",
                "identifier": source["model"],
                "max_tokens": source["max_tokens"],
                "temperature": source["temperature"],
            },
            "system_prompt": prompt,
            "tools": [],
        }
        if server:
            agent["system_prompt"] += "\n" + MCP_PROMPT
            agent["mcp_servers"] = [server_config(name, *server)]
        else:
            agent["tools"] = [
                {
                    "type": "import",
                    "name": tool["name"],
                    "enabled": tool.get("enabled", True),
                    "import_path": "fontlab_aidus_agentus.core.plugin_tools:" + tool["name"],
                }
                for tool in source.get("tools", [])
            ]
        agents[name] = agent
    return {
        "agents": agents,
        "storage": {"providers": [], "session_store": "memory", "title_generation_model": None},
    }


def server_config(agent_name: str, command: str, tools: list[Tool]) -> dict[str, Any]:
    """Keep the analyst read-only and the coder on its script-focused role."""
    config: dict[str, Any] = {
        "type": "stdio",
        "name": "fontlab",
        "command": sys.executable,
        "args": ["-m", "fontlab_remopy.mcp.relay", command],
        "timeout": 60.0,
    }
    allowed = {"fontlab_analyst": READ_ONLY_TOOLS, "fontlab_coder": CODER_TOOLS}.get(agent_name)
    if allowed is not None:
        config["enabled_tools"] = [tool.name for tool in tools if tool.name in allowed]
    return config
