# this_file: src/fontlab_aidus_agentus/plugin/main.py
# Copyright 2025 Fontlab Ltd. All rights reserved.
"""
Aidus Agentus Plugin - Main Bootstrap Entry Point (Epoch 7).

This module provides the main entry point for the Aidus Agentus plugin in FontLab.
It instantiates all components (Transport, Client, Executor, UI) and wires them
together using Qt signals and slots.
"""

from __future__ import annotations

import os
import sys
from typing import TYPE_CHECKING, Any, Optional

# Guard FontLab imports for outside-FontLab linting
_fl_available = False
fl: Any = None
try:
    import fontlab as fl  # type: ignore[import-not-found, no-redef]

    _fl_available = True
except ImportError:
    _fl_available = False

FL_AVAILABLE = _fl_available

if TYPE_CHECKING:
    from fontlab_aidus_agentus.plugin.ui import AidusAgentusDock


# Dock widget reference (persisted for FontLab session)
_dock: Optional[AidusAgentusDock] = None
# (signal, slot) pairs this module connected; disconnected again on shutdown.
_connections: list = []


def _resolve_paths() -> tuple[str, str, str]:
    """
    Resolve paths to Python executable, boot.py script, and core directory.

    Returns:
        Tuple of (python_exe_path, boot_script_path, core_dir_path).
    """
    # Load config first to check for overrides
    from fontlab_aidus_agentus.plugin.config import load_config

    config = load_config()

    from pathlib import Path
    import shutil
    import fontlab_aidus_agentus

    package_dir = Path(fontlab_aidus_agentus.__file__).parent
    core_dir = os.path.expanduser(config.get("core_path") or str(package_dir))
    boot_script = str(Path(core_dir) / "core_launcher.py")
    if config.get("core_path") and not os.path.exists(boot_script):
        boot_script = os.path.join(core_dir, "boot.py")
    configured = os.environ.get("AIDUS_PYTHON") or config.get("python_exe")
    python_exe = os.path.expanduser(configured) if configured else shutil.which("fontlab-aidus-python")
    if python_exe is None:
        raise RuntimeError("Set AIDUS_PYTHON or python_exe to an external Python 3.13+ environment with fontlab-aidus-agentus[brain] installed")
    return (python_exe, boot_script, core_dir)



def bootstrap() -> Optional[AidusAgentusDock]:
    """
    Bootstrap the Aidus Agentus plugin.

    Initializes all components and wires signals/slots. Returns the dock widget
    for registration with FontLab's main window.

    Returns:
        The AidusAgentusDock widget, or None on failure.
    """
    global _dock

    # Import components (late import to avoid circular deps)
    from fontlab_aidus_agentus.plugin.client import AidusAgentusClient
    from fontlab_aidus_agentus.plugin.config import child_environment, get_first_run_message, load_config
    from fontlab_aidus_agentus.plugin.executor import FontLabExecutor
    from fontlab_aidus_agentus.plugin.transport import ACPTransport
    from fontlab_aidus_agentus.plugin.ui import AidusAgentusDock

    # E9.13: Check first run setup
    first_run_msg = get_first_run_message()

    # Load config for transport settings
    config = load_config()
    timeout_seconds = config.get("timeout_seconds", 30)

    # Resolve paths
    python_exe, boot_script, core_dir = _resolve_paths()

    # Instantiate Executor
    executor = FontLabExecutor()

    # Instantiate Transport with working directory and timeout from config
    transport = ACPTransport(
        python_exe=python_exe,
        boot_script=boot_script,
        timeout_seconds=timeout_seconds,
        working_dir=core_dir,
        environment=child_environment(config),
    )

    # Step 5: Instantiate Client with Transport and Executor
    client = AidusAgentusClient(transport=transport, executor=executor)

    # Step 6: Instantiate UI dock widget with Client
    dock = AidusAgentusDock(client=client)
    _dock = dock
    _show_brain_stderr(transport, dock)

    # E9.13: Show first run message if setup incomplete
    if first_run_msg:
        dock.show_error(first_run_msg)
        return dock

    # Step 7: Additional signal wiring (beyond what components do internally)
    # Client chatUpdate -> UI is already wired in AidusAgentusDock.__init__
    # Client stateChanged -> UI is already wired in AidusAgentusDock.__init__

    # Step 8: Start transport (launches Core process)
    success, error = transport.start()
    if not success:
        dock.show_error("Failed to start Core: %s" % error)
        return dock

    # Step 9 & 10: Initialize client (ACP handshake)
    if not client.initialize():
        dock.show_error("Failed to initialize ACP client")
        return dock

    # Step 11 & 12: UI status updated via stateChanged signal

    return dock


def _show_brain_stderr(transport: Any, dock: Any, printer: Any = print) -> Any:
    """Brain warnings/errors go to the Output panel; failures show a bounded tail in the dock."""
    from fontlab_aidus_agentus.plugin.brain_log import BrainLog

    log = BrainLog(printer=printer)

    def finished(exit_code: int, *rest: Any) -> None:
        log.finish()
        if exit_code and log.tail():
            dock.show_error("Brain exited with code %d. Last messages:\n%s" % (exit_code, log.summary()))
        elif exit_code:
            dock.show_error("Brain exited with code %d." % exit_code)
        log.new_process()

    def failed(message: str, *rest: Any) -> None:
        if log.summary():
            dock.show_error("Recent brain messages:\n%s" % log.summary())

    for signal, slot in (
        (transport.stderrReceived, log.feed),
        (transport.processFinished, finished),
        (transport.processError, failed),
    ):
        signal.connect(slot)
        _connections.append((signal, slot))
    return log


def _disconnect_all() -> None:
    while _connections:
        signal, slot = _connections.pop()
        try:
            signal.disconnect(slot)
        except Exception:  # noqa: BLE001 - already disconnected or host refused
            pass


def run() -> None:
    """
    Main entry point for FontLab plugin.

    Called when FontLab loads the plugin. Bootstraps components and registers
    the dock widget with FontLab's main window.
    """
    if not FL_AVAILABLE:
        print("[aidus_agentus] FontLab not available - running in standalone mode")
        return

    dock = bootstrap()
    if dock is None:
        print("[aidus_agentus] Failed to bootstrap plugin")
        return

    # Register dock with FontLab's main window
    try:
        from PythonQt.QtCore import Qt

        main_window = fl.flWorkspace.instance().mainWindow
        main_window.addDockWidget(Qt.LeftDockWidgetArea, dock)
        print("[aidus_agentus] Plugin loaded successfully")
    except Exception as e:
        print("[aidus_agentus] Failed to register dock: %s" % str(e))


def get_dock() -> Optional[AidusAgentusDock]:
    """Get the current dock widget instance (for scripting/debugging)."""
    return _dock


def shutdown() -> None:
    """Clean shutdown of the plugin."""
    global _dock

    if _dock is not None:
        client = _dock.get_client()
        if client is not None:
            if client._transport is not None:
                if client._transport.stop() is False:
                    return
            client.cleanup()
        _disconnect_all()
        _dock.close()
        _dock.deleteLater()
        _dock = None


if __name__ == "__main__":
    # Allow running outside FontLab for basic testing
    print("[aidus_agentus] Running in test mode (no FontLab)")
    dock = bootstrap()
    if dock:
        print("[aidus_agentus] Bootstrap completed successfully")
    else:
        print("[aidus_agentus] Bootstrap failed")
