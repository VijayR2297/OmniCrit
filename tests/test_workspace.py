from __future__ import annotations

import json
import sqlite3
from pathlib import Path

import pytest

from omnicrit.workspace import Workspace, WorkspaceError


def test_create_project_lays_out_folder(isolated_home: Path) -> None:
    project = Workspace().create_project("Shop app")

    assert project.root.parent == isolated_home / "projects"
    assert project.config.id.startswith("shop-app-")
    for sub in ("anchors", "runs", "cache"):
        assert (project.root / sub).is_dir()
    assert json.loads(project.stack_path.read_text()) == {}
    with sqlite3.connect(project.memory_path) as db:
        row = db.execute("SELECT value FROM meta WHERE key = 'schema_version'").fetchone()
    assert row == ("1",)


def test_duplicate_names_are_rejected() -> None:
    ws = Workspace()
    ws.create_project("Shop app")
    with pytest.raises(WorkspaceError):
        ws.create_project("shop app")


def test_find_by_id_slug_or_name() -> None:
    ws = Workspace()
    project = ws.create_project("Bank Portal")
    for ref in (project.config.id, "bank-portal", "bank portal", "BANK PORTAL"):
        found = ws.find(ref)
        assert found is not None
        assert found.config.id == project.config.id


def test_use_switches_between_projects() -> None:
    ws = Workspace()
    shop = ws.create_project("Shop app")
    bank = ws.create_project("Bank portal")

    ws.use("shop-app")
    assert ws.active() is not None and ws.active().config.id == shop.config.id  # type: ignore[union-attr]
    ws.use("bank-portal")
    assert ws.active() is not None and ws.active().config.id == bank.config.id  # type: ignore[union-attr]


def test_marker_in_parent_folder_beats_use(tmp_path: Path) -> None:
    ws = Workspace()
    shop = ws.create_project("Shop app")
    bank = ws.create_project("Bank portal")
    repo = tmp_path / "shop-repo"
    nested = repo / "src" / "deep"
    nested.mkdir(parents=True)
    ws.link(shop, repo)
    ws.use(bank.config.id)

    active = ws.active(cwd=nested)
    assert active is not None and active.config.id == shop.config.id


def test_projects_are_isolated() -> None:
    ws = Workspace()
    shop = ws.create_project("Shop app")
    bank = ws.create_project("Bank portal")
    assert shop.root != bank.root
    assert shop.memory_path != bank.memory_path
