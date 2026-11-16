# this_file: tests/core/test_config.py
# Copyright 2025 Fontlab Ltd. All rights reserved.
"""Tests for config module."""

from __future__ import annotations

import pytest
from pydantic import ValidationError


def test_settings_loads_from_env(monkeypatch: pytest.MonkeyPatch) -> None:
    """Test that settings loads correctly from environment."""
    monkeypatch.setenv("OPENAI_API_KEY", "sk-test-valid-key")
    monkeypatch.setenv("LOG_LEVEL", "DEBUG")

    from fontlab_aidus_agentus.core.config import get_settings

    settings = get_settings()
    assert settings.openai_api_key == "sk-test-valid-key"
    assert settings.log_level == "DEBUG"
    assert settings.core_host == "127.0.0.1"
    assert settings.core_port == 8765


def test_settings_validates_openai_key_prefix(monkeypatch: pytest.MonkeyPatch) -> None:
    """Test that OpenAI API key must start with 'sk-'."""
    monkeypatch.setenv("OPENAI_API_KEY", "invalid-key-no-prefix")

    from fontlab_aidus_agentus.core.config import Settings

    with pytest.raises(ValidationError) as exc_info:
        Settings()

    assert "sk-" in str(exc_info.value)


def test_settings_optional_anthropic_key(monkeypatch: pytest.MonkeyPatch) -> None:
    """Test that Anthropic key is optional."""
    monkeypatch.setenv("OPENAI_API_KEY", "sk-test-key")
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)

    from fontlab_aidus_agentus.core.config import get_settings

    settings = get_settings()
    assert settings.anthropic_api_key is None
