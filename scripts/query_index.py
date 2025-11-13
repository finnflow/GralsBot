import os
import pickle
import numpy as np
from openai import OpenAI
from dotenv import load_dotenv

# 🔑 ENV laden
load_dotenv()
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

INDEX_PATH = os.path.join(os.path.dirname(__file__), "../data/index.pkl")

# Kosinus-Ähnlichkeit
def cosine_similarity(a, b):
    return np.dot(a, b) / (np.linalg.norm(a) * np.linalg.norm(b))

# Index laden
with open(INDEX_PATH, "rb") as f:
    index = pickle.load(f)

print(f"📚 Index geladen mit {len(index)} Segmenten.")

# Nutzerfrage
query = input("❓ Deine Frage: ")

# Embedding für die Frage
query_embedding = client.embeddings.create(
    model="text-embedding-3-large",
    input=query
).data[0].embedding

# Scoring
scored_segments = []
for seg in index:
    score = cosine_similarity(query_embedding, seg["embedding"])
    scored_segments.append((score, seg))

scored_segments.sort(key=lambda x: x[0], reverse=True)
top_segments = [seg for _, seg in scored_segments[:3]]

# Kontexte vorbereiten
context_texts = "\n\n".join([f"{s['kap_titel']} (Abschnitt {s['seg_nr']}):\n{s['text']}" for s in top_segments])

# GPT-5 befragen
prompt = f"""
Du bist ein Assistent, der Fragen basierend auf einem spirituellen Text beantwortet.

Frage des Nutzers:
{query}

Hier sind relevante Textstellen aus der Botschaft:

{context_texts}

Antworte bitte prägnant und klar in deinen eigenen Worten,
aber stütze dich NUR auf die Textstellen.
"""

response = client.chat.completions.create(
    model="gpt-4o-mini",  # falls du GPT-5 im Plus hast, kannst du auch "gpt-4.1" oder "gpt-4o" nutzen
    messages=[{"role": "user", "content": prompt}],
    temperature=0.2,
)

print("\n💡 Antwort:\n")
print(response.choices[0].message.content)

print("\n🔎 Verwendete Segmente:")
for s in top_segments:
    print(f"- {s['id']} | {s['kap_titel']} (Abschnitt {s['seg_nr']})")
