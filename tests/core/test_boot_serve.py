# this_file: tests/core/test_boot_serve.py
"""Boot logging, exit codes and backend selection, with the SDK and bridge faked at their seams."""

from __future__ import annotations

import io
import json
import sys
from types import SimpleNamespace

import pytest
import structlog

from fontlab_aidus_agentus.core import boot


@pytest.fixture(autouse=True)
def _reset_structlog():
    yield
    structlog.reset_defaults()


@pytest.mark.parametrize("tty", [True, False])
def test_configure_logging_when_stderr_tty_then_console_else_json(monkeypatch, capsys, tty):
    monkeypatch.setattr(sys.stderr, "isatty", lambda: tty, raising=False)
    boot.configure_logging()
    structlog.get_logger().info("probe_event", key="value")
    line = capsys.readouterr().err.strip().splitlines()[-1]
    if tty:
        assert "probe_event" in line and not line.startswith("{")
    else:
        record = json.loads(line)
        assert record["event"] == "probe_event" and record["key"] == "value" and record["level"] == "info"


def test_get_config_path_when_env_set_then_override(monkeypatch):
    monkeypatch.setenv("AIDUS_AGENTS_CONFIG", "/tmp/custom-agents.yml")
    assert boot.get_config_path() == "/tmp/custom-agents.yml"


def test_main_when_serve_completes_then_zero(monkeypatch):
    called = []

    async def fake_serve():
        called.append(True)

    monkeypatch.setattr(boot, "serve", fake_serve)
    assert boot.main() == 0 and called


@pytest.mark.parametrize(("error", "needle"), [
    (ImportError("no agentpool"), "import_failed"),
    (RuntimeError("boom"), "startup_failed"),
])
def test_main_when_serve_fails_then_one_and_logged(monkeypatch, capsys, error, needle):
    async def failing():
        raise error

    monkeypatch.setattr(boot, "serve", failing)
    assert boot.main() == 1
    assert needle in capsys.readouterr().err


@pytest.mark.asyncio
@pytest.mark.parametrize("bridge", [None, "bridge-server"])
async def test_serve_when_backend_discovered_then_pool_runs_stdio_server(monkeypatch, tmp_path, capsys, bridge):
    import agentpool
    import agentpool.models.manifest as manifest_module

    from fontlab_aidus_agentus.core import acp_server, fontlab_mcp

    config = tmp_path / "agents.yml"
    config.write_text("agents: {}\n")
    monkeypatch.setenv("AIDUS_AGENTS_CONFIG", str(config))
    seen = {}

    async def discover():
        return bridge

    def build(path, server):
        seen["build"] = (path, server)
        return {"built": True}

    class FakeManifest:
        @staticmethod
        def model_validate(data):
            seen["manifest"] = data
            return "MANIFEST"

    class FakePool:
        main_agent = "MAIN-AGENT"

        def __init__(self, manifest, main_agent_name):
            seen["pool"] = (manifest, main_agent_name)

        async def __aenter__(self):
            return self

        async def __aexit__(self, *exc):
            seen["closed"] = True

    async def fake_serve_stdio(agent, output):
        seen["stdio"] = (agent, output)
        print("third-party print must not reach the protocol pipe")

    monkeypatch.setattr(fontlab_mcp, "discover_server", discover)
    monkeypatch.setattr(fontlab_mcp, "build_manifest", build)
    monkeypatch.setattr(manifest_module, "AgentsManifest", FakeManifest)
    monkeypatch.setattr(agentpool, "AgentPool", FakePool)
    monkeypatch.setattr(acp_server, "serve_stdio", fake_serve_stdio)
    monkeypatch.setattr(sys.stderr, "isatty", lambda: False, raising=False)
    protocol = io.BytesIO()
    monkeypatch.setattr(sys, "stdout", SimpleNamespace(buffer=protocol, write=sys.stderr.write, flush=lambda: None))

    await boot.serve()

    assert seen["build"] == (boot.Path(str(config)), bridge)
    assert seen["manifest"] == {"built": True}
    assert seen["pool"] == ("MANIFEST", "fontlab_copilot")
    assert seen["stdio"] == ("MAIN-AGENT", protocol) and seen["closed"]
    assert protocol.getvalue() == b""
    assert f"backend={'mcp' if bridge else 'plugin'}" in capsys.readouterr().err
