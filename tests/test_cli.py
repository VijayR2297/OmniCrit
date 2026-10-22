from __future__ import annotations

import keyring
from typer.testing import CliRunner

from omnicrit.cli import app
from omnicrit.workspace import Workspace

runner = CliRunner()


def run(*args: str, input: str | None = None) -> str:
    result = runner.invoke(app, list(args), input=input)
    assert result.exit_code == 0, result.output
    return result.output


def test_version() -> None:
    assert "omnicrit 0.1.0" in run("version")


def test_init_list_use_current() -> None:
    run("init", "Shop app")
    run("init", "Bank portal")
    listing = run("list")
    assert "Shop app" in listing and "Bank portal" in listing

    assert "Bank portal" in run("current")
    run("use", "shop-app")
    assert "Shop app" in run("current")


def test_init_link_writes_marker() -> None:
    run("init", "Shop app", "--link")
    assert Workspace().active() is not None
    from pathlib import Path

    assert Path(".omnicrit.yaml").is_file()


def test_unknown_project_fails_cleanly() -> None:
    result = runner.invoke(app, ["use", "nope"])
    assert result.exit_code == 1
    assert "no project matches" in result.output


def test_target_add() -> None:
    run("init", "Shop app")
    run("target", "add", "web", "--kind", "web", "--env", "staging=https://staging.example.com")
    run("target", "add", "android", "--kind", "android", "--env", "dev=./build/app.apk")
    project = Workspace().active()
    assert project is not None
    web = project.config.target("web")
    android = project.config.target("android")
    assert web is not None and web.environments[0].url == "https://staging.example.com"
    assert android is not None and android.environments[0].app_path == "./build/app.apk"


def test_secrets_go_to_keychain_not_disk() -> None:
    run("init", "Shop app")
    run("secret", "set", "ANTHROPIC_API_KEY", input="sk-test-123\n")
    project = Workspace().active()
    assert project is not None
    service = f"omnicrit:{project.config.id}"
    assert keyring.get_password(service, "ANTHROPIC_API_KEY") == "sk-test-123"
    assert "sk-test-123" not in project.config_path.read_text()
    assert "ANTHROPIC_API_KEY" in run("secret", "list")
