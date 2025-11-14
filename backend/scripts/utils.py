"""Hilfsfunktionen für Skripte im GralsBot-Projekt."""

from __future__ import annotations

import re
from pathlib import Path
from typing import Iterable


def project_root() -> Path:
    """Return the absolute path to the repository root."""
    return Path(__file__).resolve().parents[2]


def ensure_directories(paths: Iterable[Path]) -> None:
    """Ensure that every directory in ``paths`` exists."""
    for directory in paths:
        directory.mkdir(parents=True, exist_ok=True)


def slugify(value: str) -> str:
    """Convert ``value`` into a filesystem-friendly slug."""
    slug = re.sub(r"[^0-9A-Za-z]+", "_", value, flags=re.UNICODE).strip("_")
    return slug or "Kapitel"


def chapter_basename(kap_nr: int, kap_titel: str) -> str:
    """Return a canonical basename for chapter artefacts."""
    return f"K{int(kap_nr):03d}_{slugify(kap_titel)}"


def default_segment_path(kap_nr: int, kap_titel: str, directory: Path) -> Path:
    """Return the default draft JSON path for a chapter."""
    return directory / f"{chapter_basename(kap_nr, kap_titel)}_draft.json"


__all__ = [
    "project_root",
    "ensure_directories",
    "slugify",
    "chapter_basename",
    "default_segment_path",
]
