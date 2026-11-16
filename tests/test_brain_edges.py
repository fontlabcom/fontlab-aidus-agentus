# this_file: tests/test_brain_edges.py
"""Brain-side (Python 3.13+) error and edge paths: health, boot, config, MCP selection."""

import asyncio
import importlib.metadata
from collections import namedtuple
from pathlib import Path
from types import SimpleNamespace

import pytest

from fontlab_aidus_agentus.core import boot, errors, fontlab_mcp, health, py_version_check
from fontlab_aidus_agentus.core.config import validate_agents_yml

AGENTS = Path(boot.__file__).with_name("agents.yml")


def _versions(table):
    def version(name):
        if name in table:
            return table[name]
        raise importlib.metadata.PackageNotFoundError(name)

    return version


def test_get_version_when_installed_as_fontlab_aidus_agentus_reports_it(monkeypatch):
    monkeypatch.setattr(importlib.metadata, "version", _versions({"fontlab-aidus-agentus": "0.3.0"}))
    assert health.get_version() == "0.3.0"


def test_get_version_when_nothing_installed_is_dev(monkeypatch):
    monkeypatch.setattr(importlib.metadata, "version", _versions({}))
    assert health.get_version() == "0.0.0-dev"


def test_check_health_when_bundled_manifest_is_healthy():
    status = health.check_health(AGENTS)
    assert status.status == "healthy" and status.config_valid and status.agent_count >= 3
    assert status.to_dict()["default_agent"] == status.default_agent


def test_check_health_when_default_path_used_reads_env_override(monkeypatch, tmp_path):
    broken = tmp_path / "agents.yml"
    broken.write_text("default_agent: missing\nagents: {}\n", encoding="utf-8")
    monkeypatch.setenv("AIDUS_AGENTS_CONFIG", str(broken))
    status = health.check_health()
    assert status.status == "unhealthy" and "not in agents" in status.error


@pytest.mark.parametrize("text", ["", "agents: [1, 2]\n", "{{{"])
def test_check_health_when_manifest_malformed_is_unhealthy(tmp_path, text):
    path = tmp_path / "agents.yml"
    path.write_text(text, encoding="utf-8")
    status = health.check_health(path)
    assert status.status == "unhealthy" and status.config_valid is False and status.error


def test_check_health_when_manifest_missing_is_unhealthy(tmp_path):
    assert health.check_health(tmp_path / "nope.yml").status == "unhealthy"


def test_validate_agents_yml_when_default_agent_unknown_raises(tmp_path):
    source = AGENTS.read_text(encoding="utf-8").replace("default_agent:", "default_agent: ghost #", 1)
    path = tmp_path / "agents.yml"
    path.write_text(source, encoding="utf-8")
    with pytest.raises(ValueError, match="ghost"):
        validate_agents_yml(path)


def test_boot_main_when_import_fails_returns_1(monkeypatch):
    async def missing():
        raise ImportError("agentpool")

    monkeypatch.setattr(boot, "serve", missing)
    assert boot.main() == 1


def test_boot_main_when_startup_crashes_returns_1(monkeypatch):
    async def crash():
        raise RuntimeError("no manifest")

    monkeypatch.setattr(boot, "serve", crash)
    assert boot.main() == 1


def test_boot_main_when_server_ends_returns_0(monkeypatch):
    async def done():
        return None

    monkeypatch.setattr(boot, "serve", done)
    assert boot.main() == 0


def test_get_config_path_when_env_unset_uses_bundled_manifest(monkeypatch):
    monkeypatch.delenv("AIDUS_AGENTS_CONFIG", raising=False)
    assert Path(boot.get_config_path()) == AGENTS


def test_discover_server_when_bridge_missing_selects_plugin(monkeypatch):
    monkeypatch.setattr(fontlab_mcp, "find_bridge", lambda: None)
    assert asyncio.run(fontlab_mcp.discover_server()) is None


def test_discover_server_when_disabled_never_probes(monkeypatch):
    monkeypatch.setenv("AIDUS_FONTLAB_MCP", "OFF")
    monkeypatch.setattr(fontlab_mcp, "find_bridge", lambda: pytest.fail("must not search"))
    assert asyncio.run(fontlab_mcp.discover_server()) is None


def test_discover_server_when_probe_raises_selects_plugin(monkeypatch):
    async def broken(command):
        raise ExceptionGroup("sdk", [ConnectionError("refused")])

    monkeypatch.setattr(fontlab_mcp, "find_bridge", lambda: "/bridge")
    monkeypatch.setattr(fontlab_mcp, "probe_tools", broken)
    assert asyncio.run(fontlab_mcp.discover_server()) is None


def test_discover_server_when_catalogue_empty_selects_plugin(monkeypatch):
    async def empty(command):
        return []

    monkeypatch.setattr(fontlab_mcp, "find_bridge", lambda: "/bridge")
    monkeypatch.setattr(fontlab_mcp, "probe_tools", empty)
    assert asyncio.run(fontlab_mcp.discover_server()) is None


def test_find_bridge_when_explicit_env_path_has_spaces_returns_it(monkeypatch, tmp_path):
    bridge = tmp_path / "Font Lab" / "fontlab-mcp"
    bridge.parent.mkdir()
    bridge.write_text("#!/bin/sh\n")
    bridge.chmod(0o755)
    monkeypatch.setenv("AIDUS_FONTLAB_MCP_COMMAND", str(bridge))
    assert fontlab_mcp.find_bridge() == str(bridge)


def test_find_bridge_when_explicit_env_path_missing_returns_none(monkeypatch, tmp_path):
    monkeypatch.setenv("AIDUS_FONTLAB_MCP_COMMAND", str(tmp_path / "absent"))
    assert fontlab_mcp.find_bridge() is None


def test_bridge_parameters_when_built_relay_native_command(tmp_path):
    params = fontlab_mcp.bridge_parameters("/Applications/FontLab 9.app/Contents/MacOS/fontlab-mcp")
    assert "/Applications/FontLab 9.app/Contents/MacOS/fontlab-mcp" in params.args


def test_python_version_check_when_old_python_raises(monkeypatch):
    version = namedtuple("version_info", "major minor micro")(3, 11, 6)
    monkeypatch.setattr(py_version_check, "sys", SimpleNamespace(version_info=version))
    with pytest.raises(RuntimeError, match=r"3\.13 or higher\. Current version: 3\.11\.6"):
        py_version_check.check_python_version()


def test_python_version_check_when_current_passes():
    py_version_check.check_python_version()


@pytest.mark.parametrize(
    "error,category",
    [(errors.FontLabConnectionError(), errors.ErrorCategory.FONTLAB_CONNECTION),
     (errors.ConfigurationError("bad"), errors.ErrorCategory.CONFIGURATION),
     (errors.ToolExecutionError("x", "run"), errors.ErrorCategory.TOOL_EXECUTION)],
)
def test_error_types_when_built_carry_category(error, category):
    assert error.category == category
