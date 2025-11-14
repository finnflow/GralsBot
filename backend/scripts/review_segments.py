"""Semantischer Review der Segmentierung mittels LLM."""

from __future__ import annotations

import argparse
import json
import logging
import sys
from pathlib import Path
from typing import Any, Dict, List

from dotenv import load_dotenv

try:
    from openai import OpenAI
except ImportError as exc:  # pragma: no cover - graceful error
    raise SystemExit(
        "Das Paket 'openai' wird benötigt, ist aber nicht installiert."
    ) from exc

from backend.config import settings
from backend.scripts import utils
from backend.scripts.segment_utils import compute_offsets, load_segments, normalise_text

LOGGER = logging.getLogger(__name__)
CONTEXT_CHARS = 160


def build_payload(
    original_text: str, segments: List[Dict[str, Any]]
) -> List[Dict[str, Any]]:
    offsets = compute_offsets(original_text, segments)
    payload: List[Dict[str, Any]] = []
    for seg, (start, end) in zip(segments, offsets):
        previous = original_text[max(0, start - CONTEXT_CHARS) : start]
        following = original_text[end : min(len(original_text), end + CONTEXT_CHARS)]
        payload.append(
            {
                "id": seg.get("id"),
                "seg_nr": seg.get("seg_nr"),
                "word_count": seg.get("word_count"),
                "text": seg.get("text"),
                "preceding_context": previous,
                "following_context": following,
            }
        )
    return payload


def build_prompt(kap_nr: int, kap_titel: str, payload: List[Dict[str, Any]]) -> str:
    instructions = (
        "Überprüfe die Segmentgrenzen für das folgende Kapitel."
        " Bewerte, ob Segmente an sinnvollen Stellen enden und ob inhaltliche"
        " Zusammenhänge erhalten bleiben."
        " Melde ausschließlich problematische oder auffällige Fälle."
        " Gib keine Änderungsvorschläge für den Text selbst aus und füge keine"
        " neuen Segmente hinzu."
        " Antworte als JSON-Objekt mit den Feldern kap_nr, kap_titel und findings."
        " findings ist eine Liste von Objekten mit type, seg_id, severity"
        " (low/medium/high) und message."
        " Wenn es keine Auffälligkeiten gibt, gib eine leere Liste zurück."
    )
    payload_json = json.dumps(payload, ensure_ascii=False)
    return (
        f"{instructions}\nKapitelnummer: {kap_nr}\nKapiteltitel: {kap_titel}\n"
        f"Segmente: {payload_json}"
    )


def call_model(prompt: str) -> str:
    load_dotenv()
    client = OpenAI()
    response = client.chat.completions.create(
        model=settings.MODEL_REVIEW,
        temperature=0,
        messages=[
            {
                "role": "system",
                "content": (
                    "Du bist eine prüfende Instanz, die Segmentgrenzen bewertet und"
                    " prägnant dokumentiert."
                ),
            },
            {"role": "user", "content": prompt},
        ],
    )
    try:
        return response.choices[0].message.content or ""
    except (AttributeError, IndexError):  # pragma: no cover
        raise RuntimeError("Unerwartete Antwortstruktur der OpenAI-API.")


def parse_report(raw: str, kap_nr: int, kap_titel: str) -> Dict[str, Any]:
    try:
        data = json.loads(raw)
    except json.JSONDecodeError as exc:
        LOGGER.error("Review-Antwort ist kein gültiges JSON: %s", exc)
        raise

    if not isinstance(data, dict):
        raise ValueError("Review-Antwort muss ein JSON-Objekt sein.")

    findings = data.get("findings", [])
    if not isinstance(findings, list):
        raise ValueError("Feld 'findings' muss eine Liste sein.")

    for entry in findings:
        if not isinstance(entry, dict):
            raise ValueError("Jeder Findings-Eintrag muss ein Objekt sein.")
        if "severity" not in entry:
            entry["severity"] = "medium"

    data.setdefault("kap_nr", kap_nr)
    data.setdefault("kap_titel", kap_titel)
    data["findings"] = findings
    return data


def review_segments(
    kap_nr: int,
    kap_titel: str,
    input_path: Path,
    segments_path: Path,
) -> Dict[str, Any]:
    original_text = normalise_text(input_path.read_text(encoding="utf-8"))
    segments = load_segments(segments_path)
    payload = build_payload(original_text, segments)
    prompt = build_prompt(kap_nr, kap_titel, payload)
    LOGGER.info("Starte Review mit Modell %s", settings.MODEL_REVIEW)
    raw = call_model(prompt)
    return parse_report(raw, kap_nr, kap_titel)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Semantischer Review der Segmentgrenzen.")
    parser.add_argument("--kap-nr", type=int, required=True, help="Kapitelnummer")
    parser.add_argument("--kap-titel", type=str, required=True, help="Kapiteltitel")
    parser.add_argument("--input", type=Path, required=True, help="Kapiteltext (TXT)")
    parser.add_argument("--segments", type=Path, required=True, help="Segment-JSON (Draft)")
    parser.add_argument(
        "--report",
        type=Path,
        required=False,
        help="Pfad zur Review-Reportdatei",
    )
    return parser.parse_args()


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
    args = parse_args()

    try:
        report = review_segments(args.kap_nr, args.kap_titel, args.input, args.segments)
    except Exception as exc:  # pragma: no cover - CLI safeguard
        LOGGER.error("Review fehlgeschlagen: %s", exc)
        sys.exit(1)

    if args.report is not None:
        report_path = args.report
    else:
        base = utils.chapter_basename(args.kap_nr, args.kap_titel)
        report_path = Path(settings.PATH_SEGMENTE) / f"{base}_review.json"

    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    LOGGER.info("Review-Report gespeichert unter %s", report_path)


if __name__ == "__main__":
    main()
