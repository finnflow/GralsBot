"""Hilfswerkzeug zum Konvertieren von Segment-JSON nach JSONL."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Iterable, List, Optional

from backend.scripts.utils import project_root

DEFAULT_DIRECTORY = project_root() / "backend" / "data" / "segmente"


def convert_file(input_path: Path, output_path: Optional[Path] = None) -> Path:
    """Convert a single JSON file containing a list of objects to JSONL."""

    input_path = input_path.resolve()
    if output_path is None:
        output_path = input_path.with_suffix(".jsonl")
    else:
        output_path = output_path.resolve()

    with input_path.open("r", encoding="utf-8") as f:
        data = json.load(f)
    if not isinstance(data, list):
        raise ValueError(f"Erwartet wurde eine Liste von Objekten in {input_path}.")

    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", encoding="utf-8") as out:
        for obj in data:
            out.write(json.dumps(obj, ensure_ascii=False) + "\n")

    print(f"✅ konvertiert: {input_path.name} -> {output_path.name}")
    return output_path


def convert_many(files: Iterable[Path], output_dir: Optional[Path] = None) -> List[Path]:
    outputs: List[Path] = []
    for file in files:
        if output_dir is not None:
            output_dir.mkdir(parents=True, exist_ok=True)
            out_path = output_dir / file.with_suffix(".jsonl").name
        else:
            out_path = None
        outputs.append(convert_file(file, out_path))
    return outputs


def convert_directory(directory: Path, output_dir: Optional[Path] = None) -> List[Path]:
    directory = directory.resolve()
    files = sorted(directory.glob("*.json"))
    if not files:
        raise FileNotFoundError(f"Keine JSON-Dateien in {directory} gefunden.")
    return convert_many(files, output_dir)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Konvertiert Segment-JSON nach JSONL.")
    parser.add_argument(
        "paths",
        nargs="*",
        type=Path,
        help="Optionale Liste von JSON-Dateien. Wenn leer, wird das Standardverzeichnis genutzt.",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        required=False,
        help="Optionales Zielverzeichnis für die JSONL-Dateien.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    output_dir = args.output_dir.resolve() if args.output_dir else None

    if args.paths:
        convert_many(args.paths, output_dir)
        return

    target_dir = None if output_dir is None or output_dir == DEFAULT_DIRECTORY else output_dir
    convert_directory(DEFAULT_DIRECTORY, target_dir)


if __name__ == "__main__":
    main()
