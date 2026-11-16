# this_file: tests/test_registered_unicode.py
"""Read the registered FontGate record without exporting an flGlyph."""
from types import SimpleNamespace

import pytest

from fontlab_aidus_agentus.plugin import executor


class Font(dict):
    id = 301

    def keys(self):
        return list(super().keys())


@pytest.fixture
def owned(monkeypatch):
    record = SimpleNamespace(name="A", id=201, unicode=0x1F600)
    font = Font(A=record)
    registered = SimpleNamespace(id=401, fgId=301, fgPackage=font, isNull=False)

    class Owner:
        id, fgId, isNull = 401, 301, False

        @property
        def fgPackage(self):
            raise AssertionError("Only the registered package may be exported")

    class Glyph:
        name, fgGlyphId = "A", 201
        package = Owner()

        @property
        def fgGlyph(self):
            raise AssertionError("Reading Unicode must not export glyph data")

    glyph = Glyph()
    # Native findPackageId is keyed by the FontGate id (fgId), not flPackage.id.
    workspace = SimpleNamespace(findPackageId=lambda identity: registered if identity == 301 else None)
    monkeypatch.setattr(executor, "fl", SimpleNamespace(
        flWorkspace=SimpleNamespace(instance=lambda: workspace)))
    return glyph, registered, font, workspace


@pytest.mark.parametrize("value", [0, 65, 0x1F600, None])
def test_unicode_when_registered_then_preserves_value(owned, value):
    glyph, registered, font, workspace = owned
    font["A"].unicode = value
    assert executor.FontLabExecutor()._native_unicode(glyph) == value


@pytest.mark.parametrize("case", [
    "no-owner", "null-owner", "missing-owner", "null-registered",
    "package-id", "fontgate-id", "missing-font", "font-id",
    "missing-name", "duplicate-name", "missing-record", "record-name", "record-id",
])
def test_unicode_when_ownership_ambiguous_then_refuses(owned, case):
    glyph, registered, font, workspace = owned
    if case == "no-owner":
        glyph.package = None
    elif case == "null-owner":
        glyph.package.isNull = True
    elif case == "missing-owner":
        workspace.findPackageId = lambda identity: None
    elif case == "null-registered":
        registered.isNull = True
    elif case == "package-id":
        registered.id = 999
    elif case == "fontgate-id":
        registered.fgId = 999
    elif case == "missing-font":
        registered.fgPackage = None
    elif case == "font-id":
        font.id = 999
    elif case == "missing-name":
        font.clear()
    elif case == "duplicate-name":
        font.keys = lambda: ["A", "A"]
    elif case == "missing-record":
        font["A"] = None
    elif case == "record-name":
        font["A"].name = "B"
    else:
        font["A"].id = 999
    with pytest.raises(executor.ToolError, match="registered|Registered"):
        executor.FontLabExecutor()._native_unicode(glyph)
