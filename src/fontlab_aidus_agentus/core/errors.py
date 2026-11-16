# this_file: src/fontlab_aidus_agentus/core/errors.py
# Copyright 2025 Fontlab Ltd. All rights reserved.
from __future__ import annotations

from enum import Enum
from typing import Any


class ErrorCategory(str, Enum):
    VALIDATION = "validation"
    TOOL_EXECUTION = "tool_execution"
    FONTLAB_CONNECTION = "fontlab_connection"
    CONFIGURATION = "configuration"
    INTERNAL = "internal"


class AidusError(Exception):
    def __init__(
        self,
        message: str,
        category: ErrorCategory,
        code: str | None = None,
        details: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(message)
        self.message = message
        self.category = category
        self.code = code or category.value.upper()
        self.details = details or {}

    def to_dict(self) -> dict[str, Any]:
        return {
            "error": self.message,
            "category": self.category.value,
            "code": self.code,
            "details": self.details,
        }


class ValidationError(AidusError):
    def __init__(self, message: str, field: str | None = None) -> None:
        details = {"field": field} if field else {}
        super().__init__(message, ErrorCategory.VALIDATION, details=details)


class ToolExecutionError(AidusError):
    def __init__(self, message: str, tool_name: str) -> None:
        super().__init__(
            message,
            ErrorCategory.TOOL_EXECUTION,
            details={"tool": tool_name},
        )


class FontLabConnectionError(AidusError):
    def __init__(self, message: str = "FontLab is not responding") -> None:
        super().__init__(message, ErrorCategory.FONTLAB_CONNECTION)


class ConfigurationError(AidusError):
    def __init__(self, message: str) -> None:
        super().__init__(message, ErrorCategory.CONFIGURATION)
