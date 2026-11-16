# this_file: src/fontlab_aidus_agentus/plugin/__init__.py
# Copyright 2025 Fontlab Ltd. All rights reserved.
"""Aidus Agentus Plugin - FontLab PythonQt ACP Client."""

from typing import Any, Optional, Tuple

__version__ = "1.0.2"

_bootstrap_fn: Any = None
_run_fn: Any = None
_shutdown_fn: Any = None

try:
    from fontlab_aidus_agentus.plugin.main import bootstrap as _bootstrap_fn
    from fontlab_aidus_agentus.plugin.main import run as _run_fn
    from fontlab_aidus_agentus.plugin.main import shutdown as _shutdown_fn
except ImportError:
    pass


def parse_version(version_string: str) -> Tuple[int, int, int]:
    """Parse version string into (major, minor, patch) tuple."""
    try:
        parts = version_string.split(".")
        major = int(parts[0]) if len(parts) > 0 else 0
        minor = int(parts[1]) if len(parts) > 1 else 0
        patch = int(parts[2].split("-")[0]) if len(parts) > 2 else 0
        return (major, minor, patch)
    except (ValueError, AttributeError):
        return (0, 0, 0)


def is_compatible(core_version: str) -> bool:
    """Check if core version is compatible with this plugin version."""
    plugin_ver = parse_version(__version__)
    core_ver = parse_version(core_version)
    if plugin_ver[0] != core_ver[0]:
        return False
    if core_ver[1] < plugin_ver[1]:
        return False
    return True


def bootstrap() -> Optional[Any]:
    if _bootstrap_fn is None:
        raise ImportError("Plugin must be loaded from FontLab")
    return _bootstrap_fn()


def run() -> None:
    if _run_fn is None:
        raise ImportError("Plugin must be loaded from FontLab")
    _run_fn()


def shutdown() -> None:
    if _shutdown_fn is None:
        raise ImportError("Plugin must be loaded from FontLab")
    _shutdown_fn()


__all__ = ["__version__", "parse_version", "is_compatible", "bootstrap", "run", "shutdown"]
