# this_file: tests/test_ui_dock.py
"""The real AidusAgentusDock against a recording PythonQt fake (value and callable getters)."""

import json
import os
from types import SimpleNamespace

import pytest


@pytest.fixture(params=[False, True], ids=["pythonqt-values", "callable-getters"])
def ui(request, fake_qt, isolated_home):
    module = fake_qt("fontlab_aidus_agentus.plugin.ui", callable_getters=request.param)
    assert module.AidusAgentusDock.HISTORY_FILE.startswith(str(isolated_home)), "History must live in the isolated HOME"
    return module


@pytest.fixture
def dock(ui, fake_client):
    return ui.AidusAgentusDock(client=fake_client())


def history(ui):
    with open(ui.AidusAgentusDock.HISTORY_FILE, encoding="utf-8") as stream:
        return json.load(stream)


def test_dock_when_built_wires_buttons_input_and_client(dock, ui):
    assert ("setObjectName", ("AidusAgentusDock",)) in dock.calls
    assert dock._reconnect_btn.clicked.slots == [dock._on_reconnect]
    assert dock._clear_btn.clicked.slots == [dock.clear_chat]
    assert dock._input_field.returnPressed.slots == [dock._on_submit]
    assert dock._client.chatUpdate.slots == [dock._on_chat_update]
    assert dock._client.stateChanged.slots == [dock._on_state_changed]
    assert dock._status_label.text_value == "● Disconnected"
    assert dock._thinking_label.visible is False
    assert dock.get_client() is dock._client


def test_dock_when_built_without_client_connects_later(ui, fake_client):
    dock = ui.AidusAgentusDock()
    assert dock.get_client() is None
    client = fake_client()
    dock.set_client(client)
    assert client.chatUpdate.slots == [dock._on_chat_update]


def test_submit_when_text_present_sends_stripped_prompt_and_clears(dock):
    dock._input_field.value = "  How wide is A?  "
    dock._on_submit()
    assert dock._client.prompts == ["How wide is A?"]
    assert dock._input_field.value == ""


@pytest.mark.parametrize("text", ["", "   ", "\n\t"])
def test_submit_when_blank_does_nothing(dock, text):
    dock._input_field.value = text
    dock._on_submit()
    assert dock._client.prompts == [] and dock._chat_display.html == []


def test_submit_when_no_client_shows_error_row(ui):
    dock = ui.AidusAgentusDock()
    dock._input_field.value = "hello"
    dock._on_submit()
    assert "No client connected" in dock._chat_display.html[-1]


def test_append_text_when_saved_writes_escaped_html_and_history(dock, ui):
    dock.append_text("user", "<b>Ä & 字</b>")
    html = dock._chat_display.html[-1]
    assert "&lt;b&gt;Ä &amp; 字&lt;/b&gt;" in html and "<b>" not in html
    assert ui.ROLE_COLORS["user"] in html and "USER" in html
    assert history(ui) == [{"role": "user", "content": "<b>Ä & 字</b>", "timestamp": history(ui)[0]["timestamp"]}]
    assert ("setValue", (500,)) in dock._chat_display.scrollbar.calls


def test_append_text_when_not_saved_skips_history(dock, ui):
    dock.append_text("system", "transient", save=False)
    assert not os.path.exists(ui.AidusAgentusDock.HISTORY_FILE)


def test_append_text_when_unknown_role_uses_default_color(dock, ui):
    dock.append_text("mystery", "x", save=False)
    assert ui.AidusAgentusDock.DEFAULT_COLOR_LIGHT in dock._chat_display.html[-1] or (
        ui.AidusAgentusDock.DEFAULT_COLOR_DARK in dock._chat_display.html[-1]
    )


@pytest.mark.parametrize("callable_getters", [False, True])
@pytest.mark.parametrize("lightness,dark", [(30, True), (247, False), (127, True), (128, False)])
def test_detect_is_dark_when_palette_lightness_varies(fake_qt, callable_getters, lightness, dark):
    module = fake_qt("fontlab_aidus_agentus.plugin.ui", callable_getters=callable_getters, lightness=lightness)
    dock = module.AidusAgentusDock()
    assert dock._detect_is_dark() is dark
    dock.append_text("system", "x", save=False)
    assert ("#EEEEEE" if dark else "#000000") in dock._chat_display.html[-1]


def test_detect_is_dark_when_palette_fails_falls_back_to_dark(dock):
    dock.palette = SimpleNamespace(color=lambda role: 1 / 0)
    assert dock._detect_is_dark() is True


def test_format_message_when_code_blocks_renders_pre_and_breaks(dock):
    text = "Run this:\n```python\nprint('<x>')\n```\nthen\n```\nsecond\n```"
    html = dock._format_message(text)
    assert html.count("<pre") == 2
    assert "print('&lt;x&gt;')" in html and "Run this:<br>" in html


def test_format_message_when_unterminated_fence_keeps_text(dock):
    html = dock._format_message("```python\nunfinished")
    assert "<pre" not in html and "unfinished" in html


def test_format_message_when_huge_input_is_linear(dock):
    text = "line\n" * 20000
    assert dock._format_message(text).count("<br>") == 20000


@pytest.mark.parametrize(
    "message,hint",
    [
        ("TRANSPORT down", "core process is running"),
        ("SEND_FAILED", "try reconnecting"),
        ("code -32600", "Invalid request"),
        ("code -32601", "Method not found"),
        ("code -32602", "Invalid parameters"),
        ("code -32603", "Internal server error"),
        ("Process error: FailedToStart", "check Python path"),
        ("Process error: Crashed", "check logs"),
        ("Process error: Timedout", "may need restart"),
    ],
)
def test_show_error_when_known_code_adds_hint(dock, message, hint):
    dock.show_error(message)
    assert hint in dock._chat_display.html[-1]


def test_show_error_when_unknown_message_is_unchanged(dock):
    assert dock._format_error_message("plain failure") == "plain failure"


def test_load_history_when_valid_restores_rows_without_rewriting(dock, ui):
    rows = [{"role": "user", "content": "hi", "timestamp": "1"}, {"role": "assistant", "content": "yo"},
            {"bad": 1}, "junk"]
    os.makedirs(os.path.dirname(ui.AidusAgentusDock.HISTORY_FILE))
    with open(ui.AidusAgentusDock.HISTORY_FILE, "w", encoding="utf-8") as stream:
        json.dump(rows, stream)
    before = os.path.getmtime(ui.AidusAgentusDock.HISTORY_FILE)
    dock._load_history()
    assert len(dock._chat_display.html) == 2 and dock._history_data == rows[:2]
    assert os.path.getmtime(ui.AidusAgentusDock.HISTORY_FILE) == before


def test_load_history_when_missing_is_noop(dock):
    dock._load_history()
    assert dock._chat_display.html == []


@pytest.mark.parametrize("payload", [b"{not json", b"\xff\xfe\x00", b'{"role": "user"}'])
def test_load_history_when_corrupt_reports_or_ignores(dock, ui, payload):
    os.makedirs(os.path.dirname(ui.AidusAgentusDock.HISTORY_FILE))
    with open(ui.AidusAgentusDock.HISTORY_FILE, "wb") as stream:
        stream.write(payload)
    dock._load_history()
    assert dock._history_data == []
    if payload.startswith(b'{"'):
        assert dock._chat_display.html == [], "A non-list document is ignored"
    else:
        assert "Failed to load history" in dock._chat_display.html[-1]


def test_save_history_when_folder_unwritable_reports_without_raising(dock, ui, monkeypatch, capsys):
    monkeypatch.setattr(ui.AidusAgentusDock, "HISTORY_FILE", "/dev/null/history.json")
    dock.append_text("user", "x")
    assert "Failed to save history" in capsys.readouterr().out


def test_clear_chat_when_history_exists_removes_file(dock, ui):
    dock.append_text("user", "x")
    dock.clear_chat(True)
    assert dock._chat_display.html == [] and dock._history_data == []
    assert not os.path.exists(ui.AidusAgentusDock.HISTORY_FILE)


def test_clear_chat_when_remove_fails_is_silent(dock, ui, monkeypatch):
    dock.append_text("user", "x")
    monkeypatch.setattr(ui.os, "remove", lambda path: (_ for _ in ()).throw(PermissionError(path)))
    dock.clear_chat()
    assert dock._history_data == []


@pytest.mark.parametrize(
    "state,label,reconnect_enabled",
    [("ready", "● Connected", False), ("connected", "● Connected", False),
     ("connecting", "● Connecting...", False), ("error", "● Disconnected", True),
     ("disconnected", "● Disconnected", True)],
)
def test_state_change_when_received_updates_status(dock, state, label, reconnect_enabled):
    dock._on_state_changed(state)
    assert dock._status_label.text_value == label
    assert dock._reconnect_btn.called("setEnabled")[-1] == (reconnect_enabled,)


def test_state_change_when_waiting_shows_thinking_and_disables_input(dock):
    dock._on_state_changed("waiting")
    assert dock._thinking_label.visible is True
    assert dock._input_field.called("setEnabled")[-1] == (False,)
    dock._on_state_changed("ready")
    assert dock._thinking_label.visible is False
    assert dock._input_field.called("setEnabled")[-1] == (True,)


def test_escape_when_thinking_cancels_display_only(dock, ui):
    dock.show_thinking()
    dock.keyPressEvent(SimpleNamespace(key=lambda: ui.Qt.Key_Escape))
    assert dock._thinking_label.visible is False
    assert "Generation cancelled" in dock._chat_display.html[-1]


def test_escape_when_idle_or_other_key_does_nothing(dock, ui):
    dock._thinking_label.visible = False
    dock.keyPressEvent(SimpleNamespace(key=lambda: ui.Qt.Key_Escape))
    dock.keyPressEvent(SimpleNamespace(key=lambda: ui.Qt.Key_Return))
    assert dock._chat_display.html == []


def test_reconnect_when_transport_present_asks_client(dock):
    dock._on_reconnect(False)
    assert dock._client.reconnects == 1
    assert "Reconnecting" in dock._chat_display.html[-1]


def test_reconnect_when_no_transport_shows_error(ui, fake_client):
    dock = ui.AidusAgentusDock(client=fake_client(transport=False))
    dock._on_reconnect()
    assert "No client transport available" in dock._chat_display.html[-1]


def test_chat_update_signal_when_emitted_appends_row(dock):
    dock._client.chatUpdate.emit("assistant", "Done.")
    assert "Done." in dock._chat_display.html[-1]


def _write_history(ui, rows):
    os.makedirs(os.path.dirname(ui.AidusAgentusDock.HISTORY_FILE), exist_ok=True)
    with open(ui.AidusAgentusDock.HISTORY_FILE, "w", encoding="utf-8") as stream:
        json.dump(rows, stream)


def test_dock_when_created_reloads_saved_history_and_keeps_appending(ui, fake_client):
    _write_history(ui, [{"role": "user", "content": "earlier ✓", "timestamp": "1"}])
    dock = ui.AidusAgentusDock(client=fake_client())
    assert len(dock._chat_display.html) == 1 and "earlier ✓" in dock._chat_display.html[0]
    dock.append_text("assistant", "later")
    assert [row["content"] for row in history(ui)] == ["earlier ✓", "later"]


def test_history_when_long_is_bounded_on_load_and_save(ui, fake_client):
    limit = ui.AidusAgentusDock.MAX_HISTORY
    _write_history(ui, [{"role": "user", "content": str(i)} for i in range(limit + 50)])
    dock = ui.AidusAgentusDock(client=fake_client())
    assert len(dock._chat_display.html) == limit and dock._history_data[0]["content"] == "50"
    dock.append_text("user", "new")
    saved = history(ui)
    assert len(saved) == limit and saved[-1]["content"] == "new"


def test_history_when_message_huge_is_truncated_when_saved(ui, fake_client):
    dock = ui.AidusAgentusDock(client=fake_client())
    dock.append_text("assistant", "x" * (ui.AidusAgentusDock.MAX_MESSAGE_CHARS * 3))
    saved = history(ui)[-1]["content"]
    assert len(saved) <= ui.AidusAgentusDock.MAX_MESSAGE_CHARS + 40 and saved.endswith("[truncated]")


def test_history_when_total_bytes_exceed_bound_drops_oldest(ui, fake_client):
    dock = ui.AidusAgentusDock(client=fake_client())
    big = "y" * ui.AidusAgentusDock.MAX_MESSAGE_CHARS
    for i in range(ui.AidusAgentusDock.MAX_HISTORY_BYTES // len(big) + 5):
        dock.append_text("user", "%d %s" % (i, big))
    assert os.path.getsize(ui.AidusAgentusDock.HISTORY_FILE) <= ui.AidusAgentusDock.MAX_HISTORY_BYTES
    assert history(ui)[-1]["content"].startswith("%d " % i), "The newest rows are kept"


def test_load_history_when_file_far_too_large_is_ignored(ui, fake_client):
    os.makedirs(os.path.dirname(ui.AidusAgentusDock.HISTORY_FILE), exist_ok=True)
    with open(ui.AidusAgentusDock.HISTORY_FILE, "w", encoding="utf-8") as stream:
        stream.write("[" + ",".join(['{"role":"user","content":"%s"}' % ("z" * 1000)] *
                     (4 * ui.AidusAgentusDock.MAX_HISTORY_BYTES // 1000 + 10)) + "]")
    dock = ui.AidusAgentusDock(client=fake_client())
    assert dock._history_data == [] and "too large" in dock._chat_display.html[-1]


@pytest.mark.parametrize("error", [PermissionError("denied"), FileNotFoundError("vanished")])
def test_load_history_when_size_unreadable_reports_unavailable(ui, fake_client, monkeypatch, error):
    _write_history(ui, [{"role": "user", "content": "x"}])

    def broken(path):
        raise error

    monkeypatch.setattr(ui.os.path, "getsize", broken)
    dock = ui.AidusAgentusDock(client=fake_client())
    assert "History file unavailable" in dock._chat_display.html[-1]
