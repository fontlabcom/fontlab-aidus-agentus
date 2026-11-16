# this_file: tests/test_brain_log.py
"""Bounded brain stderr: important lines reach FontLab's Output, a tail reaches the dock."""

import json

import pytest

from fontlab_aidus_agentus.plugin.brain_log import BrainLog


def record(level, event):
    return json.dumps({"level": level, "event": event}, ensure_ascii=False) + "\n"


@pytest.fixture
def printed():
    return []


@pytest.fixture
def log(printed):
    return BrainLog(keep_lines=5, print_limit=3, line_chars=80, printer=printed.append)


def test_feed_when_info_json_keeps_it_quiet_but_in_tail(log, printed):
    log.feed(record("info", "starting_acp_server"))
    assert printed == [] and "starting_acp_server" in log.tail()[0]


@pytest.mark.parametrize("level", ["warning", "error", "critical", "exception", "ERROR"])
def test_feed_when_warning_or_worse_prints_to_output(log, printed, level):
    log.feed(record(level, "boom"))
    assert len(printed) == 1 and printed[0].startswith("[Aidus brain] ") and "boom" in printed[0]


def test_feed_when_plain_text_traceback_prints(log, printed):
    log.feed("Traceback (most recent call last):\n  File \"x\"\nImportError: agentpool\n")
    assert len(printed) == 3 and log.tail(1) == ["ImportError: agentpool"]


def test_feed_when_lines_split_across_chunks_reassembles(log, printed):
    line = record("error", "split ✓")
    log.feed(line[:10])
    assert log.tail() == []
    log.feed(line[10:])
    assert len(log.tail()) == 1 and "split ✓" in log.tail()[0]


def test_feed_when_line_huge_truncates_each_line(log, printed):
    log.feed("x" * 10_000 + "\n")  # non-JSON, so also printed
    assert len(log.tail()[0]) <= 81 and log.tail()[0].endswith("…")
    assert len(printed[0]) <= len("[Aidus brain] ") + 81


def test_feed_when_partial_line_never_ends_is_bounded(log):
    log.feed("y" * 10_000)
    assert len(log._partial) <= 4 * 80
    assert log.tail() and log.tail()[-1].startswith("y")


def test_tail_when_many_lines_keeps_only_the_newest(log):
    for i in range(20):
        log.feed(record("info", "e%d" % i))
    assert len(log.tail(100)) == 5 and "e19" in log.tail(1)[0]


def test_print_limit_when_exceeded_announces_suppression_once(log, printed):
    for i in range(10):
        log.feed(record("error", "e%d" % i))
    assert len(printed) == 4 and "suppressed" in printed[-1]
    log.new_process()
    log.feed(record("error", "after restart"))
    assert "after restart" in printed[-1]


def test_feed_when_blank_or_non_object_json(log, printed):
    log.feed("\n   \n[1, 2]\n\"text\"\n")
    assert len(log.tail()) == 2 and len(printed) == 2, "Non-object JSON is shown like plain text"


def test_summary_when_empty_or_filled(log):
    assert log.summary() == ""
    log.feed("a\nb\n")
    assert log.summary() == "a\nb"


def test_finish_when_stderr_ends_without_newline_keeps_the_text(log, printed):
    log.feed("Fatal: missing dependency")
    assert "Fatal: missing dependency" in log.summary(), "Pending text is part of the diagnostics"
    log.finish()
    assert log.tail(1) == ["Fatal: missing dependency"] and printed[-1].endswith("missing dependency")


def test_new_process_when_called_starts_an_empty_tail(log):
    log.feed("first child said this\n")
    log.new_process()
    assert log.tail() == [] and log.summary() == ""
