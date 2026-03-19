# Architektur-Diskussion: RAG vs. Long-Context (Rachids Vorschlag)

**Erstellt:** 2026-03-19 | **Kontext:** Gespräch mit Rachid über alternative Architektur

---

## Was ist RAG?

RAG = Retrieval-Augmented Generation. Grundprinzip: statt dem LLM alles zu geben, suchst du erst die relevanten Teile heraus und gibst dem LLM nur diese.

```
Frage → relevante Stücke finden → LLM bekommt nur die relevanten Stücke → Antwort
```

### RAG in diesem System (konkret)

```
"Lyrische Texte"
  → Steckbrief berechnen (Embedding via mistral-embed)
  → top 20 Abschnitte aus 2126 Chunks finden (pgvector cosine similarity)
  → diese 20 Abschnitte an Mistral Large
  → Zusammenfassung
```

Mistral Large bekommt ~20 × 1500 Zeichen = ~30.000 Zeichen statt das ganze Buch.

---

## Rachids Gegenvorschlag: Kein RAG

Kein Retrieval. Kein Steckbrief. Kein pgvector.

```
"Lyrische Texte"
  → ganzes Buch (315 Seiten) direkt an Gemini 2.5 Pro
  → Zusammenfassung
```

Gemini 2.5 Pro hat 1M Token Context Window — die Bücher passen komplett rein. Das LLM entscheidet selbst was relevant ist, ohne vorherigen Filterungsschritt.

Genannte Modelle via OpenRouter: **Gemini 2.5 Pro**, **Claude Opus 4.6**

---

## Vergleich

| | RAG (heute) | Rachids Vorschlag |
|---|---|---|
| Wer wählt relevante Stellen? | Vektordatenbank (mathematisch) | Das LLM selbst |
| Wie viel Text sieht das LLM? | ~30K Zeichen (gefiltert) | ~500K Zeichen (alles) |
| Komplexität | Hoch (Embeddings, pgvector, Chunks) | Niedrig (OCR → LLM, fertig) |
| Kosten pro Abfrage | ~€0,05 | ~€0,35 (ohne Caching) |
| Kosten mit Caching | €0 (Summary Cache) | Günstiger via Gemini Context Cache |
| DSGVO | ✅ Mistral EU-Hosting | ⚠️ Gemini/Anthropic US-Hosting |
| "Lost in the middle" Risiko | Gering (nur relevante Chunks) | Bekanntes Qualitätsproblem bei langen Kontexten |
| Setup-Aufwand | Bereits gebaut | Würde pgvector + Embeddings ersetzen |

---

## Offene Fragen

1. **DSGVO**: Mistral wurde explizit wegen EU-Hosting gewählt. Gemini (Google) und Opus (Anthropic) laufen über US-Server. Ist das mit Philipp und den Verlagslizenzen kompatibel?

2. **Caching-Strategie**: Gemini bietet Context Caching — Buch einmal hochladen, Cache-Key behalten, Folgeabfragen günstiger. Wie verhält sich das Kostenmodell gegen den bestehenden Summary Cache?

3. **Qualität**: Würde Rachid einen A/B-Test vorschlagen — dieselben 5 Testthemen mit beiden Ansätzen und Qualitätsvergleich?

4. **Scope**: Kompletter Ersatz von RAG oder hybride Lösung (Long-Context als Fallback wenn RAG-Qualität unter Schwellenwert)?

---

## Status

Vorschlag von Rachid — noch keine Entscheidung getroffen. Aktuelles System läuft auf RAG-Basis.
