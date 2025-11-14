# GralsBot

Dieses Repository enthält den Quellcode und die Datenpipeline für den GralsBot. Der Projektfokus liegt auf der Aufbereitung spiritueller Texte sowie auf einer Embedding-gestützten Suche über segmentierte Kapitel.

## Projektstruktur

```
gralsbot/
  backend/
    api/
      server.py
    config/
      settings.py
    data/
      raw/
      segmente/
      index.pkl
    scripts/
      add_chapter.py
      build_index.py
      convert_to_jsonl.py
      segment_chapter.py
      utils.py
      pruefung_prompt.md
      query_index.py
      segmentierung_prompt.md
  docs/
    projektplan.md
  README.md
  .gitignore
```

## Nutzung

1. Installiere die Abhängigkeiten und setze deinen `OPENAI_API_KEY` in einer `.env`-Datei im Projektstamm.
2. Verwende `backend/scripts/build_index.py`, um einen neuen Embedding-Index aus den Segmentdateien unter `backend/data/segmente/` zu erstellen.
3. Füge mit `backend/scripts/add_chapter.py` weitere Kapitel hinzu.
4. Stelle Fragen an den Index mit `backend/scripts/query_index.py`.

Die Konfiguration für Modellnamen, Nachbarschaftsgröße und Dateipfade wird zentral in `backend/config/settings.py` verwaltet.
