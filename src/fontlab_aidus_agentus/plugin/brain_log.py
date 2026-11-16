# this_file: src/fontlab_aidus_agentus/plugin/brain_log.py
"""Bounded record of the brain process's stderr, so its failures are visible in FontLab.

The brain logs JSON lines (structlog). Warnings, errors and non-JSON text
(tracebacks before logging starts) are printed to FontLab's Output panel, at
most `print_limit` lines per process; the newest `keep_lines` lines are kept for
the dock to show when the process fails. Every line is cut to `line_chars`.
"""

from __future__ import annotations

import json
from collections import deque
from typing import Callable, List

PREFIX = "[Aidus brain] "
LOUD_LEVELS = {"warning", "error", "critical", "exception"}


class BrainLog:
    def __init__(
        self,
        keep_lines: int = 200,
        print_limit: int = 50,
        line_chars: int = 1000,
        printer: Callable[[str], None] = print,
    ) -> None:
        self._lines: deque = deque(maxlen=keep_lines)
        self._partial = ""
        self._printed = 0
        self._print_limit = print_limit
        self._chars = line_chars
        self._printer = printer

    def feed(self, text: str) -> None:
        """Accept a stderr chunk; complete lines are recorded, the rest waits."""
        *lines, self._partial = (self._partial + text).split("\n")
        if len(self._partial) > 4 * self._chars:
            lines.append(self._partial)
            self._partial = ""
        for line in lines:
            self._add(line)

    def finish(self) -> None:
        """At EOF, keep text the brain wrote without a final newline."""
        partial, self._partial = self._partial, ""
        self._add(partial)

    def new_process(self) -> None:
        """A fresh brain gets its own tail and Output budget."""
        self._lines.clear()
        self._partial = ""
        self._printed = 0

    def tail(self, count: int = 5) -> List[str]:
        return list(self._lines)[-count:]

    def summary(self, count: int = 5) -> str:
        """The newest lines, including any not yet terminated."""
        lines = self.tail(count)
        if self._partial.strip():
            lines = (lines + [self._partial.rstrip()[: self._chars]])[-count:]
        return "\n".join(lines)

    def _add(self, line: str) -> None:
        line = line.rstrip()
        if not line:
            return
        loud = self._loud(line)
        if len(line) > self._chars:
            line = line[: self._chars] + "…"
        self._lines.append(line)
        if loud:
            self._print(line)

    @staticmethod
    def _loud(line: str) -> bool:
        try:
            record = json.loads(line)
        except ValueError:
            return True
        if not isinstance(record, dict):
            return True
        return str(record.get("level", "")).lower() in LOUD_LEVELS

    def _print(self, line: str) -> None:
        if self._printed < self._print_limit:
            self._printer(PREFIX + line)
        elif self._printed == self._print_limit:
            self._printer(PREFIX + "further messages suppressed; the dock shows the last lines on failure")
        self._printed += 1
