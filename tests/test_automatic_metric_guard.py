# this_file: tests/test_automatic_metric_guard.py
"""Automatic-layer assignments must not reach setters or history notification.

CurrentGlyph is an inert fixture here; its separate read-preservation gap remains.
"""

from copy import deepcopy
from types import SimpleNamespace

import pytest

from fontlab_aidus_agentus.plugin import executor
from fontlab_aidus_agentus.plugin.client import AidusAgentusClient


class Glyph:
    name = "A"

    def __init__(self, automatic=True, fallback=False):
        self.payload = {
            "width": 500,
            "lsb": 40,
            "rsb": 60,
            "unrelated": {"note": "keep", "anchors": [(10, 20)]},
        }
        self.writes = []
        self.layers = [SimpleNamespace(autoLayer=automatic, transform="identity")]
        self.activeLayer = None if fallback else self.layers[0]

    @property
    def advanceWidth(self):
        return self.payload["width"]

    @advanceWidth.setter
    def advanceWidth(self, value):
        self.writes.append(("width", value))
        self.payload["width"] = value

    def getLSB(self, transform):
        return self.payload["lsb"]

    def getRSB(self, transform):
        return self.payload["rsb"]

    def setLSB(self, value, flag, transform):
        self.writes.append(("lsb", value))
        self.payload["lsb"] = value
        return True

    def setRSB(self, value, transform):
        self.writes.append(("rsb", value))
        self.payload["rsb"] = value
        return True


def install(monkeypatch, glyph):
    notifications, reads = [], []

    def current():
        reads.append(True)
        return glyph

    monkeypatch.setattr(executor, "FL_AVAILABLE", True)
    monkeypatch.setattr(
        executor,
        "fl",
        SimpleNamespace(
            CurrentFont=lambda: object(),
            CurrentGlyph=current,
            flItems=lambda: SimpleNamespace(
                notifyChangesApplied=lambda *args: notifications.append(args)
            ),
        ),
    )
    return executor.FontLabExecutor(), notifications, reads


@pytest.mark.parametrize(
    "arguments",
    [
        {"width": 520},
        {"lsb": 0},
        {"rsb": 0},
        {"width": 520, "lsb": 1, "rsb": 2},
        {"width": 500},
        {"lsb": 40, "rsb": 60},
        {"lsb": 40.0000001},
    ],
)
@pytest.mark.parametrize("fallback", [False, True])
def test_automatic_assignment_when_requested_then_refuse_before_mutation(
    monkeypatch, arguments, fallback
):
    glyph = Glyph(fallback=fallback)
    ex, notifications, _ = install(monkeypatch, glyph)
    before = deepcopy(glyph.payload)
    result = ex.run("set_glyph_metrics", arguments)
    assert "automatic layer" in result.get("error", "").lower()
    assert not glyph.writes and not notifications, (
        "No setter or history call is allowed"
    )
    assert glyph.payload == before, "Refusal preserves the entire fixture payload"


def test_automatic_assignment_when_empty_then_no_setters_or_history(monkeypatch):
    glyph = Glyph()
    ex, notifications, _ = install(monkeypatch, glyph)
    before = deepcopy(glyph.payload)
    result = ex.run("set_glyph_metrics", {})
    assert result["success"] and result["changes"] == []
    assert not glyph.writes and not notifications and glyph.payload == before


@pytest.mark.parametrize("state", ["missing", "raises"])
def test_automatic_flag_when_unknown_then_refuse_before_mutation(monkeypatch, state):
    glyph = Glyph()

    class BrokenLayer:
        transform = "identity"

        @property
        def autoLayer(self):
            raise RuntimeError("automatic state unavailable")

    glyph.activeLayer = (
        SimpleNamespace(transform="identity") if state == "missing" else BrokenLayer()
    )
    ex, notifications, _ = install(monkeypatch, glyph)
    before = deepcopy(glyph.payload)
    assert "error" in ex.run("set_glyph_metrics", {"width": 520})
    assert not glyph.writes and not notifications and glyph.payload == before


def test_native_manual_assignment_when_requested_then_keep_existing_history(
    monkeypatch,
):
    glyph = Glyph(automatic=False)
    ex, notifications, _ = install(monkeypatch, glyph)
    result = ex.run("set_glyph_metrics", {"width": 520, "lsb": 0, "rsb": 0})
    assert result["success"] and glyph.writes == [
        ("width", 520),
        ("lsb", 0),
        ("rsb", 0),
    ]
    assert len(notifications) == 2
    assert all(objects == [glyph.activeLayer, glyph] for _, objects in notifications)


def test_acp_automatic_assignment_when_refused_then_one_response_without_replay(
    monkeypatch,
):
    glyph = Glyph()
    ex, notifications, reads = install(monkeypatch, glyph)
    client = AidusAgentusClient(executor=ex)
    sent = []
    client._transport = SimpleNamespace(send=sent.append)
    client._session_id = "owned"
    client._handle_server_request(
        {
            "id": 123,
            "method": "_fontlab/tool",
            "params": {
                "sessionId": "owned",
                "name": "set_glyph_metrics",
                "arguments": {"width": 520},
            },
        }
    )
    assert len(sent) == 1 and sent[0]["id"] == 123
    assert "automatic layer" in sent[0]["result"].get("error", "").lower()
    assert len(reads) == 2, (
        "Existing preflight and resolution occur once, without replay"
    )
    assert not glyph.writes and not notifications
