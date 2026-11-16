# this_file: src/fontlab_aidus_agentus/core/__init__.py
# Copyright 2025 Fontlab Ltd. All rights reserved.
"""
Aidus Agentus Core - AgentPool ACP Server for FontLab.

This package provides the AI "brain" that communicates with the FontLab
plugin via the Agent Client Protocol (ACP).
"""

from fontlab_aidus_agentus.core.py_version_check import check_python_version

check_python_version()

__version__ = "1.0.0"
__all__ = ["__version__"]
