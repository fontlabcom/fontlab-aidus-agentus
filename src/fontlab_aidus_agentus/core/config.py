# this_file: src/fontlab_aidus_agentus/core/config.py
# Copyright 2025 Fontlab Ltd. All rights reserved.
from __future__ import annotations

from pathlib import Path
from typing import Any, Literal

import yaml
from pydantic import BaseModel, Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

_CORE_DIR = Path(__file__).resolve().parent
_ENV_FILE = _CORE_DIR / ".env"


class Settings(BaseSettings):
    """
    Application settings loaded from environment variables.

    Attributes:
        openai_api_key: OpenAI API key (required, must start with 'sk-').
        anthropic_api_key: Anthropic API key (optional).
        log_level: Logging level (default: INFO).
        core_host: Host for core server (default: 127.0.0.1).
        core_port: Port for core server (default: 8765).
    """

    model_config = SettingsConfigDict(
        env_file=str(_ENV_FILE),
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    openai_api_key: str = Field(
        ...,
        description="OpenAI API key",
    )
    anthropic_api_key: str | None = Field(
        default=None,
        description="Anthropic API key (optional)",
    )
    log_level: Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"] = Field(
        default="INFO",
        description="Logging level",
    )
    core_host: str = Field(
        default="127.0.0.1",
        description="Host address for core server",
    )
    core_port: int = Field(
        default=8765,
        ge=1024,
        le=65535,
        description="Port for core server",
    )

    @field_validator("openai_api_key")
    @classmethod
    def validate_openai_key(cls, v: str) -> str:
        """Validate that OpenAI API key has correct format."""
        if not v.startswith("sk-"):
            raise ValueError("OpenAI API key must start with 'sk-'")
        return v


def get_settings() -> Settings:
    return Settings()


class ToolConfig(BaseModel):
    name: str
    enabled: bool = True


class SystemPromptFile(BaseModel):
    type: Literal["file"]
    path: str


class AgentConfig(BaseModel):
    type: Literal["native", "acp"] = "native"
    model: str
    system_prompt: str | SystemPromptFile
    tools: list[ToolConfig] = Field(default_factory=list)
    max_tokens: int = Field(default=4096, ge=1, le=128000)
    temperature: float = Field(default=0.7, ge=0.0, le=2.0)


class AgentsYmlSchema(BaseModel):
    default_agent: str
    agents: dict[str, AgentConfig]
    tools: dict[str, Any] | None = None
    prompts: dict[str, str] | None = None

    @field_validator("agents")
    @classmethod
    def validate_default_agent_exists(
        cls, v: dict[str, AgentConfig], info: Any
    ) -> dict[str, AgentConfig]:
        return v


def validate_agents_yml(path: Path) -> AgentsYmlSchema:
    with path.open() as f:
        data = yaml.safe_load(f)
    schema = AgentsYmlSchema(**data)
    if schema.default_agent not in schema.agents:
        msg = f"default_agent '{schema.default_agent}' not in agents"
        raise ValueError(msg)
    return schema
