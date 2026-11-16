# this_file: tests/core/test_agents_yml.py
# Copyright 2025 Fontlab Ltd. All rights reserved.
"""
Tests for agents.yml configuration parsing and validation.

Covers:
- YAML syntax validation
- Required fields validation
- Agent definition structure
- Tool definition structure
- System prompt loading
- Default agent validation
"""

from __future__ import annotations

from pathlib import Path

import pytest
import yaml

from fontlab_aidus_agentus.core import boot

# =============================================================================
# Fixtures
# =============================================================================


@pytest.fixture
def agents_yml_path() -> Path:
    """Return path to the actual agents.yml file."""
    return Path(boot.__file__).with_name("agents.yml")


@pytest.fixture
def agents_yml_content(agents_yml_path: Path) -> dict:
    """Load and return the agents.yml content."""
    with open(agents_yml_path) as f:
        return yaml.safe_load(f)


# =============================================================================
# YAML Syntax Tests
# =============================================================================


class TestYamlSyntax:
    """Test that agents.yml is valid YAML."""

    def test_file_exists(self, agents_yml_path: Path) -> None:
        """Verify agents.yml exists."""
        assert agents_yml_path.exists(), f"agents.yml not found at {agents_yml_path}"

    def test_valid_yaml_syntax(self, agents_yml_path: Path) -> None:
        """Verify agents.yml is valid YAML."""
        with open(agents_yml_path) as f:
            content = yaml.safe_load(f)
        assert isinstance(content, dict), "agents.yml must be a YAML mapping"

    def test_no_yaml_parsing_errors(self, agents_yml_path: Path) -> None:
        """Verify no YAML parsing errors occur."""
        try:
            with open(agents_yml_path) as f:
                yaml.safe_load(f)
        except yaml.YAMLError as e:
            pytest.fail(f"YAML parsing error: {e}")


# =============================================================================
# Required Fields Tests
# =============================================================================


class TestRequiredFields:
    """Test that all required top-level fields are present."""

    def test_has_default_agent(self, agents_yml_content: dict) -> None:
        """Verify default_agent field exists."""
        assert "default_agent" in agents_yml_content

    def test_has_agents(self, agents_yml_content: dict) -> None:
        """Verify agents field exists."""
        assert "agents" in agents_yml_content

    def test_default_agent_is_string(self, agents_yml_content: dict) -> None:
        """Verify default_agent is a string."""
        assert isinstance(agents_yml_content["default_agent"], str)

    def test_agents_is_dict(self, agents_yml_content: dict) -> None:
        """Verify agents is a dictionary."""
        assert isinstance(agents_yml_content["agents"], dict)

    def test_default_agent_exists_in_agents(self, agents_yml_content: dict) -> None:
        """Verify the default agent is defined in agents."""
        default = agents_yml_content["default_agent"]
        agents = agents_yml_content["agents"]
        assert default in agents, f"Default agent '{default}' not found in agents"


# =============================================================================
# Agent Definition Tests
# =============================================================================


class TestAgentDefinitions:
    """Test the structure of agent definitions."""

    def test_all_agents_have_required_fields(self, agents_yml_content: dict) -> None:
        """Verify each agent has required fields."""
        required_fields = {"type", "model"}
        agents = agents_yml_content["agents"]

        for name, config in agents.items():
            for field in required_fields:
                assert field in config, f"Agent '{name}' missing field '{field}'"

    def test_agent_type_is_valid(self, agents_yml_content: dict) -> None:
        """Verify agent type is a recognized value."""
        valid_types = {"native", "acp"}
        agents = agents_yml_content["agents"]

        for name, config in agents.items():
            assert config["type"] in valid_types, (
                f"Agent '{name}' has invalid type '{config['type']}'"
            )

    def test_agent_model_is_string(self, agents_yml_content: dict) -> None:
        """Verify agent model is a string."""
        agents = agents_yml_content["agents"]

        for name, config in agents.items():
            assert isinstance(config["model"], str), f"Agent '{name}' model must be a string"

    def test_agent_tools_is_list(self, agents_yml_content: dict) -> None:
        """Verify agent tools is a list when present."""
        agents = agents_yml_content["agents"]

        for name, config in agents.items():
            if "tools" in config:
                assert isinstance(config["tools"], list), f"Agent '{name}' tools must be a list"

    def test_agent_max_tokens_is_int(self, agents_yml_content: dict) -> None:
        """Verify max_tokens is an integer when present."""
        agents = agents_yml_content["agents"]

        for name, config in agents.items():
            if "max_tokens" in config:
                assert isinstance(config["max_tokens"], int), (
                    f"Agent '{name}' max_tokens must be int"
                )
                assert config["max_tokens"] > 0, f"Agent '{name}' max_tokens must be positive"

    def test_agent_temperature_is_number(self, agents_yml_content: dict) -> None:
        """Verify temperature is a number when present."""
        agents = agents_yml_content["agents"]

        for name, config in agents.items():
            if "temperature" in config:
                temp = config["temperature"]
                assert isinstance(temp, (int, float)), (
                    f"Agent '{name}' temperature must be a number"
                )
                assert 0 <= temp <= 2, f"Agent '{name}' temperature must be 0-2"


# =============================================================================
# Tool Definition Tests
# =============================================================================


class TestToolDefinitions:
    """Test the structure of tool definitions."""

    def test_tools_section_exists(self, agents_yml_content: dict) -> None:
        """Verify tools section exists."""
        assert "tools" in agents_yml_content

    def test_tools_is_dict(self, agents_yml_content: dict) -> None:
        """Verify tools is a dictionary."""
        assert isinstance(agents_yml_content["tools"], dict)

    def test_all_tools_have_description(self, agents_yml_content: dict) -> None:
        """Verify each tool has a description."""
        tools = agents_yml_content.get("tools", {})

        for name, config in tools.items():
            assert "description" in config, f"Tool '{name}' missing 'description' field"

    def test_tool_parameters_structure(self, agents_yml_content: dict) -> None:
        """Verify tool parameters have correct structure when non-empty."""
        tools = agents_yml_content.get("tools", {})
        valid_types = {"string", "number", "integer", "boolean", "array", "object"}

        for name, config in tools.items():
            if "parameters" not in config:
                continue
            params = config["parameters"]
            if not params:
                continue  # Empty parameters dict is valid
            # JSON Schema style: {type: object, properties: {...}, required: [...]}
            if isinstance(params, dict) and "type" in params:
                assert params["type"] in valid_types, (
                    f"Tool '{name}' parameters type '{params['type']}' invalid"
                )
                if "properties" in params:
                    for pname, pconfig in params["properties"].items():
                        assert "type" in pconfig, f"Tool '{name}' param '{pname}' missing type"
                        assert pconfig["type"] in valid_types, (
                            f"Tool '{name}' param '{pname}' has invalid type"
                        )

    def test_referenced_tools_exist(self, agents_yml_content: dict) -> None:
        """Verify tools referenced by agents exist in the tools section."""
        agents = agents_yml_content.get("agents", {})
        tools = agents_yml_content.get("tools", {})

        for agent_name, agent_config in agents.items():
            agent_tools = agent_config.get("tools", [])
            for tool_entry in agent_tools:
                # Agent tools are list of {name: ..., enabled: ...} dicts
                tool_name = tool_entry["name"] if isinstance(tool_entry, dict) else tool_entry
                assert tool_name in tools, (
                    f"Agent '{agent_name}' references undefined tool '{tool_name}'"
                )


# =============================================================================
# System Prompt Tests
# =============================================================================


class TestSystemPrompts:
    """Test system prompt configuration."""

    def test_prompts_section_optional(self, agents_yml_content: dict) -> None:
        """Verify prompts section exists (may be empty)."""
        # Prompts section is optional but if present should be dict
        if "prompts" in agents_yml_content:
            assert isinstance(agents_yml_content["prompts"], dict)

    def test_agent_system_prompts_valid(self, agents_yml_content: dict) -> None:
        """Verify system_prompt references are valid."""
        agents = agents_yml_content.get("agents", {})
        prompts = agents_yml_content.get("prompts", {})

        for name, config in agents.items():
            if "system_prompt" in config:
                prompt_ref = config["system_prompt"]
                # Can be a direct string or a file reference
                if isinstance(prompt_ref, dict) and "file" in prompt_ref:
                    # File reference - check prompts directory
                    pass  # File existence checked at runtime
                elif isinstance(prompt_ref, str) and prompt_ref.startswith("$"):
                    ref_name = prompt_ref[1:]
                    assert ref_name in prompts, (
                        f"Agent '{name}' references undefined prompt '{ref_name}'"
                    )


# =============================================================================
# Specific Agent Tests
# =============================================================================


class TestExpectedAgents:
    """Test that expected agents exist with correct configuration."""

    def test_fontlab_copilot_exists(self, agents_yml_content: dict) -> None:
        """Verify fontlab_copilot agent exists."""
        agents = agents_yml_content.get("agents", {})
        assert "fontlab_copilot" in agents

    def test_fontlab_copilot_has_tools(self, agents_yml_content: dict) -> None:
        """Verify fontlab_copilot has tools configured."""
        copilot = agents_yml_content["agents"]["fontlab_copilot"]
        assert "tools" in copilot
        assert len(copilot["tools"]) > 0

    def test_fontlab_copilot_is_default(self, agents_yml_content: dict) -> None:
        """Verify fontlab_copilot is the default agent."""
        assert agents_yml_content["default_agent"] == "fontlab_copilot"


# =============================================================================
# Pydantic Schema Validation Tests
# =============================================================================


class TestSchemaValidation:
    """Test Pydantic schema validation."""

    def test_validate_agents_yml_succeeds(
        self, agents_yml_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Verify validate_agents_yml succeeds with valid file."""
        monkeypatch.setenv("OPENAI_API_KEY", "sk-test-key")

        from fontlab_aidus_agentus.core.config import validate_agents_yml

        result = validate_agents_yml(agents_yml_path)
        assert result is not None
        assert result.default_agent == "fontlab_copilot"

    def test_validate_agents_yml_returns_schema(
        self, agents_yml_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Verify validate_agents_yml returns AgentsYmlSchema."""
        monkeypatch.setenv("OPENAI_API_KEY", "sk-test-key")

        from fontlab_aidus_agentus.core.config import AgentsYmlSchema, validate_agents_yml

        result = validate_agents_yml(agents_yml_path)
        assert isinstance(result, AgentsYmlSchema)

    def test_validate_agents_yml_missing_file(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Verify validate_agents_yml raises on missing file."""
        monkeypatch.setenv("OPENAI_API_KEY", "sk-test-key")

        from fontlab_aidus_agentus.core.config import validate_agents_yml

        with pytest.raises((FileNotFoundError, OSError)):
            validate_agents_yml(tmp_path / "nonexistent.yml")
