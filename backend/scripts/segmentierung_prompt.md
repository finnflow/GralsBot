Ziel: Den folgenden Kapiteltext in **sinntragende Segmente** aufteilen – vollständig, unverändert, ohne Seitenzahlen. Gib **nur** eine JSON-Liste aus.

VERBINDLICHE REGELN (Iteration 1)
1) Vollständigkeit & Unverändertheit:
   - Gib den **gesamten Inputtext** vollständig und unverändert wieder, nur in Segmente aufgeteilt.
   - Keine Auslassungen, keine Umformulierungen, keine Korrekturen, keine hinzugefügten Zeichen.
   - Segmentgrenzen **nur** an Satzgrenzen.

2) Größe & Kohärenz:
   - Zielbereich: **150–400 Wörter** pro Segment (angestrebt 180–350).
   - Erlaubte Ausnahmen:
     a) **<120 Wörter** nur, wenn es ein **kurzer, prägnanter Absatz** ist, der **mindestens 2 vollständige Sätze** enthält und **in sich verständlich** ist.
     b) **bis ~550 Wörter**, wenn ein stark zusammenhängender Gedankengang sonst spürbar leiden würde.
   - **Strikt verboten:** **Einzelsatz-Segmente**.

3) Reihenfolge & Lücken:
   - Die Segmente müssen aneinandergefügt wieder exakt den Originaltext ergeben (keine Lücken, keine Überschneidungen).
   - Reihenfolge beibehalten.

4) IDs:
   - `"id"` im Format `K{kap_nr:03d}-S{seg_nr:03d}` (z. B. `K033-S009`).
   - `"kap_nr"` (Zahl), `"kap_titel"` (String), `"seg_nr"` (Zahl).
   - `"word_count"` bitte mitliefern.

AUSGABEFORMAT (nur JSON-Liste, keine Kommentare):
[
  {
    "id": "K001-S001",
    "kap_nr": 1,
    "kap_titel": "<TITEL>",
    "seg_nr": 1,
    "word_count": 0,
    "text": "…exakter Originaltext…"
  }
]

Jetzt segmentiere bitte den folgenden Text.
Parameter: kap_nr=<ZAHL>, kap_titel="<TITEL>"
TEXT:
<<<
[HIER DEN KOMPLETTEN KAPITELTEXT UNVERÄNDERT EINFÜGEN]
>>>
