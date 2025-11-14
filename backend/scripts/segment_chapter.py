"""Segmentiert ein Kapitel mithilfe eines LLMs."""

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
except ImportError as exc:  # pragma: no cover - graceful error for missing dependency
    raise SystemExit(
        "Das Paket 'openai' wird benötigt, ist aber nicht installiert."
    ) from exc

from backend.config import settings
from backend.scripts.segment_utils import save_segments
from backend.scripts.segment_utils import id_matches
from backend.scripts.utils import default_segment_path, ensure_directories

LOGGER = logging.getLogger(__name__)
PROMPT_FILE = Path(__file__).with_name("segmentierung_prompt.md")


def load_prompt_template() -> str:
    if not PROMPT_FILE.exists():
        raise FileNotFoundError(
            f"Prompt-Datei wurde nicht gefunden: {PROMPT_FILE}"
        )
    return PROMPT_FILE.read_text(encoding="utf-8")


def build_prompt(kap_nr: int, kap_titel: str, text: str) -> str:
    template = load_prompt_template()
    rules = (
        "Segmentierungsregeln:\n"
        f"- Decke den gesamten Text ohne Auslassungen ab.\n"
        "- Formuliere den Text nicht um, übernimm ihn 1:1 aus dem Original.\n"
        "- Verwende Segment-IDs im Format KNNN-SMMM.\n"
        f"- Zielwortanzahl je Segment: {settings.SEG_TARGET_MIN} bis {settings.SEG_TARGET_MAX} Wörter.\n"
        f"- Harte Obergrenze: maximal {settings.SEG_HARD_MAX} Wörter.\n"
        f"- Mindestlänge: mindestens {settings.SEG_MIN_WORDS} Wörter, falls der Text es zulässt.\n"
        "- Liefere die Ausgabe als JSON-Array ohne zusätzlichen Text.\n"
        "- Felder pro Segment: id, kap_nr, kap_titel, seg_nr, word_count, text.\n"
        "- Optional: char_start und char_end können ergänzt werden, falls verfügbar.\n"
        "- Stelle sicher, dass word_count zur tatsächlichen Wortanzahl passt.\n"
    )
    metadata = (
        f"Kapitelnummer: {kap_nr}\n"
        f"Kapiteltitel: {kap_titel}\n"
    )
    prompt = (
        f"{template}\n\n{rules}\n{metadata}\n"
        "Kapiteltext (übernimm exakt diesen Text, keine Änderungen):\n"
        "<<<TEXT_BEGIN>>>\n"
        f"{text}\n"
        "<<<TEXT_END>>>\n"
        "Gib ausschließlich das JSON-Array der Segmente zurück."
    )
    return prompt


def call_model(prompt: str) -> str:
    load_dotenv()
    client = OpenAI()
    response = client.chat.completions.create(
        model=settings.MODEL_SEGMENTATION,
        temperature=0,
        messages=[
            {
                "role": "system",
                "content": (
                    "Du bist ein akribischer Editor, der Kapiteltexte ohne Änderungen "
                    "segmentiert und konsistente IDs vergibt."
                ),
            },
            {"role": "user", "content": prompt},
        ],
    )
    try:
        return response.choices[0].message.content or ""
    except (AttributeError, IndexError):  # pragma: no cover - defensive coding
        raise RuntimeError("Unerwartete Antwortstruktur der OpenAI-API.")


def parse_segments(raw: str) -> List[Dict[str, Any]]:
    try:
        data = json.loads(raw)
    except json.JSONDecodeError as exc:
        LOGGER.error("Antwort ist kein gültiges JSON: %s", exc)
        raise

    if isinstance(data, dict) and "segments" in data:
        data = data["segments"]

    if not isinstance(data, list):
        raise ValueError("Die Antwort muss ein JSON-Array mit Segmenten sein.")

    segments: List[Dict[str, Any]] = []
    for entry in data:
        if not isinstance(entry, dict):
            raise ValueError("Jedes Segment muss ein JSON-Objekt sein.")
        segments.append(entry)
    if not segments:
        raise ValueError("Keine Segmente erhalten.")
    return segments


def schema_check(segments: List[Dict[str, Any]], kap_nr: int, kap_titel: str) -> None:
    for idx, seg in enumerate(segments, start=1):
        missing = {
            "id",
            "kap_nr",
            "kap_titel",
            "seg_nr",
            "word_count",
            "text",
        } - set(seg.keys())
        if missing:
            raise ValueError(
                f"Segment {idx} fehlt folgende Pflichtfelder: {sorted(missing)}"
            )

        if not isinstance(seg["id"], str):
            raise TypeError(f"Segment {idx}: id muss ein String sein.")
        if not isinstance(seg["kap_nr"], int):
            raise TypeError(f"Segment {idx}: kap_nr muss ein Integer sein.")
        if not isinstance(seg["kap_titel"], str):
            raise TypeError(f"Segment {idx}: kap_titel muss ein String sein.")
        if not isinstance(seg["seg_nr"], int):
            raise TypeError(f"Segment {idx}: seg_nr muss ein Integer sein.")
        if not isinstance(seg["word_count"], int):
            raise TypeError(f"Segment {idx}: word_count muss ein Integer sein.")
        if not isinstance(seg["text"], str):
            raise TypeError(f"Segment {idx}: text muss ein String sein.")

        if seg["kap_nr"] != int(kap_nr):
            raise ValueError(
                f"Segment {idx}: kap_nr {seg['kap_nr']} passt nicht zu {kap_nr}."
            )
        if seg["kap_titel"].strip() != kap_titel.strip():
            raise ValueError(
                "kap_titel des Segments stimmt nicht mit der Eingabe überein."
            )
        seg_nr = seg["seg_nr"]
        if seg_nr != idx:
            LOGGER.warning(
                "Segmentnummer %s weicht von erwarteter Position %s ab.", seg_nr, idx
            )
        if not id_matches(kap_nr, seg["id"], seg_nr):
            raise ValueError(
                f"Segment {idx}: id {seg['id']} entspricht nicht dem Muster KNNN-SMMM."
            )

        for key in ("char_start", "char_end"):
            if key in seg and not isinstance(seg[key], int):
                raise TypeError(f"Segment {idx}: {key} muss ein Integer sein, falls vorhanden.")


def segment_chapter(
    kap_nr: int,
    kap_titel: str,
    input_path: Path,
    output_path: Path,
) -> List[Dict[str, Any]]:
    text = input_path.read_text(encoding="utf-8")
    prompt = build_prompt(kap_nr, kap_titel, text)
    LOGGER.info("Starte Segmentierung mit Modell %s", settings.MODEL_SEGMENTATION)
    raw_response = call_model(prompt)
    segments = parse_segments(raw_response)
    schema_check(segments, kap_nr, kap_titel)
    ensure_directories([output_path.parent])
    save_segments(output_path, segments)
    LOGGER.info("Segmentierung gespeichert unter %s", output_path)
    return segments


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Segmentiert ein Kapitel.")
    parser.add_argument("--kap-nr", type=int, required=True, help="Kapitelnummer")
    parser.add_argument("--kap-titel", type=str, required=True, help="Kapiteltitel")
    parser.add_argument("--input", type=Path, required=True, help="Pfad zur TXT-Datei")
    parser.add_argument(
        "--output",
        type=Path,
        required=False,
        help="Pfad zur Draft-JSON-Datei",
    )
    return parser.parse_args()


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
    args = parse_args()

    output_path = args.output
    if output_path is None:
        output_path = default_segment_path(
            args.kap_nr, args.kap_titel, Path(settings.PATH_SEGMENTE)
        )

    try:
        segment_chapter(args.kap_nr, args.kap_titel, args.input, output_path)
    except Exception as exc:  # pragma: no cover - CLI safeguard
        LOGGER.error("Segmentierung fehlgeschlagen: %s", exc)
        sys.exit(1)


if __name__ == "__main__":
    main()
