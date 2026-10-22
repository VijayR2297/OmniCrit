"""Configuration models for the workspace, projects, targets and environments."""

from __future__ import annotations

import re
import secrets
from datetime import UTC, datetime
from enum import StrEnum

from pydantic import BaseModel, Field, field_validator


class TargetKind(StrEnum):
    WEB = "web"
    ANDROID = "android"
    IOS = "ios"
    API = "api"
    DESKTOP = "desktop"


class AccessLevel(StrEnum):
    """How deep the agent can see into the app. See the spec's 'Access levels' section."""

    BLACK_BOX = "black_box"
    GREY_BOX = "grey_box"
    WHITE_BOX = "white_box"


class Environment(BaseModel):
    """One place a target runs, such as dev or staging."""

    name: str
    url: str | None = None
    app_path: str | None = None


class Target(BaseModel):
    """One testable part of a project, such as its web app or Android app."""

    name: str
    kind: TargetKind
    environments: list[Environment] = Field(default_factory=list)

    def environment(self, name: str) -> Environment | None:
        return next((env for env in self.environments if env.name == name), None)


class LLMSettings(BaseModel):
    """Which model to use for each job. Model names follow LiteLLM's 'provider/model' form."""

    provider: str = "anthropic"
    models: dict[str, str] = Field(
        default_factory=lambda: {
            "explore": "anthropic/claude-sonnet-5-5",
            "plan": "anthropic/claude-sonnet-5-5",
            "heal": "anthropic/claude-sonnet-5-5",
            "summarise": "anthropic/claude-haiku-5-5",
        }
    )
    token_budget: int | None = None


def slugify(name: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-")
    if not slug:
        raise ValueError(f"cannot make a project slug from {name!r}")
    return slug


def new_project_id(name: str) -> str:
    return f"{slugify(name)}-{secrets.token_hex(2)}"


class ProjectConfig(BaseModel):
    """Contents of a project's project.yaml."""

    id: str
    name: str
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    access_level: AccessLevel = AccessLevel.BLACK_BOX
    targets: list[Target] = Field(default_factory=list)
    llm: LLMSettings = Field(default_factory=LLMSettings)
    secret_names: list[str] = Field(default_factory=list)

    @field_validator("name")
    @classmethod
    def _name_not_blank(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("project name must not be blank")
        return value.strip()

    @property
    def slug(self) -> str:
        return slugify(self.name)

    def target(self, name: str) -> Target | None:
        return next((t for t in self.targets if t.name == name), None)


class GlobalConfig(BaseModel):
    """Contents of ~/.omnicrit/config.yaml."""

    active_project: str | None = None
    default_llm: LLMSettings = Field(default_factory=LLMSettings)


class ProjectMarker(BaseModel):
    """Contents of a .omnicrit.yaml file that ties a folder to a project."""

    project: str
