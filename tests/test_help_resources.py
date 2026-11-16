# this_file: tests/test_help_resources.py
"""Authored offline help has one canonical source and complete local links."""

import re
import tomllib
from pathlib import Path
from urllib.parse import unquote, urlsplit

ROOT = Path(__file__).resolve().parents[1]
HELP_FILES = (
    "configure.md",
    "development-and-limits.md",
    "dock-and-acp.md",
    "guides/architecture.md",
    "guides/external-agents-mcp.md",
    "guides/fontlab-installations.md",
    "guides/fontlab-mcp.md",
    "guides/manual-tests.md",
    "guides/troubleshooting.md",
    "index.md",
    "installation.md",
)


def test_wheel_help_when_selected_maps_only_canonical_authored_bytes():
    config = tomllib.loads((ROOT / "pyproject.toml").read_text())
    wheel = config["tool"]["hatch"]["build"]["targets"]["wheel"]
    assert wheel.get("force-include") == {
        f"src_docs/md/{name}": f"fontlab_aidus_agentus/_help/{name}"
        for name in HELP_FILES
    }
    for name in HELP_FILES:
        page = ROOT / "src_docs/md" / name
        assert page.read_text(encoding="utf-8").strip()
        for target in re.findall(r"\[[^\]]*\]\(([^)]+)\)", page.read_text()):
            url = urlsplit(target)
            if url.scheme or url.netloc or not url.path:
                continue
            destination = (page.parent / unquote(url.path)).resolve()
            relative = destination.relative_to(ROOT / "src_docs/md").as_posix()
            assert relative in HELP_FILES, (name, target)


def test_sdist_when_selected_keeps_private_repository_history_out_of_packages():
    config = tomllib.loads((ROOT / "pyproject.toml").read_text())
    sdist = config["tool"]["hatch"]["build"]["targets"]["sdist"]
    assert "CHANGELOG.md" not in sdist["only-include"]
    assert config["project"]["readme"] == "README.md"
    assert {"LICENSE", "LICENSE-3RD-PARTY.md"} <= set(sdist["only-include"])
