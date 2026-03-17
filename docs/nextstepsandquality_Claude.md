# Next Steps & Aktueller Stand — student PRO PDF Engine

**Aktualisiert:** 2026-03-17 | **Owner:** Jan

---

## Aktueller Stand (bereit für Präsentation)

### Was live ist ✅

| Bereich | Status |
|---|---|
| 2 Bücher indexiert (Klett 109 S. + Paul D 315 S., 2126 Chunks) | ✅ |
| Lehrplan-Extraktion (Deutsch + Mathe, EF/GK/LK automatisch erkannt) | ✅ |
| 93 Themen in der Datenbank | ✅ |
| Thema abfragen → Top-10 Buchseiten + Zusammenfassung | ✅ |
| Caching — wiederholte Abfragen kosten €0 | ✅ |
| Beispieldokumente als Stilvorlage (RAG on Examples) | ✅ |
| Cost Tracking — Kosten pro Buch in `processing_log` | ✅ |
| UX — aufklappbare Ergebnisse, Kostenübersicht, Erklärungen | ✅ |
| Deployment — auto-deploy auf studentpro.streamlit.app | ✅ |

### Was fehlt ❌

| Was | Warum wichtig | Aufwand |
|---|---|---|
| **Export** — Zusammenfassung als Datei herunterladen | Vertraglich vereinbart. Ohne Export geht kein Inhalt in Philipps Lehrer-App. | ~2h |
| **Akzeptanztest** — Philipp bewertet Top-10 für 5 Themen | Abnahmekriterium: ≥ 8/10 relevant. Kann erst nach Export sinnvoll stattfinden. | Philipp |

---

## Was als nächstes gebaut wird

---

### 🔴 1. Export — Zusammenfassung herunterladen

**Was:** Ein Button der die Zusammenfassung + Quellseiten als Datei speichert — in dem Format das Philipps Admin-Panel erwartet.

**Warum #1:**
Ohne Export ist das System wie ein Drucker ohne Papier. Die Zusammenfassung ist da, aber sie kommt nie bei den Lehrern an. Das ist der einzige fehlende Baustein zwischen dem was heute live ist und einem funktionierenden Produkt.

**Optionen:**
- **Markdown (.md)** — einfachste Option, sofort lesbar, in jede App importierbar
- **JSON** — strukturiert, maschinenlesbar, ideal wenn Philipps Admin-Panel eine API hat
- **DOCX** — direkt bearbeitbar in Word, für Philipp am vertrautesten

Empfehlung: zuerst Markdown oder DOCX, JSON wenn die Admin-Panel-Integration klar ist.

**Aufwand:** ~2 Stunden.

---

### 🔴 2. Akzeptanztest mit Philipp

**Was:** Philipp wählt 5 Themen, schaut die Top-10 Buchseiten an und bewertet jede mit ✓ (relevant) oder ✗ (nicht relevant). Ziel: mindestens 8 von 10 pro Thema.

**Warum #2:**
Das ist die vertraglich vereinbarte Abnahme. Außerdem zeigt uns der Test genau wo das System schwächelt — welche Themen schlechte Treffer liefern, welche Bücher fehlen.

**Geblockt durch:** Philipp muss sich Zeit nehmen. Export (#1) sollte zuerst fertig sein damit er den vollen Workflow sieht.

---

### 🟡 3. Zwei-Schritt-Abfrage (Phase 1 und Phase 2 trennen)

**Was:** Heute löst ein einziger Button beide Schritte aus — Buchseiten suchen UND Zusammenfassung schreiben. Das trennen:
- Button 1: `[Buchseiten abrufen]` → zeigt die Quellseiten, noch kein Mistral-Large-Aufruf
- Button 2: `[Zusammenfassung erstellen]` → erst dann wird die KI beauftragt

**Warum:** Philipp kann die sachliche Wiedergabe (Quellseiten) prüfen bevor er entscheidet ob er eine Zusammenfassung will. Macht den Prozess transparenter und gibt ihm mehr Kontrolle. Spart auch Kosten wenn er die Quellseiten als ausreichend empfindet.

**Aufwand:** ~2 Stunden.

---

### 🟡 4. Mehr Bücher

**Was:** Cornelsen, Westermann, Mathe-Bücher indexieren.

**Geblockt durch:** Philipp liefert die PDFs.

---

### 🟢 5. Hybrid Search (Keyword + Semantic)

**Was:** Heute nur semantische Suche (Steckbrief-Vergleich). Zusätzlich Volltextsuche (BM25) einbauen und beide kombinieren.

**Warum:** Findet auch Seiten die exakt den Fachbegriff enthalten aber semantisch weniger ähnlich sind. Besonders wichtig für Mathe. Kostet keine zusätzlichen Mistral-Credits.

**Aufwand:** ~2 Stunden.

---

### 🟢 6. Query Expansion (Synonyme)

**Was:** Vor der Suche fragt das System Mistral: „Was sind verwandte Begriffe zu diesem Thema?" und sucht dann nach allen gleichzeitig.

**Beispiel:** „Lyrische Texte" → sucht auch nach „Gedicht, Lyrik, Strophe, poetische Texte"

**Aufwand:** ~1 Stunde.

---

### 🟢 7. Modelle vergleichen

**Was:** Dieselbe Abfrage mit verschiedenen Modellen laufen lassen (z.B. Mistral Large vs. Mistral Small) und Ergebnisse nebeneinander zeigen.

**Warum:** Gibt Philipp ein Gefühl für den Qualitätsunterschied und den Kostenvorteil kleinerer Modelle.

**Aufwand:** ~2 Stunden.

---

## Für Rachid (Code Review)

Der gesamte Code läuft in einer einzigen Datei: `app_Claude.py`.

| Thema | Details |
|---|---|
| Stack | Streamlit + Mistral API + Supabase (pgvector) |
| Retrieval | cosine similarity via `match_documents` RPC, subject + filename filter |
| Chunking | 1500 Zeichen, 200 Overlap, `chunk_text()` in app_Claude.py |
| Embedding | `mistral-embed`, 1024 Dimensionen, pro Seite alle Chunks in einem Batch |
| Caching | `summary_cache` Tabelle — topic als unique key, hits-Counter |
| Prompts | editierbar in der App, gespeichert in `settings` Tabelle |
| Kosten-Tracking | `processing_log` Tabelle — OCR + Embed geloggt, Zusammenfassung noch nicht |

Offene technische Punkte für Review:
- Ist ein einziges `app_Claude.py` für diesen Umfang noch vertretbar oder Zeit für Splitting?
- Chunking-Parameter (1500 Zeichen) — Einschätzung ob das für Schulbuch-PDFs optimal ist
- Fehlerbehandlung bei Mistral API Timeouts — heute nur `st.error()` ohne Retry

---

## Priorisierung auf einen Blick

| # | Was | Typ | Aufwand | Geblockt |
|---|---|---|---|---|
| 1 | Export (Zusammenfassung herunterladen) | Pflicht | ~2h | — |
| 2 | Akzeptanztest | Pflicht | — | Philipp |
| 3 | Zwei-Schritt-Abfrage | UX | ~2h | — |
| 4 | Mehr Bücher | Inhalt | — | Philipp |
| 5 | Hybrid Search | Qualität | ~2h | — |
| 6 | Query Expansion | Qualität | ~1h | — |
| 7 | Modelle vergleichen | Experiment | ~2h | — |
