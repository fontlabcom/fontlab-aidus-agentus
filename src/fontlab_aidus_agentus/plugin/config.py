# this_file: src/fontlab_aidus_agentus/plugin/config.py
# Copyright 2025 Fontlab Ltd. All rights reserved.
"""Configuration loader for Aidus Agentus Plugin (E7.14)."""

from __future__ import annotations

import json
import os
from typing import Any, Dict, Optional

_DEFAULT_CONFIG: Dict[str, Any] = {
    "core_path": None,  # Auto-detect if None
    "python_exe": None,  # Auto-detect if None
    "timeout_seconds": 30,
    "log_level": "INFO",
    "api_keys": {},  # Map of provider -> key_source (file path or env var name)
}


def _find_config_paths() -> list[str]:
    """Return list of potential config file locations in priority order."""
    explicit = os.environ.get("AIDUS_CONFIG")
    if explicit:
        return [os.path.expanduser(explicit)]
    paths: list[str] = []

    plugin_dir = os.path.dirname(os.path.abspath(__file__))
    project_dir = os.path.dirname(plugin_dir)

    paths.append(os.path.join(project_dir, "aidus_config.json"))
    paths.append(os.path.join(plugin_dir, "aidus_config.json"))

    home = os.path.expanduser("~")
    paths.append(os.path.join(home, ".config", "aidus_agentus", "config.json"))
    # Read-only fallback: the folder used before the Aidus Agentus rename.
    paths.append(os.path.join(home, ".config", "aidus_code", "config.json"))
    paths.append(os.path.join(home, ".aidus_config.json"))

    return paths


def load_config() -> Dict[str, Any]:
    """Load configuration from aidus_config.json.

    Searches in order:
    1. Project root/aidus_config.json
    2. Plugin dir/aidus_config.json
    3. ~/.config/aidus_agentus/config.json
    4. ~/.config/aidus_code/config.json (pre-rename location, still read)
    5. ~/.aidus_config.json

    Reports invalid/unreadable files without contents and tries the next path.
    Returns default config if no valid UTF-8 JSON object is found.
    """
    config = _DEFAULT_CONFIG.copy()

    for path in _find_config_paths():
        if os.path.exists(path):
            try:
                with open(path, "r", encoding="utf-8") as f:
                    user_config = json.load(f)
                    if isinstance(user_config, dict):
                        config.update(user_config)
                        config["_loaded_from"] = path
                        break
                reason = "expected a JSON object"
            except UnicodeDecodeError:
                reason = "not UTF-8"
            except json.JSONDecodeError:
                reason = "invalid JSON"
            except OSError:
                reason = "unreadable"
            print(
                f"[Aidus Agentus] Skipping configuration ({reason}): {path}. "
                "Open this file in a text editor to repair it as a UTF-8 JSON object."
            )

    return config


def get_api_key(config: Dict[str, Any], provider: str) -> Optional[str]:
    """Get API key for a provider from config, file, or environment."""
    api_keys = config.get("api_keys", {})
    key_source = api_keys.get(provider)

    if not key_source:
        env_var = "%s_API_KEY" % provider.upper()
        return os.environ.get(env_var)

    if key_source.startswith("env:"):
        env_var = key_source[4:]
        return os.environ.get(env_var)

    key_path = os.path.expanduser(key_source)
    if os.path.exists(key_path):
        try:
            with open(key_path, "r", encoding="utf-8") as f:
                return f.read().strip()
        except OSError:
            pass

    return None



def child_environment(config: Dict[str, Any]) -> Dict[str, str]:
    """Resolve configured key sources only into canonical child variables."""
    aliases = {"mistralai": "mistral", "gemini": "google"}
    result = {}
    for provider in config.get("api_keys", {}):
        key = get_api_key(config, provider)
        if key:
            canonical = aliases.get(provider, provider).upper() + "_API_KEY"
            result[canonical] = key
    return result


def save_default_config(path: Optional[str] = None) -> bool:
    """Save a default config file template."""
    if path is None:
        plugin_dir = os.path.dirname(os.path.abspath(__file__))
        project_dir = os.path.dirname(plugin_dir)
        path = os.path.join(project_dir, "aidus_config.json")

    template = {
        "core_path": None,
        "python_exe": None,
        "timeout_seconds": 30,
        "log_level": "INFO",
        "api_keys": {
            "openai": "env:OPENAI_API_KEY",
            "mistral": "~/.config/mistral/api_key",
        },
    }

    try:
        with open(path, "w", encoding="utf-8") as f:
            json.dump(template, f, indent=2)
        return True
    except OSError:
        return False


def check_first_run_setup() -> Dict[str, Any]:
    """Check if initial setup is complete and return status (E9.13)."""
    config = load_config()
    issues: list[str] = []
    hints: list[str] = []

    # The external brain validates credentials for its selected manifest.
    # Test/local models must not require unrelated hosted-provider keys here.
    plugin_dir = os.path.dirname(os.path.abspath(__file__))
    project_dir = os.path.dirname(plugin_dir)
    from pathlib import Path
    import fontlab_aidus_agentus
    core_dir = config.get("core_path") or str(Path(fontlab_aidus_agentus.__file__).parent)
    boot_script = os.path.join(core_dir, "core_launcher.py")
    if config.get("core_path") and not os.path.exists(boot_script):
        boot_script = os.path.join(core_dir, "boot.py")

    if not os.path.exists(boot_script):
        issues.append("Core boot.py not found at %s" % boot_script)
        hints.append("Install fontlab-aidus-agentus[brain] in external Python 3.13+ and set AIDUS_PYTHON")

    return {
        "ready": len(issues) == 0,
        "issues": issues,
        "hints": hints,
        "config_loaded": config.get("_loaded_from"),
    }


def get_first_run_message() -> Optional[str]:
    """Return a user-friendly message if first-run setup is incomplete (E9.13)."""
    status = check_first_run_setup()
    if status["ready"]:
        return None

    lines = ["Aidus Agentus needs setup before first use:", ""]
    for issue in status["issues"]:
        lines.append("  [!] " + issue)

    if status["hints"]:
        lines.append("")
        lines.append("To fix:")
        for hint in status["hints"]:
            lines.append("  - " + hint)

    return "\n".join(lines)
