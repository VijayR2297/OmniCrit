"""The omnicrit command line (also installed as 'crit')."""

from __future__ import annotations

from pathlib import Path
from typing import Annotated

import typer
from rich.console import Console
from rich.table import Table

from omnicrit import __version__, secrets
from omnicrit.log import setup_logging
from omnicrit.models import Environment, Target, TargetKind
from omnicrit.workspace import Project, Workspace, WorkspaceError

app = typer.Typer(
    name="omnicrit",
    help="OmniCrit: an AI testing agent for any app.",
    no_args_is_help=True,
    add_completion=False,
)
target_app = typer.Typer(
    help="Manage the parts of a project that get tested.", no_args_is_help=True
)
secret_app = typer.Typer(help="Store project secrets in the OS keychain.", no_args_is_help=True)
app.add_typer(target_app, name="target")
app.add_typer(secret_app, name="secret")

console = Console()


def _fail(message: str) -> typer.Exit:
    console.print(f"[red]Error:[/red] {message}")
    return typer.Exit(code=1)


def _active(ws: Workspace) -> Project:
    try:
        project = ws.active()
    except WorkspaceError as exc:
        raise _fail(str(exc)) from exc
    if project is None:
        raise _fail("no active project; run 'omnicrit init <name>' or 'omnicrit use <name>'")
    return project


@app.callback()
def main(
    verbose: Annotated[bool, typer.Option("--verbose", "-v", help="Show debug logs.")] = False,
) -> None:
    setup_logging(verbose)


@app.command()
def version() -> None:
    """Print the OmniCrit version."""
    console.print(f"omnicrit {__version__}")


@app.command()
def init(
    name: Annotated[str, typer.Argument(help="Project name, for example 'Shop app'.")],
    link: Annotated[
        bool, typer.Option(help="Write .omnicrit.yaml here so this folder selects the project.")
    ] = False,
) -> None:
    """Create a project and make it the active one."""
    ws = Workspace()
    try:
        project = ws.create_project(name)
    except (WorkspaceError, ValueError) as exc:
        raise _fail(str(exc)) from exc
    ws.use(project.config.id)
    console.print(f"Created project [bold]{project.config.name}[/bold] ({project.config.id})")
    console.print(f"  folder: {project.root}")
    if link:
        marker = ws.link(project, Path.cwd())
        console.print(f"  linked: {marker}")


@app.command("list")
def list_projects() -> None:
    """List all projects."""
    ws = Workspace()
    projects = ws.projects()
    if not projects:
        console.print("No projects yet. Create one with 'omnicrit init <name>'.")
        return
    active = ws.active()
    table = Table("", "Name", "Id", "Targets", "Access level")
    for p in projects:
        mark = "*" if active and active.config.id == p.config.id else ""
        targets = ", ".join(f"{t.name} ({t.kind})" for t in p.config.targets) or "-"
        table.add_row(mark, p.config.name, p.config.id, targets, p.config.access_level)
    console.print(table)


@app.command()
def use(ref: Annotated[str, typer.Argument(help="Project name, slug or id.")]) -> None:
    """Switch the active project."""
    try:
        project = Workspace().use(ref)
    except WorkspaceError as exc:
        raise _fail(str(exc)) from exc
    console.print(f"Active project: [bold]{project.config.name}[/bold] ({project.config.id})")


@app.command()
def current() -> None:
    """Show the active project and where its files live."""
    project = _active(Workspace())
    console.print(f"[bold]{project.config.name}[/bold] ({project.config.id})")
    console.print(f"  folder: {project.root}")
    console.print(f"  access level: {project.config.access_level}")
    for t in project.config.targets:
        envs = ", ".join(e.name for e in t.environments) or "no environments"
        console.print(f"  target {t.name} ({t.kind}): {envs}")


@target_app.command("add")
def target_add(
    name: Annotated[str, typer.Argument(help="Target name, for example 'web' or 'android'.")],
    kind: Annotated[TargetKind, typer.Option(help="What kind of app this is.")],
    env: Annotated[
        list[str] | None,
        typer.Option(help="Environment as name=url-or-path. Repeat for more than one."),
    ] = None,
) -> None:
    """Add a target to the active project."""
    project = _active(Workspace())
    if project.config.target(name):
        raise _fail(f"target {name!r} already exists")
    environments = []
    for item in env or []:
        env_name, sep, location = item.partition("=")
        if not sep or not env_name or not location:
            raise _fail(f"--env must look like name=url-or-path, got {item!r}")
        is_url = location.startswith(("http://", "https://"))
        environments.append(
            Environment(
                name=env_name,
                url=location if is_url else None,
                app_path=None if is_url else location,
            )
        )
    project.config.targets.append(Target(name=name, kind=kind, environments=environments))
    project.save()
    console.print(f"Added target [bold]{name}[/bold] ({kind}) to {project.config.name}")


@secret_app.command("set")
def secret_set(
    name: Annotated[str, typer.Argument(help="Secret name, for example ANTHROPIC_API_KEY.")],
) -> None:
    """Store a secret for the active project (you'll be prompted for the value)."""
    project = _active(Workspace())
    value = typer.prompt(f"Value for {name}", hide_input=True)
    secrets.set_secret(project, name, value)
    console.print(f"Stored {name} in the keychain for {project.config.name}")


@secret_app.command("list")
def secret_list() -> None:
    """List secret names (never values) for the active project."""
    project = _active(Workspace())
    names = project.config.secret_names
    console.print("\n".join(names) if names else "No secrets stored.")


@secret_app.command("delete")
def secret_delete(name: Annotated[str, typer.Argument()]) -> None:
    """Delete a secret from the keychain."""
    project = _active(Workspace())
    secrets.delete_secret(project, name)
    console.print(f"Deleted {name}")
