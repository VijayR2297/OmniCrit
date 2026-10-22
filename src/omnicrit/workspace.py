"""The multi-project workspace: one sealed folder per project under ~/.omnicrit/projects."""

from __future__ import annotations

import json
import sqlite3
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml
from pydantic import BaseModel

from omnicrit import paths
from omnicrit.models import GlobalConfig, ProjectConfig, ProjectMarker, new_project_id

MEMORY_SCHEMA_VERSION = 1
PROJECT_SUBDIRS = ("anchors", "runs", "cache")


class WorkspaceError(Exception):
    """A problem the user can fix, such as an unknown project name."""


def _read_yaml[M: BaseModel](path: Path, model: type[M]) -> M:
    data: Any = yaml.safe_load(path.read_text()) or {}
    return model.model_validate(data)


def _write_yaml(path: Path, model: BaseModel) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(yaml.safe_dump(model.model_dump(mode="json"), sort_keys=False))
    tmp.replace(path)


@dataclass(frozen=True)
class Project:
    """A project on disk: its folder plus its loaded config."""

    root: Path
    config: ProjectConfig

    @property
    def config_path(self) -> Path:
        return self.root / "project.yaml"

    @property
    def stack_path(self) -> Path:
        return self.root / "stack.json"

    @property
    def memory_path(self) -> Path:
        return self.root / "memory.db"

    def save(self) -> None:
        _write_yaml(self.config_path, self.config)


class Workspace:
    """Creates, finds and switches between projects."""

    def __init__(self, home: Path | None = None) -> None:
        self.home = home or paths.omnicrit_home()

    @property
    def projects_dir(self) -> Path:
        return self.home / "projects"

    @property
    def config_path(self) -> Path:
        return self.home / "config.yaml"

    # Global config

    def load_config(self) -> GlobalConfig:
        if not self.config_path.exists():
            return GlobalConfig()
        return _read_yaml(self.config_path, GlobalConfig)

    def save_config(self, config: GlobalConfig) -> None:
        _write_yaml(self.config_path, config)

    # Projects

    def create_project(self, name: str) -> Project:
        config = ProjectConfig(id=new_project_id(name), name=name)
        if self.find(config.name, required=False):
            raise WorkspaceError(f"a project named {config.name!r} already exists")
        config.llm = self.load_config().default_llm.model_copy(deep=True)
        root = self.projects_dir / config.id
        root.mkdir(parents=True)
        for sub in PROJECT_SUBDIRS:
            (root / sub).mkdir()
        project = Project(root=root, config=config)
        project.save()
        project.stack_path.write_text(json.dumps({}, indent=2) + "\n")
        _init_memory(project.memory_path)
        return project

    def projects(self) -> list[Project]:
        if not self.projects_dir.exists():
            return []
        found = [
            Project(root=d, config=_read_yaml(d / "project.yaml", ProjectConfig))
            for d in sorted(self.projects_dir.iterdir())
            if (d / "project.yaml").is_file()
        ]
        return sorted(found, key=lambda p: p.config.name.lower())

    def find(self, ref: str, *, required: bool = True) -> Project | None:
        """Find a project by id, slug or name (case-insensitive)."""
        wanted = ref.strip().lower()
        for project in self.projects():
            keys = {project.config.id, project.config.slug, project.config.name.lower()}
            if wanted in keys:
                return project
        if required:
            raise WorkspaceError(f"no project matches {ref!r}; run 'omnicrit list' to see them")
        return None

    def use(self, ref: str) -> Project:
        project = self.find(ref)
        assert project is not None
        config = self.load_config()
        config.active_project = project.config.id
        self.save_config(config)
        return project

    def active(self, cwd: Path | None = None) -> Project | None:
        """The project to work on: a .omnicrit.yaml marker in cwd or a parent wins over 'use'."""
        marker = find_marker(cwd or Path.cwd())
        if marker is not None:
            return self.find(_read_yaml(marker, ProjectMarker).project)
        active_id = self.load_config().active_project
        return self.find(active_id, required=False) if active_id else None

    def link(self, project: Project, folder: Path) -> Path:
        """Write a .omnicrit.yaml marker so this folder always selects the project."""
        marker = folder / paths.MARKER_FILE
        _write_yaml(marker, ProjectMarker(project=project.config.id))
        return marker


def find_marker(start: Path) -> Path | None:
    for folder in (start.resolve(), *start.resolve().parents):
        candidate = folder / paths.MARKER_FILE
        if candidate.is_file():
            return candidate
    return None


def _init_memory(path: Path) -> None:
    """Create the project's memory database. Later modules add their own tables."""
    db = sqlite3.connect(path)
    try:
        with db:
            db.execute(
                "CREATE TABLE IF NOT EXISTS meta (key TEXT PRIMARY KEY, value TEXT NOT NULL)"
            )
            db.execute(
                "INSERT OR REPLACE INTO meta (key, value) VALUES ('schema_version', ?)",
                (str(MEMORY_SCHEMA_VERSION),),
            )
    finally:
        db.close()
