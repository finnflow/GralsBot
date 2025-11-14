"""Gemeinsame Utilities für Segmentierungs-Skripte."""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any, Dict, Iterable, List, Sequence, Tuple

_WORD_PATTERN = re.compile(r"\b\w+\b", re.UNICODE)


def load_segments(path: Path) -> List[Dict[str, Any]]:
    """Load a JSON file containing a list of segment dicts."""
    with path.open("r", encoding="utf-8") as f:
        data = json.load(f)
    if not isinstance(data, list):
        raise ValueError("Segmentdatei muss ein JSON-Array enthalten.")
    return data


def save_segments(path: Path, segments: Iterable[Dict[str, Any]]) -> None:
    """Write ``segments`` as UTF-8 JSON."""
    with path.open("w", encoding="utf-8") as f:
        json.dump(list(segments), f, ensure_ascii=False, indent=2)


def count_words(text: str) -> int:
    """Return a simple word count for ``text`` (unicode aware)."""
    return len(_WORD_PATTERN.findall(text))


def normalise_text(text: str) -> str:
    """Normalise line endings for reliable comparisons."""
    return text.replace("\r\n", "\n")


def compute_offsets(original_text: str, segments: Sequence[Dict[str, Any]]) -> List[Tuple[int, int]]:
    """Compute (start, end) character offsets for ``segments``.

    Segments must appear in order without gaps. Raises ``ValueError`` if a
    segment text is not found at the expected position.
    """

    offsets: List[Tuple[int, int]] = []
    cursor = 0
    for seg in segments:
        text = seg.get("text", "")
        if not isinstance(text, str):
            raise ValueError("Segment enthält kein Textfeld vom Typ String.")
        end = cursor + len(text)
        snippet = original_text[cursor:end]
        if snippet != text:
            raise ValueError(
                "Segmenttext stimmt nicht mit dem Originaltext überein (ID "
                f"{seg.get('id', 'unbekannt')})."
            )
        offsets.append((cursor, end))
        cursor = end
    return offsets


def id_matches(kap_nr: int, seg_id: str, seg_nr: int) -> bool:
    """Return whether ``seg_id`` matches the canonical pattern."""
    if not isinstance(seg_id, str):
        return False
    pattern = rf"^K{int(kap_nr):03d}-S{int(seg_nr):03d}$"
    return re.fullmatch(pattern, seg_id) is not None


__all__ = [
    "load_segments",
    "save_segments",
    "count_words",
    "normalise_text",
    "compute_offsets",
    "id_matches",
]
