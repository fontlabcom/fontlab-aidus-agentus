# this_file: tests/test_active_glyph_read.py
"""Branches of the non-exporting active-glyph read (companion of test_info_read_preservation)."""
from types import SimpleNamespace

import pytest

from fontlab_aidus_agentus.plugin import executor


class Native:
    def __init__(self, package):
        self.name, self.id, self.fgGlyphId, self.isNull, self.advanceWidth = "A", 101, 201, False, 600
        self.layers = [SimpleNamespace(transform="t")]
        self.activeLayer = self.layers[0]
        self.package = package

    def getLSB(self, t):
        return 20

    def getRSB(self, t):
        return 30


def _install(monkeypatch, workspace, current_glyph):
    record = SimpleNamespace(name="A", id=201, unicode=65)
    font = type("Font", (dict,), {"id": 301})(A=record)
    package = SimpleNamespace(id=401, fgId=301, fgPackage=font, isNull=False)
    workspace.setdefault("findPackageId", lambda i: package if i == 301 else None)
    monkeypatch.setattr(executor, "FL_AVAILABLE", True)
    monkeypatch.setattr(executor, "fl", SimpleNamespace(
        CurrentFont=lambda: font, CurrentGlyph=current_glyph,
        flWorkspace=SimpleNamespace(instance=lambda: SimpleNamespace(**workspace)),
    ))
    return package


def test_info_when_workspace_glyph_belongs_to_other_font_then_error(monkeypatch):
    other = SimpleNamespace(id=999)
    _install(monkeypatch, {"currentPackage": SimpleNamespace(id=401),
                           "currentGlyph": SimpleNamespace(glyph=Native(other))}, lambda: None)
    result = executor.FontLabExecutor().run("get_current_glyph_info")
    assert "does not belong" in result["error"], result


def test_info_when_workspace_has_no_glyph_then_falls_back_to_current_glyph(monkeypatch):
    holder = {}
    package = _install(monkeypatch, {"currentPackage": SimpleNamespace(id=401), "currentGlyph": None},
                       lambda: holder["glyph"])
    holder["glyph"] = Native(package)
    result = executor.FontLabExecutor().run("get_current_glyph_info")
    assert result["unicode"] == 65, result


def test_info_when_workspace_lacks_current_glyph_attribute_then_falls_back(monkeypatch):
    holder = {}
    package = _install(monkeypatch, {}, lambda: holder["glyph"])
    holder["glyph"] = Native(package)
    result = executor.FontLabExecutor().run("get_current_glyph_info")
    assert result["unicode"] == 65, result


def test_guard_when_neither_workspace_nor_current_glyph_has_glyph_then_error(monkeypatch):
    _install(monkeypatch, {"currentGlyph": None}, lambda: None)
    result = executor.FontLabExecutor().run("get_current_glyph_info")
    assert result == {"error": "No glyph is currently selected"}


def test_info_when_workspace_glyph_is_null_then_uses_current_glyph(monkeypatch):
    holder = {}
    package = _install(monkeypatch, {"currentPackage": SimpleNamespace(id=401),
                                     "currentGlyph": SimpleNamespace(glyph=SimpleNamespace(isNull=True))},
                       lambda: holder["glyph"])
    holder["glyph"] = Native(package)
    assert executor.FontLabExecutor().run("get_current_glyph_info")["unicode"] == 65


def test_info_when_workspace_package_is_null_then_error(monkeypatch):
    package = SimpleNamespace(id=401, isNull=True)
    glyph = Native(SimpleNamespace(id=401))
    _install(monkeypatch, {"currentPackage": package, "currentGlyph": SimpleNamespace(glyph=glyph)},
             lambda: None)
    result = executor.FontLabExecutor().run("get_current_glyph_info")
    assert "does not belong" in result["error"], result


# --- set_glyph_metrics must write the glyph the read path shows (M2) ---------

def _write_env(monkeypatch, shown_name, current):
    """Workspace shows glyph `shown_name`; CurrentGlyph() returns `current`."""
    package = SimpleNamespace(id=401, fgId=301, isNull=False)
    shown = SimpleNamespace(name=shown_name, isNull=False, package=package)
    font = SimpleNamespace(id=301)
    workspace = SimpleNamespace(currentGlyph=SimpleNamespace(glyph=shown), currentPackage=package)
    monkeypatch.setattr(executor, "FL_AVAILABLE", True)
    monkeypatch.setattr(executor, "fl", SimpleNamespace(
        CurrentFont=lambda: font, CurrentGlyph=lambda: current,
        flWorkspace=SimpleNamespace(instance=lambda: workspace)))


def _plain_glyph(name):
    return SimpleNamespace(name=name, width=500, lsb=10, rsb=20, unicode=65)


def test_set_metrics_when_same_glyph_then_writes(monkeypatch):
    glyph = _plain_glyph("A")
    _write_env(monkeypatch, "A", glyph)
    result = executor.FontLabExecutor().run("set_glyph_metrics", {"width": 640})
    assert result.get("success") is True, result
    assert glyph.width == 640, "same glyph must be written"


def test_set_metrics_when_workspace_shows_other_glyph_then_refuses_and_writes_nothing(monkeypatch):
    glyph = _plain_glyph("B")
    _write_env(monkeypatch, "A", glyph)
    result = executor.FontLabExecutor().run("set_glyph_metrics", {"width": 640})
    assert "differs" in result["error"], result
    assert glyph.width == 500, "a refused write must not touch the glyph"


def test_set_metrics_when_workspace_glyph_in_other_font_then_refuses(monkeypatch):
    glyph = _plain_glyph("A")
    _write_env(monkeypatch, "A", glyph)
    executor.fl.flWorkspace.instance().currentPackage.fgId = 999
    result = executor.FontLabExecutor().run("set_glyph_metrics", {"width": 640})
    assert "differs" in result["error"], result
    assert glyph.width == 500


def test_set_metrics_when_current_glyph_none_then_not_selected_message(monkeypatch):
    # workspace shows a glyph (guard passes) but CurrentGlyph() has none
    _write_env(monkeypatch, "A", None)
    result = executor.FontLabExecutor().run("set_glyph_metrics", {"width": 640})
    assert result == {"error": "No glyph is currently selected"}, result
