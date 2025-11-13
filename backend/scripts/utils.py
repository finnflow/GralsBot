"""Hilfsfunktionen für Skripte im GralsBot-Projekt."""

from __future__ import annotations

from pathlib import Path
from typing import Iterable


def project_root() -> Path:
    """Return the absolute path to the repository root."""
    return Path(__file__).resolve().parents[2]


def ensure_directories(paths: Iterable[Path]) -> None:
    """Ensure that every directory in ``paths`` exists."""
    for directory in paths:
        directory.mkdir(parents=True, exist_ok=True)
