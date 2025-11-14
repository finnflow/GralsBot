"""Deterministische Validierung der von LLM erzeugten Segmente."""

from __future__ import annotations

import argparse
import json
import logging
import sys
from pathlib import Path
from typing import Any, Dict, List, Tuple

from backend.config import settings
from backend.scripts import utils
from backend.scripts.segment_utils import (
    count_words,
    id_matches,
    load_segments,
    normalise_text,
    save_segments,
)

LOGGER = logging.getLogger(__name__)
REQUIRED_FIELDS = {"id", "kap_nr", "kap_titel", "seg_nr", "word_count", "text"}


def _issue(issue_type: str, seg_id: str | None, message: str) -> Dict[str, Any]:
    return {"type": issue_type, "seg_id": seg_id, "message": message}


def _sentence_boundary_warning(text: str) -> bool:
    trimmed = text.rstrip()
    if not trimmed:
        return False
    closing_chars = '"\'”»›)]}'
    while trimmed and trimmed[-1] in closing_chars:
        trimmed = trimmed[:-1].rstrip()
    return bool(trimmed and trimmed[-1] not in ".?!")


def validate_segments(
    kap_nr_hint: int | None,
    input_path: Path,
    segments_path: Path,
) -> Tuple[Dict[str, Any], List[Dict[str, Any]]]:
    original_text = normalise_text(input_path.read_text(encoding="utf-8"))
    raw_segments = load_segments(segments_path)

    if not raw_segments:
        raise ValueError("Segmentdatei enthält keine Einträge.")

    errors: List[Dict[str, Any]] = []
    warnings: List[Dict[str, Any]] = []
    normalised_segments: List[Dict[str, Any]] = []

    first = raw_segments[0]
    kap_nr = int(first.get("kap_nr", kap_nr_hint or 0))
    kap_titel = str(first.get("kap_titel", ""))

    if kap_nr_hint is not None and kap_nr != int(kap_nr_hint):
        warnings.append(
            _issue(
                "kap_nr_mismatch",
                first.get("id"),
                f"Kapitelnummer in Datei ({kap_nr}) weicht vom Parameter ({kap_nr_hint}) ab.",
            )
        )

    cursor = 0
    expected_seg_nr = 1

    for seg in raw_segments:
        seg_id = seg.get("id") if isinstance(seg, dict) else None
        if not isinstance(seg, dict):
            errors.append(
                _issue(
                    "schema",
                    None,
                    "Jedes Segment muss ein Objekt mit Feldern sein.",
                )
            )
            continue

        missing = REQUIRED_FIELDS - set(seg.keys())
        if missing:
            errors.append(
                _issue(
                    "schema",
                    seg_id if isinstance(seg_id, str) else None,
                    f"Fehlende Felder: {sorted(missing)}",
                )
            )
            continue

        try:
            seg_nr = int(seg["seg_nr"])
            seg_kap_nr = int(seg["kap_nr"])
            word_count_reported = int(seg["word_count"])
        except (TypeError, ValueError):
            errors.append(
                _issue(
                    "schema",
                    seg_id if isinstance(seg_id, str) else None,
                    "seg_nr, kap_nr und word_count müssen Ganzzahlen sein.",
                )
            )
            continue

        text = seg.get("text")
        if not isinstance(text, str):
            errors.append(
                _issue("schema", seg_id, "text-Feld muss ein String sein."),
            )
            continue

        if seg_kap_nr != kap_nr:
            errors.append(
                _issue(
                    "kap_nr_inconsistent",
                    seg_id,
                    f"Kapitelnummer {seg_kap_nr} passt nicht zu {kap_nr}.",
                )
            )
        if str(seg.get("kap_titel", "")).strip() != kap_titel.strip():
            errors.append(
                _issue(
                    "kap_titel_inconsistent",
                    seg_id,
                    "kap_titel weicht von den anderen Segmenten ab.",
                )
            )

        if seg_nr != expected_seg_nr:
            errors.append(
                _issue(
                    "seg_nr_sequence",
                    seg_id,
                    f"Erwartet wurde seg_nr {expected_seg_nr}, gefunden {seg_nr}.",
                )
            )
        expected_seg_nr += 1

        if not id_matches(kap_nr, str(seg_id), seg_nr):
            errors.append(
                _issue(
                    "id_format",
                    seg_id,
                    "Segment-ID entspricht nicht dem Muster KNNN-SMMM.",
                )
            )

        start = cursor
        end = start + len(text)
        snippet = original_text[start:end]
        if snippet != text:
            errors.append(
                _issue(
                    "text_mismatch",
                    seg_id,
                    "Segmenttext stimmt nicht exakt mit dem Original überein.",
                )
            )
        cursor = end

        if "char_start" in seg and seg["char_start"] != start:
            errors.append(
                _issue(
                    "char_start",
                    seg_id,
                    f"char_start {seg['char_start']} stimmt nicht mit {start} überein.",
                )
            )
        if "char_end" in seg and seg["char_end"] != end:
            errors.append(
                _issue(
                    "char_end",
                    seg_id,
                    f"char_end {seg['char_end']} stimmt nicht mit {end} überein.",
                )
            )

        actual_word_count = count_words(text)
        if actual_word_count != word_count_reported:
            errors.append(
                _issue(
                    "word_count",
                    seg_id,
                    f"Wortanzahl {word_count_reported} stimmt nicht mit {actual_word_count} überein.",
                )
            )

        if actual_word_count < settings.SEG_MIN_WORDS:
            warnings.append(
                _issue(
                    "segment_length",
                    seg_id,
                    f"Segment hat nur {actual_word_count} Wörter (< {settings.SEG_MIN_WORDS}).",
                )
            )
        if actual_word_count > settings.SEG_HARD_MAX:
            warnings.append(
                _issue(
                    "segment_length",
                    seg_id,
                    f"Segment hat {actual_word_count} Wörter (> {settings.SEG_HARD_MAX}).",
                )
            )

        if _sentence_boundary_warning(text):
            warnings.append(
                _issue(
                    "sentence_boundary",
                    seg_id,
                    "Segment endet nicht auf ., ! oder ? (abzüglich Abschlusszeichen).",
                )
            )

        normalised = dict(seg)
        normalised["char_start"] = start
        normalised["char_end"] = end
        normalised["word_count"] = actual_word_count
        normalised_segments.append(normalised)

    if cursor != len(original_text):
        errors.append(
            _issue(
                "coverage",
                None,
                "Segmente decken den Originaltext nicht vollständig ab.",
            )
        )

    status = "ok"
    if errors:
        status = "errors"
    elif warnings:
        status = "warnings"

    report = {
        "kap_nr": kap_nr,
        "kap_titel": kap_titel,
        "status": status,
        "errors": errors,
        "warnings": warnings,
    }
    return report, normalised_segments


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Validiert Segment-JSON gegen den Originaltext.")
    parser.add_argument("--kap-nr", type=int, required=False, help="Kapitelnummer für Logging")
    parser.add_argument("--input", type=Path, required=True, help="Kapiteltext (TXT)")
    parser.add_argument("--segments", type=Path, required=True, help="Segment-JSON (Draft)")
    parser.add_argument(
        "--report",
        type=Path,
        required=False,
        help="Pfad zur Validierungs-Reportdatei",
    )
    parser.add_argument(
        "--normalized-output",
        type=Path,
        required=False,
        help="Optionaler Pfad für normalisierte Segmente",
    )
    return parser.parse_args()


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
    args = parse_args()

    try:
        report, normalised_segments = validate_segments(
            args.kap_nr, args.input, args.segments
        )
    except Exception as exc:  # pragma: no cover - CLI safeguard
        LOGGER.error("Validierung fehlgeschlagen: %s", exc)
        sys.exit(1)

    if args.report is not None:
        report_path = args.report
    else:
        base = utils.chapter_basename(
            report["kap_nr"], report.get("kap_titel", "")
        )
        report_path = Path(settings.PATH_SEGMENTE) / f"{base}_validation.json"

    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    LOGGER.info("Validierungsreport gespeichert unter %s", report_path)

    if args.normalized_output:
        save_segments(args.normalized_output, normalised_segments)
        LOGGER.info("Normalisierte Segmente gespeichert unter %s", args.normalized_output)

    if report["status"] == "errors":
        sys.exit(1)


if __name__ == "__main__":
    main()
