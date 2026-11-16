# this_file: tests/test_executor_preflight_errors.py
"""Native preflight failures obey the same error contract as tool handlers."""
from types import SimpleNamespace

import pytest

from fontlab_aidus_agentus.plugin import executor


@pytest.mark.parametrize("getter", ["CurrentFont", "CurrentGlyph"])
@pytest.mark.parametrize("error", [RuntimeError("owned getter failure"), executor.ToolError("owned refusal")])
@pytest.mark.parametrize("tool,args", [("get_current_glyph_info", {}), ("set_glyph_metrics", {"width": 600})])
def test_run_when_preflight_getter_raises_then_returns_error_without_handler(monkeypatch, getter, error, tool, args):
    calls = []
    def fail():
        calls.append(getter)
        raise error
    api = SimpleNamespace(CurrentFont=lambda: object(), CurrentGlyph=lambda: object())
    setattr(api, getter, fail)
    monkeypatch.setattr(executor, "fl", api)
    monkeypatch.setattr(executor, "FL_AVAILABLE", True)
    def handler(*args, **kwargs):
        pytest.fail("A failed preflight must not enter a tool handler")
    monkeypatch.setattr(executor.FontLabExecutor, "_get_current_glyph_info", handler)
    monkeypatch.setattr(executor.FontLabExecutor, "_set_glyph_metrics", handler)
    result = executor.FontLabExecutor().run(tool, args)
    expected = str(error) if isinstance(error, executor.ToolError) else "Execution error: " + str(error)
    assert result == {"error": expected}, "Use the existing handler error contract"
    assert calls == [getter], "Do not retry a failed native getter"


def test_run_when_preflight_is_interrupted_then_propagates_interruption(monkeypatch):
    def interrupt():
        raise KeyboardInterrupt("owned interruption")
    monkeypatch.setattr(executor, "FL_AVAILABLE", True)
    monkeypatch.setattr(executor, "fl", SimpleNamespace(CurrentFont=interrupt))
    with pytest.raises(KeyboardInterrupt, match="owned interruption"):
        executor.FontLabExecutor().run("get_current_glyph_info")
