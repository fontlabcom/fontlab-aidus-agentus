# this_file: tests/test_info_read_preservation.py
"""Fail-first model of both native glyph-export entry points (fl#8525).

These are source regression traps, not evidence from a running FontLab.
"""
from copy import deepcopy
from types import SimpleNamespace

import pytest

from fontlab_aidus_agentus.plugin import executor


class Glyph:
    def __init__(self, payload, destructive_export):
        self.name, self.id, self.fgGlyphId = "A", 101, 201
        self.isNull, self.advanceWidth = False, 600
        self.layers = [SimpleNamespace(transform="identity")]
        self.activeLayer = self.layers[0]
        self.payload, self.destructive_export = payload, destructive_export

    @property
    def fgGlyph(self):
        if self.destructive_export:
            self.payload["lib"].pop("note", None)
        return SimpleNamespace(name="A", id=201, unicode=65)

    def getLSB(self, transform):
        return 20

    def getRSB(self, transform):
        return 30


@pytest.mark.parametrize("entry", ["CurrentGlyph", "fgGlyph"])
def test_info_when_note_is_fresh_preserves_full_payload(monkeypatch, entry):
    payload = {"note": "fresh note", "lib": {"note": "fresh note", "other": [1, 2]}}
    before = deepcopy(payload)
    glyph = Glyph(payload, destructive_export=entry == "fgGlyph")
    record = SimpleNamespace(name="A", id=201, unicode=65)

    class Font(dict):
        id = 301

    font = Font(A=record)
    package = SimpleNamespace(id=401, fgId=301, fgPackage=font, isNull=False)
    glyph.package = package
    workspace = SimpleNamespace(
        currentPackage=package,
        currentGlyph=SimpleNamespace(glyph=glyph),
        findPackageId=lambda identity: package if identity == package.fgId else None,
    )

    def current_glyph():
        # python_gate.cpp get_glyph exports with fgGlyph(true), even in preflight.
        if entry == "CurrentGlyph":
            payload["lib"].pop("note", None)
        return glyph

    monkeypatch.setattr(executor, "FL_AVAILABLE", True)
    monkeypatch.setattr(executor, "fl", SimpleNamespace(
        CurrentFont=lambda: font, CurrentGlyph=current_glyph,
        flWorkspace=SimpleNamespace(instance=lambda: workspace),
    ))
    result = executor.FontLabExecutor().run("get_current_glyph_info")
    assert result["unicode"] == 65, "Keep the existing information feature"
    assert payload == before, "Reading glyph information must preserve fresh note and full lib"
