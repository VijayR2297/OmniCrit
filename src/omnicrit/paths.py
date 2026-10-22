"""Where OmniCrit keeps its files on disk."""

from __future__ import annotations

import os
from pathlib import Path

HOME_ENV = "OMNICRIT_HOME"
MARKER_FILE = ".omnicrit.yaml"


def omnicrit_home() -> Path:
    """Root folder for all OmniCrit data. Override with the OMNICRIT_HOME environment variable."""
    override = os.environ.get(HOME_ENV)
    return Path(override).expanduser() if override else Path.home() / ".omnicrit"


def projects_dir() -> Path:
    return omnicrit_home() / "projects"


def global_config_path() -> Path:
    return omnicrit_home() / "config.yaml"


def logs_dir() -> Path:
    return omnicrit_home() / "logs"
