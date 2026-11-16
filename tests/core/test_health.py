# this_file: tests/core/test_health.py
from __future__ import annotations

from pathlib import Path

from fontlab_aidus_agentus.core import boot
from fontlab_aidus_agentus.core.health import HealthStatus, check_health, get_version


def test_get_version_returns_string():
    version = get_version()
    assert isinstance(version, str)
    assert len(version) > 0


def test_check_health_with_valid_config():
    config_path = Path(boot.__file__).with_name("agents.yml")
    status = check_health(config_path)
    assert status.status == "healthy"
    assert status.config_valid is True
    assert status.agent_count >= 1
    assert status.default_agent == "fontlab_copilot"


def test_check_health_with_invalid_path():
    status = check_health(Path("/nonexistent/config.yml"))
    assert status.status == "unhealthy"
    assert status.config_valid is False
    assert status.error is not None


def test_health_status_to_dict():
    status = HealthStatus(
        status="healthy",
        version="1.0.0",
        config_valid=True,
        agent_count=3,
        default_agent="test_agent",
    )
    result = status.to_dict()
    assert result["status"] == "healthy"
    assert result["version"] == "1.0.0"
    assert result["agent_count"] == 3
