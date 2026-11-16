# this_file: tests/test_dependency_pins.py
"""Keep the root [brain] extra on its supported exact dependency tuple (DEPENDENCIES.md)."""

import tomllib
from pathlib import Path

from packaging.requirements import Requirement

PINNED = (
    "agentpool", "pydantic-ai-slim", "pydantic-graph", "openai",
    "anthropic", "mistralai", "google-genai",
)


def test_brain_extra_when_packaged_then_each_supported_package_has_one_exact_pin():
    root = Path(__file__).resolve().parents[1]
    brain = tomllib.loads((root / "pyproject.toml").read_text())["project"][
        "optional-dependencies"
    ]["brain"]
    requirements = [Requirement(value) for value in brain]
    for name in PINNED:
        matches = [r for r in requirements if r.name == name]
        assert len(matches) == 1, f"Expected one [brain] entry for {name}: {matches}"
        specifiers = list(matches[0].specifier)
        assert (
            len(specifiers) == 1
            and specifiers[0].operator == "=="
            and "*" not in specifiers[0].version
        ), f"Require one exact version: {matches[0]}"
