"""Project secrets (API keys, test passwords) stored in the OS keychain, never on disk."""

from __future__ import annotations

import keyring

from omnicrit.workspace import Project

SERVICE_PREFIX = "omnicrit"


def _service(project: Project) -> str:
    return f"{SERVICE_PREFIX}:{project.config.id}"


def set_secret(project: Project, name: str, value: str) -> None:
    keyring.set_password(_service(project), name, value)
    if name not in project.config.secret_names:
        project.config.secret_names.append(name)
        project.save()


def get_secret(project: Project, name: str) -> str | None:
    return keyring.get_password(_service(project), name)


def delete_secret(project: Project, name: str) -> None:
    keyring.delete_password(_service(project), name)
    if name in project.config.secret_names:
        project.config.secret_names.remove(name)
        project.save()
