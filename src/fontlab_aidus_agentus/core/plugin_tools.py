# this_file: src/fontlab_aidus_agentus/core/plugin_tools.py
"""AgentPool tools for the existing plugin executor when native MCP is unavailable."""

from __future__ import annotations

import asyncio
from typing import Any

from agentpool import AgentContext  # noqa: TC002 - AgentPool resolves tool annotations at runtime
from agentpool_server.acp_server.input_provider import ACPInputProvider


async def call_plugin(ctx: AgentContext, name: str, arguments: dict[str, Any]) -> dict[str, Any]:
    """Use ACP's extension mechanism to execute a registered plugin tool once."""
    provider = ctx.get_input_provider()
    if not isinstance(provider, ACPInputProvider):
        raise RuntimeError("FontLab plugin tools require an ACP session")
    result = await asyncio.wait_for(
        provider.session.client.ext_method(
            "fontlab/tool",
            {"sessionId": provider.session.session_id, "name": name, "arguments": arguments},
        ),
        timeout=60.0,
    )
    if result.get("error"):
        raise RuntimeError(str(result["error"]))
    return result


async def get_current_glyph_info(ctx: AgentContext) -> dict[str, Any]:
    """Read metrics and properties of the currently selected glyph in FontLab."""
    return await call_plugin(ctx, "get_current_glyph_info", {})


async def set_glyph_metrics(
    ctx: AgentContext, width: int | None = None, lsb: int | None = None, rsb: int | None = None
) -> dict[str, Any]:
    """Set advance width and sidebearings of the current glyph through the plugin."""
    arguments = {
        key: value
        for key, value in {"width": width, "lsb": lsb, "rsb": rsb}.items()
        if value is not None
    }
    return await call_plugin(ctx, "set_glyph_metrics", arguments)


async def run_fontlab_script(ctx: AgentContext, script: str) -> dict[str, Any]:
    """Execute Python in the existing FontLab plugin sandbox."""
    return await call_plugin(ctx, "run_fontlab_script", {"code": script})
