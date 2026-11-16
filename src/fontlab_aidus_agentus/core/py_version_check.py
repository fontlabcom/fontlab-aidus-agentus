# this_file: src/fontlab_aidus_agentus/core/py_version_check.py
# Copyright 2025 Fontlab Ltd. All rights reserved.
"""Python version check for Aidus Agentus Core."""

import sys

MINIMUM_PYTHON = (3, 13)


def check_python_version() -> None:
    """
    Assert that the Python version meets minimum requirements.

    Raises:
        RuntimeError: If Python version is below 3.13.
    """
    if sys.version_info < MINIMUM_PYTHON:
        raise RuntimeError(
            f"Aidus Agentus Core requires Python {MINIMUM_PYTHON[0]}.{MINIMUM_PYTHON[1]} or higher. "
            f"Current version: {sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}"
        )
