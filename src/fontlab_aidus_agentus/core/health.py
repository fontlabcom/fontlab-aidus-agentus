# this_file: src/fontlab_aidus_agentus/core/health.py
# Copyright 2025 Fontlab Ltd. All rights reserved.
from __future__ import annotations

import importlib.metadata
from dataclasses import dataclass
from pathlib import Path

from .config import validate_agents_yml


@dataclass
class HealthStatus:
    status: str
    version: str
    config_valid: bool
    agent_count: int
    default_agent: str
    error: str | None = None

    def to_dict(self) -> dict:
        return {
            "status": self.status,
            "version": self.version,
            "config_valid": self.config_valid,
            "agent_count": self.agent_count,
            "default_agent": self.default_agent,
            "error": self.error,
        }


def get_version() -> str:
    """Installed fontlab-aidus-agentus version, or 0.0.0-dev for an uninstalled checkout."""
    try:
        return importlib.metadata.version("fontlab-aidus-agentus")
    except importlib.metadata.PackageNotFoundError:
        return "0.0.0-dev"


def check_health(config_path: Path | None = None) -> HealthStatus:
    version = get_version()

    if config_path is None:
        from .boot import get_config_path

        config_path = Path(get_config_path())

    try:
        schema = validate_agents_yml(config_path)
        return HealthStatus(
            status="healthy",
            version=version,
            config_valid=True,
            agent_count=len(schema.agents),
            default_agent=schema.default_agent,
        )
    except Exception as e:
        return HealthStatus(
            status="unhealthy",
            version=version,
            config_valid=False,
            agent_count=0,
            default_agent="",
            error=str(e),
        )
