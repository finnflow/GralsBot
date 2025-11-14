"""Orchestriert die Segmentierungs-Pipeline für ein Kapitel."""

from __future__ import annotations

import argparse
import json
import logging
import sys
from pathlib import Path
from typing import Any, Dict

from backend.config import settings
from backend.scripts import utils
from backend.scripts import segment_chapter as segment_module
from backend.scripts import validate_segments as validator_module
from backend.scripts import review_segments as review_module
from backend.scripts import convert_to_jsonl as convert_module
from backend.scripts import add_chapter as add_chapter_module
from backend.scripts.segment_utils import save_segments

LOGGER = logging.getLogger(__name__)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Kapitel vollständig verarbeiten.")
    parser.add_argument("--kap-nr", type=int, required=True, help="Kapitelnummer")
    parser.add_argument("--kap-titel", type=str, required=True, help="Kapiteltitel")
    parser.add_argument("--input", type=Path, required=True, help="Kapiteltext (TXT)")
    parser.add_argument(
        "--non-interactive",
        action="store_true",
        help="Ohne Rückfragen durchführen",
    )
    parser.add_argument(
        "--output",
        type=Path,
        required=False,
        help="Optionaler Pfad für das Draft-JSON",
    )
    return parser.parse_args()



def summarise_findings(report: Dict[str, Any], review: Dict[str, Any]) -> None:
    warnings = report.get("warnings", [])
    findings = review.get("findings", [])
    if warnings:
        print(f"⚠️  {len(warnings)} Validierungswarnung(en) vorhanden.")
    if findings:
        print(f"🔍  {len(findings)} Review-Fund(e) vorhanden.")
    if warnings:
        for item in warnings[:3]:
            seg = item.get("seg_id", "-")
            print(f"   • [{seg}] {item.get('type')}: {item.get('message')}")
    if findings:
        for item in findings[:3]:
            seg = item.get("seg_id", "-")
            print(
                f"   • [{seg}] {item.get('severity', 'medium')}: {item.get('message')}"
            )


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
    args = parse_args()

    segment_dir = Path(settings.PATH_SEGMENTE)
    segment_dir.mkdir(parents=True, exist_ok=True)

    if args.output:
        draft_path = args.output
    else:
        draft_path = utils.default_segment_path(args.kap_nr, args.kap_titel, segment_dir)

    base = utils.chapter_basename(args.kap_nr, args.kap_titel)
    validation_report_path = segment_dir / f"{base}_validation.json"
    review_report_path = segment_dir / f"{base}_review.json"
    final_jsonl_path = segment_dir / f"{base}_final.jsonl"

    LOGGER.info("1/5 Segmentierung starten ...")
    try:
        segment_module.segment_chapter(
            args.kap_nr, args.kap_titel, args.input, draft_path
        )
    except Exception as exc:
        LOGGER.error("Segmentierung fehlgeschlagen: %s", exc)
        sys.exit(1)

    LOGGER.info("2/5 Validierung durchführen ...")
    try:
        report, normalised_segments = validator_module.validate_segments(
            args.kap_nr, args.input, draft_path
        )
    except Exception as exc:
        LOGGER.error("Validierung fehlgeschlagen: %s", exc)
        sys.exit(1)

    validation_report_path.write_text(
        json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    LOGGER.info("Validierungsreport gespeichert unter %s", validation_report_path)

    if report["status"] == "errors":
        LOGGER.error("Validierung meldet Fehler. Pipeline wird abgebrochen.")
        sys.exit(1)

    save_segments(draft_path, normalised_segments)

    LOGGER.info("3/5 Semantischen Review starten ...")
    try:
        review = review_module.review_segments(
            args.kap_nr, args.kap_titel, args.input, draft_path
        )
    except Exception as exc:
        LOGGER.error("Review fehlgeschlagen: %s", exc)
        sys.exit(1)

    review_report_path.write_text(
        json.dumps(review, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    LOGGER.info("Review-Report gespeichert unter %s", review_report_path)

    proceed = True
    if not args.non_interactive and (
        report.get("warnings") or review.get("findings")
    ):
        summarise_findings(report, review)
        answer = input("Segmentierung übernehmen? [y/N] ").strip().lower()
        proceed = answer == "y"
    elif args.non_interactive:
        if report.get("warnings"):
            LOGGER.info("Warnungen vorhanden, werden aber im non-interactive Modus akzeptiert.")
        if review.get("findings"):
            LOGGER.info("Review-Findings vorhanden, werden aber übernommen.")

    if not proceed:
        LOGGER.info("Pipeline wurde vom Benutzer abgebrochen. Dateien bleiben bestehen.")
        return

    LOGGER.info("4/5 Konvertiere Segmente in JSONL ...")
    try:
        convert_module.convert_file(draft_path, final_jsonl_path)
    except Exception as exc:
        LOGGER.error("Konvertierung nach JSONL fehlgeschlagen: %s", exc)
        sys.exit(1)

    LOGGER.info("5/5 Aktualisiere Embedding-Index ...")
    try:
        add_chapter_module.add_chapter(str(final_jsonl_path), str(Path(settings.PATH_INDEX)))
    except Exception as exc:
        LOGGER.error("Import in den Index fehlgeschlagen: %s", exc)
        sys.exit(1)

    LOGGER.info(
        "Kapitel %s »%s« wurde erfolgreich verarbeitet und dem Index hinzugefügt.",
        args.kap_nr,
        args.kap_titel,
    )


if __name__ == "__main__":
    main()
