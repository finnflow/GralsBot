import json
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
DATA_DIR = PROJECT_ROOT / "backend" / "data" / "segmente"

for file in DATA_DIR.glob("*.json"):
    with open(file, "r", encoding="utf-8") as f:
        data = json.load(f)  # lädt die ganze Liste
    
    out_file = file.with_suffix(".jsonl")
    with open(out_file, "w", encoding="utf-8") as out:
        for obj in data:
            out.write(json.dumps(obj, ensure_ascii=False) + "\n")
    
    print(f"✅ konvertiert: {file.name} -> {out_file.name}")
