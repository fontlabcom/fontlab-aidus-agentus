# this_file: tests/plugin/test_executor.py
# Copyright 2025 Fontlab Ltd. All rights reserved.
from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from fontlab_aidus_agentus.plugin.executor import FontLabExecutor, ToolRegistry


def _noop() -> None:
    pass


class TestToolRegistry:
    def test_register_and_get(self) -> None:
        registry = ToolRegistry()
        registry.register("test_tool", _noop)
        assert registry.has("test_tool")
        assert registry.get("test_tool") is _noop

    def test_get_unknown_returns_none(self) -> None:
        registry = ToolRegistry()
        assert registry.get("unknown") is None

    def test_list_all(self) -> None:
        registry = ToolRegistry()
        registry.register("tool_a", _noop)
        registry.register("tool_b", _noop)
        tools = registry.list_all()
        assert "tool_a" in tools
        assert "tool_b" in tools

    def test_get_info(self) -> None:
        registry = ToolRegistry()
        registry.register("test", lambda: None, required_params=["a"], optional_params=["b"])
        info = registry.get_info("test")
        assert info is not None
        assert info["required_params"] == ["a"]
        assert info["optional_params"] == ["b"]


class TestFontLabExecutorInit:
    def test_init_registers_builtin_tools(self) -> None:
        executor = FontLabExecutor()
        assert executor.has_tool("get_current_glyph_info")
        assert executor.has_tool("set_glyph_metrics")
        assert executor.has_tool("run_fontlab_script")
        assert executor.has_tool("list_tools")

    def test_list_tools(self) -> None:
        executor = FontLabExecutor()
        tools = executor.list_tools()
        assert len(tools) >= 4


class TestArgumentValidation:
    def test_missing_required_param(self) -> None:
        executor = FontLabExecutor()
        result = executor.run("run_fontlab_script", {})
        assert "error" in result
        assert "Missing" in result["error"]
        assert "code" in result["error"]

    def test_unknown_param_with_registry(self) -> None:
        executor = FontLabExecutor()
        result = executor.run("run_fontlab_script", {"code": "pass", "bogus": 1})
        assert "error" in result
        assert "Unknown" in result["error"]


class TestResultSanitization:
    def test_sanitize_none(self) -> None:
        executor = FontLabExecutor()
        result = executor._sanitize_result(None)
        assert result == {"success": True}

    def test_sanitize_dict(self) -> None:
        executor = FontLabExecutor()
        result = executor._sanitize_result({"key": "value"})
        assert result == {"key": "value"}

    def test_sanitize_list(self) -> None:
        executor = FontLabExecutor()
        result = executor._sanitize_result([1, 2, 3])
        assert result == {"result": [1, 2, 3]}

    def test_sanitize_nested(self) -> None:
        executor = FontLabExecutor()
        result = executor._sanitize_result({"outer": {"inner": [1, "two"]}})
        assert result == {"outer": {"inner": [1, "two"]}}

    def test_sanitize_object_to_string(self) -> None:
        executor = FontLabExecutor()
        obj = object()
        result = executor._sanitize_value(obj)
        assert isinstance(result, str)


class TestFontGlyphGuards:
    def test_require_font_without_fontlab(self) -> None:
        executor = FontLabExecutor()
        result = executor._require_font()
        assert result is not None
        assert "error" in result

    def test_require_glyph_without_fontlab(self) -> None:
        executor = FontLabExecutor()
        result = executor._require_glyph()
        assert result is not None
        assert "error" in result


class TestUnknownTool:
    def test_unknown_tool_returns_error(self) -> None:
        executor = FontLabExecutor()
        result = executor.run("nonexistent_tool", {})
        assert "error" in result
        assert "Unknown tool" in result["error"]


class TestListToolsTool:
    def test_list_tools_returns_all(self) -> None:
        executor = FontLabExecutor()
        result = executor.run("list_tools", {})
        assert "tools" in result
        tool_names = [t["name"] for t in result["tools"]]
        assert "get_current_glyph_info" in tool_names
        assert "set_glyph_metrics" in tool_names


class TestScriptExecution:
    def test_run_simple_script(self) -> None:
        executor = FontLabExecutor()
        result = executor.run("run_fontlab_script", {"code": "result = 42"})
        assert "error" not in result
        assert result.get("result") == 42

    def test_run_script_with_error(self) -> None:
        executor = FontLabExecutor()
        result = executor.run("run_fontlab_script", {"code": "1/0"})
        assert "error" in result
        assert "traceback" in result

    def test_run_script_syntax_error(self) -> None:
        executor = FontLabExecutor()
        result = executor.run("run_fontlab_script", {"code": "def foo("})
        assert "error" in result


class TestTimeout:
    def test_set_timeout(self) -> None:
        executor = FontLabExecutor()
        executor.set_timeout(60)
        assert executor._timeout_seconds == 60


class TestToolsNeedFontlab:
    def test_get_glyph_info_needs_fontlab(self) -> None:
        executor = FontLabExecutor()
        result = executor.run("get_current_glyph_info", {})
        assert "error" in result

    def test_set_metrics_needs_fontlab(self) -> None:
        executor = FontLabExecutor()
        result = executor.run("set_glyph_metrics", {"width": 500})
        assert "error" in result
