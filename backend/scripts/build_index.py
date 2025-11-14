import os
import json
import pickle
import numpy as np
from pathlib import Path

from dotenv import load_dotenv
from openai import OpenAI

from backend.config.settings import INDEX_PATH as CONFIG_INDEX_PATH, MODEL_NAME

# --- .env aus Projektwurzel laden ---
ROOT_DIR = Path(__file__).resolve().parents[2]
ENV_PATH = ROOT_DIR / ".env"
load_dotenv(dotenv_path=ENV_PATH)

API_KEY = os.getenv("OPENAI_API_KEY")
if not API_KEY:
    raise RuntimeError(f"OPENAI_API_KEY nicht gefunden. Erwartet in: {ENV_PATH}")
print(f"🔑 OPENAI_API_KEY geladen (Länge {len(API_KEY)}).")

client = OpenAI(api_key=API_KEY)

DATA_DIR = ROOT_DIR / "backend" / "data" / "segmente"
INDEX_FILE = ROOT_DIR / CONFIG_INDEX_PATH

def embed_text(text: str) -> np.ndarray:
    resp = client.embeddings.create(model=MODEL_NAME, input=text)
    return np.array(resp.data[0].embedding, dtype="float32")

def preview(path: Path) -> str:
    raw = path.read_bytes()
    head = raw[:200].decode("utf-8", errors="replace")
    return head.replace("\n", "\\n")

def load_segments_from_file(fp: Path):
    txt = fp.read_text(encoding="utf-8", errors="replace")
    txt = txt.lstrip("\ufeff").strip()  # BOM entfernen + trim
    segs = []
    if not txt:
        return segs
    if txt.startswith("["):
        # JSON-Liste
        data = json.loads(txt)
        if not isinstance(data, list):
            raise RuntimeError(f"{fp.name}: JSON beginnt mit '[' ist aber keine Liste.")
        return data
    # JSONL: eine Zeile = ein Objekt
    for i, line in enumerate(txt.splitlines(), start=1):
        s = line.strip()
        if not s:
            continue
        try:
            segs.append(json.loads(s))
        except json.JSONDecodeError as e:
            raise RuntimeError(f"{fp.name}: JSONL-Fehler in Zeile {i}: {e}\nZeile: {s[:120]}")
    return segs

def build_index():
    files = sorted(list(DATA_DIR.glob("*.jsonl")) + list(DATA_DIR.glob("*.json")))
    print(f"📂 Segment-Dateien gefunden: {len(files)} in {DATA_DIR}")
    if not files:
        print("⚠️ Keine .jsonl/.json Dateien gefunden.")
        return

    index = []
    for f in files:
        size = f.stat().st_size
        print(f"➡️  Lese: {f.name}  (Bytes: {size})")
        print(f"   🔎 Vorschau: {preview(f)[:160]}{'…' if size>200 else ''}")
        segs = load_segments_from_file(f)
        print(f"   • Segmente in Datei: {len(segs)}")
        for seg in segs:
            emb = embed_text(seg["text"])
            index.append({
                "id": seg["id"],
                "kap_nr": seg["kap_nr"],
                "kap_titel": seg["kap_titel"],
                "seg_nr": seg["seg_nr"],
                "text": seg["text"],
                "embedding": emb
            })
            print(f"   ✅ eingebettet: {seg['id']}")

    with INDEX_FILE.open("wb") as out:
        pickle.dump(index, out)
    print(f"💾 Index gespeichert: {INDEX_FILE} (Segmente: {len(index)})")

if __name__ == "__main__":
    print(f"🚀 Starte Index-Bau … (ROOT={ROOT_DIR})")
    build_index()
    print("✨ Fertig.")
