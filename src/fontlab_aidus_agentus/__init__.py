# this_file: src/fontlab_aidus_agentus/__init__.py
"""Embedded FontLab client; the external AgentPool brain is loaded lazily."""
from importlib.metadata import version, PackageNotFoundError

try:
    __version__ = version("fontlab-aidus-agentus")
except PackageNotFoundError:
    __version__ = "0+unknown"


def run() -> None:
    """Open the embedded ACP client dock in FontLab."""
    from fontlab_aidus_agentus.plugin.main import run as run_plugin
    run_plugin()


def shutdown() -> None:
    """Stop the client process and remove its dock."""
    from fontlab_aidus_agentus.plugin.main import shutdown as shutdown_plugin
    shutdown_plugin()
