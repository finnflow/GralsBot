import os
import sys
import json
import pickle
from pathlib import Path
from typing import List, Dict

import numpy as np
from dotenv import load_dotenv
from openai import OpenAI

from backend.config.settings import MODEL_NAME, INDEX_PATH as CONFIG_INDEX_PATH

# ==== Einstellungen ============================================================
PROJECT_ROOT = Path(__file__).resolve().parents[2]
EMBEDDING_MODEL = MODEL_NAME  # muss zu deinem Index & query_index.py passen!
INDEX_PATH = PROJECT_ROOT / CONFIG_INDEX_PATH
REQUIRED_FIELDS = {"id", "kap_nr", "kap_titel", "seg_nr", "word_count", "text"}
BATCH_SIZE = 64  # Embeddings in Batches schicken (sparsam & stabil)

# ==== Setup ===================================================================
load_dotenv()
API_KEY = os.getenv("OPENAI_API_KEY")
if not API_KEY:
    raise RuntimeError("OPENAI_API_KEY nicht gefunden. Bitte in .env setzen.")
client = OpenAI(api_key=API_KEY)

# ==== Helpers =================================================================
def load_index(path) -> List[Dict]:
    path = Path(path)
    if path.exists():
        with open(path, "rb") as f:
            return pickle.load(f)
    return []

def save_index(index: List[Dict], path):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "wb") as f:
        pickle.dump(index, f)

def read_jsonl(file_path: str) -> List[Dict]:
    """Liest JSONL: 1 Zeile = 1 JSON-Objekt. Leere Zeilen werden übersprungen."""
    segs = []
    with open(file_path, "r", encoding="utf-8-sig") as f:  # -sig: entfernt evtl. BOM
        for ln, line in enumerate(f, start=1):
            line = line.strip()
            if not line:
                continue
            try:
                obj = json.loads(line)
            except json.JSONDecodeError as e:
                raise ValueError(f"JSON-Fehler in Zeile {ln}: {e}")
            missing = REQUIRED_FIELDS - set(obj.keys())
            if missing:
                raise ValueError(f"Fehlende Felder in Zeile {ln}: {sorted(missing)}")
            segs.append(obj)
    if not segs:
        raise ValueError("Die JSONL-Datei enthält keine Segmente.")
    # einfache Konsistenz-Prüfungen
    kap_nrs = {int(s["kap_nr"]) for s in segs}
    if len(kap_nrs) != 1:
        raise ValueError(f"Uneinheitliche kap_nr in der Datei: {sorted(kap_nrs)}")
    titles = {s["kap_titel"] for s in segs}
    if len(titles) != 1:
        raise ValueError(f"Uneinheitliche kap_titel in der Datei: {sorted(titles)}")
    # fortlaufende seg_nr?
    seg_nums = sorted(int(s["seg_nr"]) for s in segs)
    expected = list(range(1, len(segs) + 1))
    if seg_nums != expected:
        raise ValueError(f"seg_nr nicht fortlaufend ab 1: gefunden {seg_nums}, erwartet {expected}")
    return segs

def embed_batch(texts: List[str]) -> List[List[float]]:
    resp = client.embeddings.create(model=EMBEDDING_MODEL, input=texts)
    return [d.embedding for d in resp.data]

def cosine_dim(vec: List[float]) -> int:
    return len(vec)

# ==== Main ====================================================================
def add_chapter(chapter_path: str, index_path: str = INDEX_PATH):
    # 1) Vorhandenen Index laden
    index = load_index(index_path)
    current_count = len(index)
    expected_dim = None
    if index:
        # Nimm die Dimension aus dem ersten Eintrag als „Single Source of Truth“
        expected_dim = len(index[0]["embedding"])

    # 2) Neue Segmente lesen & Basisprüfungen
    new_segs = read_jsonl(chapter_path)

    # 3) Deduplizieren nach id (falls versehentlich erneut hinzugefügt)
    existing_ids = {seg["id"] for seg in index}
    filtered = [s for s in new_segs if s["id"] not in existing_ids]
    skipped = len(new_segs) - len(filtered)
    if skipped:
        print(f"⚠️  {skipped} Segment(e) übersprungen (ID bereits im Index vorhanden).")

    if not filtered:
        print("ℹ️  Keine neuen Segmente zum Hinzufügen (alles waren Duplikate).")
        print(f"📚 Index bleibt bei {len(index)} Segmenten.")
        return

    # 4) Embeddings in Batches erzeugen
    texts = [s["text"] for s in filtered]
    embeddings: List[List[float]] = []
    for i in range(0, len(texts), BATCH_SIZE):
        batch = texts[i : i + BATCH_SIZE]
        vecs = embed_batch(batch)
        embeddings.extend(vecs)

    # 5) Dimensions-Wächter
    new_dim = cosine_dim(embeddings[0])
    if expected_dim is not None and new_dim != expected_dim:
        raise RuntimeError(
            f"Embedding-Dimension ungleich Index: Index={expected_dim}, neu={new_dim}. "
            f"Bitte überall dasselbe Modell verwenden (aktuell: {EMBEDDING_MODEL})."
        )

    # 6) Embeddings anreichern & in den Index hängen
    for seg, vec in zip(filtered, embeddings):
        seg["embedding"] = vec
        index.append(seg)

    # 7) Speichern
    save_index(index, index_path)

    # 8) Ausgabe
    added = len(filtered)
    total = len(index)
    kap_nr = filtered[0]["kap_nr"]
    kap_titel = filtered[0]["kap_titel"]
    print(f"✅ Kapitel {kap_nr} „{kap_titel}“: {added} neue Segmente hinzugefügt.")
    if skipped:
        print(f"↩️  {skipped} Duplikat(e) wurden nicht erneut hinzugefügt.")
    print(f"📚 Index hat jetzt {total} Segmente insgesamt.")
    print(f"🔢 Embedding-Modell: {EMBEDDING_MODEL} | Vektor-Dimension: {new_dim}")

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("❌ Bitte eine Kapiteldatei (JSONL) angeben.\n"
              "   Beispiel:\n"
              "   python backend/scripts/add_chapter.py backend/data/segmente/K004_Das_Leben.jsonl")
        sys.exit(1)
    add_chapter(sys.argv[1])
