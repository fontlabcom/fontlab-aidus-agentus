# this_file: tests/core/test_errors.py
from __future__ import annotations

from fontlab_aidus_agentus.core.errors import (
    AidusError,
    ErrorCategory,
    ToolExecutionError,
    ValidationError,
)


def test_aidus_error_to_dict():
    err = AidusError("test message", ErrorCategory.INTERNAL)
    result = err.to_dict()
    assert result["error"] == "test message"
    assert result["category"] == "internal"
    assert result["code"] == "INTERNAL"


def test_validation_error_includes_field():
    err = ValidationError("invalid value", field="width")
    result = err.to_dict()
    assert result["details"]["field"] == "width"


def test_tool_execution_error_includes_tool_name():
    err = ToolExecutionError("failed", tool_name="run_fontlab_script")
    result = err.to_dict()
    assert result["details"]["tool"] == "run_fontlab_script"
