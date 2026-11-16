# this_file: tests/plugin/test_config.py
# Copyright 2025 Fontlab Ltd. All rights reserved.
"""Tests for plugin configuration module."""

from __future__ import annotations

import json
import os
import tempfile
from unittest import mock

from fontlab_aidus_agentus.plugin import config


class TestDefaultConfig:
    def test_default_config_has_expected_keys(self):
        defaults = config._DEFAULT_CONFIG
        assert "core_path" in defaults
        assert "python_exe" in defaults
        assert "timeout_seconds" in defaults
        assert "log_level" in defaults
        assert "api_keys" in defaults

    def test_default_timeout_is_30_seconds(self):
        assert config._DEFAULT_CONFIG["timeout_seconds"] == 30

    def test_default_log_level_is_info(self):
        assert config._DEFAULT_CONFIG["log_level"] == "INFO"

    def test_default_core_path_is_none(self):
        assert config._DEFAULT_CONFIG["core_path"] is None


class TestFindConfigPaths:
    def test_returns_list_of_paths(self):
        paths = config._find_config_paths()
        assert isinstance(paths, list)
        assert len(paths) >= 2

    def test_includes_project_root_path(self):
        paths = config._find_config_paths()
        assert any("aidus_config.json" in p for p in paths)

    def test_includes_home_config_path(self):
        paths = config._find_config_paths()
        home = os.path.expanduser("~")
        assert any(home in p for p in paths)

    def test_find_config_paths_when_renamed_then_new_folder_precedes_legacy_fallback(self):
        home = os.path.expanduser("~")
        paths = config._find_config_paths()
        current = os.path.join(home, ".config", "aidus_agentus", "config.json")
        legacy = os.path.join(home, ".config", "aidus_code", "config.json")
        assert paths.index(current) < paths.index(legacy), "pre-rename config must stay readable, after the new one"


class TestLoadConfig:
    def test_returns_dict(self):
        result = config.load_config()
        assert isinstance(result, dict)

    def test_returns_default_when_no_file(self):
        with mock.patch.object(
            config, "_find_config_paths", return_value=["/nonexistent/path.json"]
        ):
            result = config.load_config()
            assert result["timeout_seconds"] == 30

    def test_loads_from_file(self):
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            json.dump({"timeout_seconds": 60, "log_level": "DEBUG"}, f)
            temp_path = f.name

        try:
            with mock.patch.object(config, "_find_config_paths", return_value=[temp_path]):
                result = config.load_config()
                assert result["timeout_seconds"] == 60
                assert result["log_level"] == "DEBUG"
                assert result["_loaded_from"] == temp_path
        finally:
            os.unlink(temp_path)

    def test_ignores_invalid_json(self):
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            f.write("{invalid json}")
            temp_path = f.name

        try:
            with mock.patch.object(config, "_find_config_paths", return_value=[temp_path]):
                result = config.load_config()
                assert result["timeout_seconds"] == 30
        finally:
            os.unlink(temp_path)


class TestGetApiKey:
    def test_returns_none_for_unconfigured_provider(self):
        cfg = {"api_keys": {}}
        with mock.patch.dict(os.environ, {}, clear=True):
            result = config.get_api_key(cfg, "nonexistent")
            assert result is None

    def test_reads_from_env_var_by_default(self):
        cfg = {"api_keys": {}}
        with mock.patch.dict(os.environ, {"OPENAI_API_KEY": "sk-test123"}):
            result = config.get_api_key(cfg, "openai")
            assert result == "sk-test123"

    def test_reads_from_env_prefix(self):
        cfg = {"api_keys": {"openai": "env:MY_CUSTOM_KEY"}}
        with mock.patch.dict(os.environ, {"MY_CUSTOM_KEY": "sk-custom"}):
            result = config.get_api_key(cfg, "openai")
            assert result == "sk-custom"

    def test_reads_from_file(self):
        with tempfile.NamedTemporaryFile(mode="w", suffix=".key", delete=False) as f:
            f.write("sk-from-file\n")
            temp_path = f.name

        try:
            cfg = {"api_keys": {"openai": temp_path}}
            result = config.get_api_key(cfg, "openai")
            assert result == "sk-from-file"
        finally:
            os.unlink(temp_path)

    def test_strips_whitespace_from_file(self):
        with tempfile.NamedTemporaryFile(mode="w", suffix=".key", delete=False) as f:
            f.write("  sk-test  \n\n")
            temp_path = f.name

        try:
            cfg = {"api_keys": {"openai": temp_path}}
            result = config.get_api_key(cfg, "openai")
            assert result == "sk-test"
        finally:
            os.unlink(temp_path)


class TestSaveDefaultConfig:
    def test_saves_to_specified_path(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            path = os.path.join(tmpdir, "test_config.json")
            result = config.save_default_config(path)
            assert result is True
            assert os.path.exists(path)

    def test_saved_config_is_valid_json(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            path = os.path.join(tmpdir, "test_config.json")
            config.save_default_config(path)
            with open(path) as f:
                data = json.load(f)
            assert "timeout_seconds" in data
            assert "api_keys" in data

    def test_returns_false_on_error(self):
        result = config.save_default_config("/nonexistent/dir/config.json")
        assert result is False


class TestCheckFirstRunSetup:
    def test_returns_dict_with_ready_key(self):
        result = config.check_first_run_setup()
        assert isinstance(result, dict)
        assert "ready" in result
        assert "issues" in result
        assert "hints" in result

    def test_defers_provider_keys_to_selected_manifest(self):
        with mock.patch.object(config, "get_api_key", return_value=None):
            result = config.check_first_run_setup()
            assert not any("API key" in issue for issue in result["issues"])


class TestGetFirstRunMessage:
    def test_returns_none_when_ready(self):
        with mock.patch.object(
            config,
            "check_first_run_setup",
            return_value={"ready": True, "issues": [], "hints": []},
        ):
            result = config.get_first_run_message()
            assert result is None

    def test_returns_message_when_not_ready(self):
        status = {
            "ready": False,
            "issues": ["No API key configured"],
            "hints": ["Set OPENAI_API_KEY"],
        }
        with mock.patch.object(config, "check_first_run_setup", return_value=status):
            result = config.get_first_run_message()
            assert result is not None
            assert "No API key configured" in result
            assert "OPENAI_API_KEY" in result
