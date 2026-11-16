# this_file: tests/core/test_boot.py
# Copyright 2025 Fontlab Ltd. All rights reserved.
"""Tests for boot module."""

from __future__ import annotations

import os


def test_get_config_path() -> None:
    """Test that config path points to existing agents.yml."""
    from fontlab_aidus_agentus.core.boot import get_config_path

    config_path = get_config_path()
    assert config_path.endswith("agents.yml")
    assert os.path.exists(config_path), f"Config file not found: {config_path}"


def test_config_file_is_valid_yaml() -> None:
    """Test that agents.yml is valid YAML."""
    import yaml

    from fontlab_aidus_agentus.core.boot import get_config_path

    config_path = get_config_path()
    with open(config_path) as f:
        config = yaml.safe_load(f)

    assert "agents" in config
    assert "fontlab_copilot" in config["agents"]
