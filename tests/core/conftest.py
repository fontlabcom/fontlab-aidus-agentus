# this_file: tests/core/conftest.py
# Copyright 2025 Fontlab Ltd. All rights reserved.
"""Pytest configuration and shared fixtures."""

from __future__ import annotations

import os
from typing import TYPE_CHECKING

import pytest

from fontlab_aidus_agentus.core import boot

if TYPE_CHECKING:
    from collections.abc import Iterator


@pytest.fixture(autouse=True)
def mock_env_vars(monkeypatch: pytest.MonkeyPatch) -> Iterator[None]:
    """Set up mock environment variables for testing."""
    monkeypatch.setenv("OPENAI_API_KEY", "sk-test-key-for-testing-only")
    monkeypatch.setenv("AIDUS_LOG_LEVEL", "DEBUG")
    yield


@pytest.fixture
def config_path() -> str:
    """Return path to agents.yml config file."""
    return os.path.join(os.path.dirname(boot.__file__), "agents.yml")
