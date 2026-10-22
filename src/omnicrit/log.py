"""Logging: readable output on the terminal, full detail in ~/.omnicrit/logs/omnicrit.log."""

from __future__ import annotations

import logging
from pathlib import Path

from rich.logging import RichHandler

from omnicrit import paths


def setup_logging(verbose: bool = False, log_dir: Path | None = None) -> None:
    folder = log_dir or paths.logs_dir()
    folder.mkdir(parents=True, exist_ok=True)
    file_handler = logging.FileHandler(folder / "omnicrit.log", encoding="utf-8")
    file_handler.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(name)s: %(message)s"))
    file_handler.setLevel(logging.DEBUG)
    console = RichHandler(show_path=False, rich_tracebacks=True)
    console.setLevel(logging.DEBUG if verbose else logging.WARNING)
    logging.basicConfig(level=logging.DEBUG, handlers=[file_handler, console], force=True)
