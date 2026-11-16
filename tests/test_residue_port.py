# this_file: tests/test_residue_port.py
"""Guard the issue-201 port: package-aware prompt, load-check script, archive hashes."""

import json
import runpy
import sys
from pathlib import Path
from types import ModuleType

import pytest

ROOT = Path(__file__).resolve().parents[1]
PROMPT = ROOT / "src/fontlab_aidus_agentus/core/prompts/fontlab_api.md"
CHECK = ROOT / "run_in_fontlab/check_aidus_in_fontlab.vfpy"
PACKAGES = (
    "fontlab-echopy", "fontlab-fly", "fontlab-fontlabapp", "pythonqtside", "fontlab-glyport",
    "fontlab-fontport", "fontlab-python-pens", "fontlab-python-plugmix", "fontlab-python-scriptmix", "fontlab-remopy",
)
SNIPPETS = (
    "from fly import fl, fg, pr", "from fly import fl, fg, tr, pr, qt, ap, qs, gp, fp, pens",
    "from fly.ap.core.application import Application", "from fly.qs import QtCore, QtGui, QtWidgets",
    "from fly.gp import GlyphsApp", "from fly.fp.transfer import",
    "fly.ap.plugins", "fontlabapp.plugmix", "from fly import pens", "flCanvas.appendPythonPainter", "with FontLab() as fl",
    "`polyline`, `text`, `polygon`",
)


@pytest.mark.parametrize("name", PACKAGES)
def test_prompt_when_loaded_then_names_each_target_package(name):
    present = name in PROMPT.read_text()
    assert present, f"prompt must tell the agent about {name}"


@pytest.mark.parametrize("snippet", SNIPPETS)
def test_prompt_when_loaded_then_has_exact_import_snippet(snippet):
    present = snippet in PROMPT.read_text()
    assert present, f"prompt lacks the exact snippet {snippet!r}"


def test_prompt_when_loaded_then_remopy_client_is_external_only():
    text = PROMPT.read_text()
    external_only = "do not use the client API from code running inside FontLab" in text
    enable_allowed = "enable_mcp()" in text and "Never import it" not in text
    assert external_only
    assert enable_allowed


def test_prompt_when_loaded_then_has_no_legacy_aidus_code_path():
    text = PROMPT.read_text()
    clean = "aidus-code/" not in text and "vendor/repos" not in text
    assert clean


def _run_check(monkeypatch, tmp_path, present):
    out = tmp_path / "report.json"
    monkeypatch.setenv("AIDUS_LOAD_CHECK", str(out))
    for name in present:
        module = ModuleType(name)
        module.__version__ = "9.9"
        monkeypatch.setitem(sys.modules, name, module)
    runpy.run_path(str(CHECK))
    return json.loads(out.read_text())


def test_check_script_when_required_modules_import_then_success(monkeypatch, tmp_path):
    required = ["PythonQt", "fontlab", "fontlab_aidus_agentus", "fontlab_aidus_agentus.plugin"]
    plugin = [f"fontlab_aidus_agentus.plugin.{n}" for n in ("config", "executor", "transport", "client", "ui", "main")]
    report = _run_check(monkeypatch, tmp_path, required + plugin)
    assert report["success"] is True, report
    assert report["required"]["fontlab"]["version"] == "9.9"
    assert report["ecosystem"]["fly"]["ok"] is False, "absent optional package is reported, not fatal"


def test_check_script_when_required_module_missing_then_reports_it(monkeypatch, tmp_path):
    for name in ("PythonQt", "fontlab", "fontlab_aidus_agentus", "fontlab_aidus_agentus.plugin"):
        monkeypatch.setitem(sys.modules, name, None)  # None makes import raise ImportError
    report = _run_check(monkeypatch, tmp_path, [])
    assert report["success"] is False
    assert "fontlab" in report["missing_required"]
    assert "ModuleNotFoundError" in report["required"]["fontlab"]["error"]
