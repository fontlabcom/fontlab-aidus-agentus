# this_file: conftest.py
"""Keep every test away from the developer's real configuration and chat history.

The plugin reads `~/.config/aidus_agentus/config.json` and writes `history.json`
beside it; Clear deletes that file. An `aidus_config.json` at the repository
root is also a live configuration candidate, because the owner's FontLab imports
this checkout through an editable install.
"""

import os
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent


def pytest_sessionstart(session):
    stray = ROOT / "aidus_config.json"
    if stray.exists():
        pytest.exit(f"{stray} exists: tests (and the live FontLab) would load it. Move it away.", returncode=3)


@pytest.fixture(autouse=True)
def isolated_home(tmp_path_factory, monkeypatch):
    """Point HOME at an empty folder (outside tmp_path) and drop configuration overrides."""
    home = tmp_path_factory.mktemp("home")
    monkeypatch.setenv("HOME", str(home))
    monkeypatch.setenv("USERPROFILE", str(home))
    for name in ("AIDUS_CONFIG", "AIDUS_PYTHON", "AIDUS_FONTLAB_MCP_COMMAND", "FONTLAB_MCP_COMMAND"):
        monkeypatch.delenv(name, raising=False)
    # Provider keys from the developer's shell must never reach a test child process.
    for name in [n for n in os.environ if n.endswith("_API_KEY")]:
        monkeypatch.delenv(name)
    return home
