# this_file: src/fontlab_aidus_agentus/core/boot.py
# Copyright 2025 Fontlab Ltd. All rights reserved.
"""Aidus Agentus Core — entry point for the AgentPool ACP server.

FontLab 9's embedded PythonQt cannot run modern AI libraries, so the AI brain
lives in a separate process (here) and communicates with the Plugin over
stdin/stdout using JSON-RPC 2.0 (ACP protocol).

This module is launched by the Plugin via QProcess::start(). It:
1. Configures structlog (console format when attached to a tty, JSON otherwise)
2. Reads agents.yml, which defines the three LLM agents and their tools
3. Selects native MCP or plugin tools and starts AgentPool's stdio ACP server

The server runs until the Plugin closes the QProcess pipe.
"""

from __future__ import annotations

import asyncio
import os
import sys
from contextlib import redirect_stdout
from pathlib import Path

import structlog


def configure_logging() -> None:
    """Configure structlog for structured stderr logging."""
    structlog.configure(
        processors=[
            structlog.contextvars.merge_contextvars,
            structlog.processors.add_log_level,
            structlog.processors.StackInfoRenderer(),
            structlog.processors.format_exc_info,
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.dev.ConsoleRenderer()
            if sys.stderr.isatty()
            else structlog.processors.JSONRenderer(),
        ],
        wrapper_class=structlog.make_filtering_bound_logger(20),  # INFO level
        context_class=dict,
        logger_factory=structlog.PrintLoggerFactory(file=sys.stderr),
        cache_logger_on_first_use=True,
    )


def get_config_path() -> str:
    """Return the path to the agents.yml configuration file."""
    return os.environ.get("AIDUS_AGENTS_CONFIG") or os.path.join(os.path.dirname(__file__), "agents.yml")


def main() -> int:
    """
    Main entry point for Aidus Agentus Core.

    Starts the AgentPool ACP server using the fontlab_copilot agent
    configuration. Communication happens via stdio.

    Returns:
        Exit code (0 for success, non-zero for failure).
    """
    configure_logging()
    log = structlog.get_logger()

    try:
        asyncio.run(serve())
        return 0
    except ImportError as e:
        log.error("import_failed", error=str(e), hint="Run 'uv sync' to install dependencies")
        return 1
    except Exception as e:
        log.exception("startup_failed", error=str(e))
        return 1


async def serve() -> None:
    """Select a reachable FontLab backend and run AgentPool's supported ACP server."""
    from agentpool import AgentPool
    from agentpool.models.manifest import AgentsManifest

    from fontlab_aidus_agentus.core.acp_server import serve_stdio
    from fontlab_aidus_agentus.core.fontlab_mcp import build_manifest, discover_server

    server = await discover_server()
    config_path = Path(get_config_path())
    manifest = AgentsManifest.model_validate(build_manifest(config_path, server))
    structlog.get_logger().info("starting_acp_server", backend="mcp" if server else "plugin")
    protocol_output = sys.stdout.buffer
    with redirect_stdout(sys.stderr):
        async with AgentPool(manifest, main_agent_name="fontlab_copilot") as pool:
            await serve_stdio(pool.main_agent, protocol_output)


if __name__ == "__main__":
    sys.exit(main())
