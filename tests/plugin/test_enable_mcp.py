# this_file: tests/plugin/test_enable_mcp.py
"""Verify the activation helper changes only MCP and notifies the live listener."""

import sys
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock


def test_helper_when_run_loads_only_mcp_preference_and_notifies(monkeypatch):
    preferences = Mock()
    items = Mock()
    monkeypatch.setitem(
        sys.modules, "fontlab", SimpleNamespace(flItems=items, flPreferences=lambda: preferences)
    )
    path = Path(__file__).parents[2] / "run_in_fontlab/enable_fontlab_mcp.vfpy"
    exec(compile(path.read_text(), str(path), "exec"), {})
    preferences.load.assert_called_once_with({"mcp.enabled": True})
    preferences.save.assert_not_called()
    items.notifyPreferencesChanged.assert_called_once_with()
