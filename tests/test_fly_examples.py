# this_file: tests/test_fly_examples.py
"""Generated-script teaching uses Fly; binding probes keep their raw identities."""

import ast
import re
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
PROMPT = "src/fontlab_aidus_agentus/core/prompts/fontlab_api.md"
GUIDES = (
    "src_docs/md/guides/external-agents-mcp.md",
    "src_docs/md/guides/fontlab-installations.md",
)
PROVIDERS = {
    "fontlab", "fontgate", "fontpr", "PythonQt", "echopy", "fontlabapp",
    "fontlab_fontport", "fontlab_glyport", "fontlab_pens", "pythonqtside",
    "GlyphsApp", "fontlab_plugmix",
}


def _provider_import_count(source):
    try:
        tree = ast.parse(source)
    except SyntaxError:
        pytest.fail("Invalid Python teaching syntax", pytrace=False)
    imports = [
        name.name for node in ast.walk(tree) if isinstance(node, ast.Import)
        for name in node.names
    ] + [
        node.module or "" for node in ast.walk(tree)
        if isinstance(node, ast.ImportFrom)
    ]
    return sum(name.split(".")[0] in PROVIDERS for name in imports)


@pytest.mark.parametrize("relative", (PROMPT, *GUIDES))
def test_python_teaching_when_importing_providers_then_uses_fly(relative):
    text = (ROOT / relative).read_text()
    blocks = re.findall(r"^```python\n(.*?)^```", text, re.MULTILINE | re.DOTALL)
    assert blocks, f"No Python teaching fences in {relative}"
    for index, body in enumerate(blocks, 1):
        if _provider_import_count(body):
            pytest.fail(f"Direct provider import in {relative} Python fence {index}", pytrace=False)


def test_inline_teaching_when_importing_providers_then_uses_fly():
    text = (ROOT / PROMPT).read_text()
    imports = [
        name for code in re.findall(r"`([^`\n]+)`", text)
        for name in re.findall(r"(?:^|;)\s*(?:from|import)\s+([\w.]+)", code)
    ]
    if any(name.split(".")[0] in PROVIDERS for name in imports):
        pytest.fail("Direct provider import in inline prompt teaching", pytrace=False)


@pytest.mark.parametrize("path", sorted((ROOT / "Scripts").rglob("*.py")) + [
    ROOT / "run_in_fontlab/check_aidus_in_fontlab.vfpy",
    ROOT / "run_in_fontlab/enable_fontlab_mcp.vfpy",
])
def test_user_script_when_importing_providers_then_uses_fly(path):
    # Raw provider-name probing and Remopy transport are intentional diagnostics.
    assert not _provider_import_count(path.read_text()), path.relative_to(ROOT)


@pytest.mark.parametrize("relative", (PROMPT, "src/fontlab_aidus_agentus/core/agents.yml"))
def test_generation_policy_when_loading_either_prompt_then_requires_fly(relative):
    text = (ROOT / relative).read_text()
    if "Use Fly for generated FontLab scripts" not in text:
        pytest.fail(f"Fly generation policy missing in {relative}", pytrace=False)


def test_raw_binding_probe_when_inspecting_legacy_fl_then_keeps_distinct_imports():
    path = ROOT / "run_in_fontlab/introspect_pythonqt.vfpy"
    imports = {
        name.name for node in ast.walk(ast.parse(path.read_text()))
        if isinstance(node, ast.Import) for name in node.names
    }
    assert {"PythonQt", "fl", "fontlab"} <= imports
