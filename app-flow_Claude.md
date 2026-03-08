# App Flow — student PRO PDF Retrieval Engine

**Version:** 1.0 | **Created:** 2026-03-04 | **Owner:** Jan

---

## 1. User & Context

**Single user: Philipp Nitsche**
Uses the tool in isolated sessions. Each session targets one topic at a time. No concurrent users, no authentication.

**Typical session pattern:**
1. One-time setup: upload all books for a subject (done once per subject)
2. Daily work: query topics one by one → review → export → upload to admin panel

---

## 2. Primary User Journeys

### Journey A — First use (new subject)
```
Open app → Tab 1 (Bücher verwalten) → Upload 3–6 books for subject
→ Wait for indexing to complete → Tab 2 (Thema abfragen) → First query
```

### Journey B — Daily content production
```
Open app → Tab 2 → Select topic → Run query → Review Top-10
→ Tab 3 → Rate chunks → Tab 2/4 → Generate summary → Edit → Export
```

### Journey C — Quality check session
```
Open app → Tab 3 → Select previously queried topic → Rate all 10 chunks
→ Review precision score → If < 8/10: note topic for developer follow-up
```

---

## 3. Screen-by-Screen Flow

---

### Screen 1 — Tab 1: Bücher verwalten (Book Management)

**Entry:** App launch (default tab)

**State: No books indexed**
```
[Empty state]
"Noch keine Bücher indexiert. Laden Sie das erste Buch hoch."
[PDF hochladen ↓]
```

**State: Upload form visible**
```
Inputs:
  - File uploader (PDF, max 200 MB)
  - Text input: Buchtitel (required)
  - Select: Fach (Deutsch / Biologie / Sozialwissenschaften) (required)

Button: [Buch verarbeiten]
```

**State: Processing**
```
Spinner: "Hochladen zu Mistral OCR..."
Spinner: "OCR läuft... (kann 1–2 Minuten dauern)"
Info: "OCR abgeschlossen — 498 Seiten erkannt."
Progress bar: "Seite 47 von 498 wird verarbeitet..."
```

**State: Done**
```
Success: "Verarbeitung abgeschlossen — 498 Seiten in 1.204 Chunks indexiert."
Form resets to empty.
```

**State: Books listed**
```
Table: Buch | Fach | Seiten | Chunks | Hochgeladen am
[Delete button per row — shows confirmation dialog]
```

**Transitions:**
- Upload complete → stay on Tab 1, show success + updated table
- Click Tab 2 → go to query screen

---

### Screen 2 — Tab 2: Thema abfragen (Topic Query)

**Entry:** User clicks Tab 2

**State: No query yet**
```
Filters:
  - Select: Fach (Deutsch / Biologie / Sozialwissenschaften)
  - Select: Thema (filtered by Fach, grouped by Jahrgangsstufe)
    e.g. "Lyrik – Oberstufe", "Epik – Klasse 10"

Button: [Relevante Inhalte abrufen]
```

**State: Loading**
```
Spinner: "Suchanfrage wird erweitert..."
Spinner: "Semantische Suche läuft..."
Spinner: "Ergebnisse werden sortiert..."
```

**State: Results displayed**
```
Header: "Top-10 Treffer für: Lyrik – Oberstufe"

For each of 10 results:
  ┌────────────────────────────────────────────────┐
  │ #1  Deutschbuch Klasse 10 — Seite 47  [97%]   │
  │ ▼ (expandable)                                  │
  │   "Das Sonett ist eine lyrische Gedichtform..." │
  └────────────────────────────────────────────────┘

Button: [Zusammenfassung erstellen]
```

**State: Summary generated**
```
Section: "Zusammenfassung"
[Editable text area with LLM-generated German summary]

Note: "Generiert aus 10 Quellseiten. Letzte Aktualisierung: 04.03.2026 14:32"
```

**Transitions:**
- "Relevante Inhalte abrufen" → loading → results
- "Zusammenfassung erstellen" → loading → summary below results
- Tab 3 → quality rating screen (pre-loaded with current topic's results)
- Tab 4 → export screen (pre-loaded with current summary)

---

### Screen 3 — Tab 3: Qualität prüfen (Quality Rating)

**Entry:** User clicks Tab 3 (topic carries over from Tab 2 if active)

**State: Topic selected, no ratings yet**
```
Header: "Qualitätsprüfung: Lyrik – Oberstufe"
Subheader: "Bitte bewerten Sie jeden Treffer."

Precision counter: "0 von 10 bewertet"

For each of 10 results:
  ┌────────────────────────────────────────────────┐
  │ #1  Deutschbuch Klasse 10 — Seite 47           │
  │ "Das Sonett ist eine lyrische Gedichtform..."  │
  │ [✓ Relevant]  [✗ Nicht relevant]               │
  └────────────────────────────────────────────────┘
```

**State: Partially rated**
```
Precision counter: "6 von 10 bewertet — noch 4 ausstehend"
Rated chunks show their label (green ✓ or red ✗)
```

**State: All rated — threshold met**
```
Success badge: "8 von 10 relevant ✓  (80% — Abnahmekriterium erfüllt)"
```

**State: All rated — threshold NOT met**
```
Warning badge: "5 von 10 relevant ⚠️  (50% — Abnahmekriterium nicht erreicht)"
Caption: "Bitte kontaktieren Sie Jan für eine Anpassung."
```

**Transitions:**
- Rating a chunk → updates precision counter live (no page reload)
- All 10 rated + threshold met → green banner
- All 10 rated + threshold not met → orange banner with developer note

---

### Screen 4 — Tab 4: Exportieren (Export)

**Entry:** User clicks Tab 4

**State: Summary available**
```
Header: "Export: Lyrik – Oberstufe"

Label: "Zusammenfassung (bearbeitbar vor Export):"
[Text area — pre-filled with generated summary, editable]

Section: "Quellen (10 Seiten)"
Compact list: Deutschbuch Kl. 10 — S. 47, S. 88, S. 112 | Lesebuch — S. 203, S. 218

[📄 Als JSON exportieren ↓]   [📊 Als CSV exportieren ↓]
```

**State: No summary yet**
```
Info: "Für dieses Thema wurde noch keine Zusammenfassung erstellt."
Button: [Zur Abfrage → Tab 2]
```

**State: Export complete**
```
Success: "Datei wurde heruntergeladen: lyrik_oberstufe_2026-03-04.json"
```

---

## 4. Navigation Map

```
                    ┌─────────────────┐
                    │  App launches   │
                    └────────┬────────┘
                             │
                    ┌────────▼────────┐
              ┌────►│   Tab 1         │◄────┐
              │     │ Bücher verwalten│     │
              │     └─────────────────┘     │
              │                             │
              │     ┌─────────────────┐     │
              ├────►│   Tab 2         │─────┤
              │     │ Thema abfragen  │     │
              │     └────────┬────────┘     │
              │              │ results      │
              │     ┌────────▼────────┐     │
              ├────►│   Tab 3         │─────┤
              │     │ Qualität prüfen │     │
              │     └────────┬────────┘     │
              │              │ rated        │
              │     ┌────────▼────────┐     │
              └────►│   Tab 4         │─────┘
                    │ Exportieren     │
                    └─────────────────┘
```

State flows left-to-right in normal use, but tabs can be accessed in any order.

---

## 5. State Management

Streamlit `st.session_state` holds:

```python
st.session_state = {
    "current_topic_id": str | None,       # selected topic UUID
    "current_topic_name": str | None,     # display name
    "current_results": list[dict] | None, # top-10 chunks from last query
    "current_summary": str | None,        # LLM-generated summary
    "ratings": dict[str, bool],           # chunk_id → relevant (True/False)
    "last_exported_topic": str | None,    # for success messages
}
```

Session state resets on page refresh. No persistent client-side state needed (all data lives in Supabase).

---

## 6. Edge Cases & Error States

### Upload errors

| Situation | UI Response |
|---|---|
| PDF is password-protected / DRM | `st.error("Diese PDF-Datei ist geschützt und kann nicht verarbeitet werden.")` |
| PDF > 200 MB | `st.error("Datei zu groß. Maximale Dateigröße: 200 MB.")` (client-side, before upload) |
| Mistral OCR API failure | `st.error("OCR-Verarbeitung fehlgeschlagen. Bitte erneut versuchen.")` + retry button |
| OCR returns 0 pages | `st.warning("Keine lesbaren Seiten gefunden. Möglicherweise handelt es sich um eine gescannte PDF ohne OCR-Layer.")` |
| Supabase write failure | `st.error("Datenbankfehler beim Speichern. Bitte Jan kontaktieren.")` |

### Query errors

| Situation | UI Response |
|---|---|
| No books indexed | `st.warning("Noch keine Bücher indexiert. Bitte zuerst ein Buch hochladen.")` |
| Query returns 0 results | `st.warning("Keine Treffer gefunden. Das Thema wurde möglicherweise noch nicht behandelt.")` |
| Query returns < 10 results | Show what was found + `st.info("Nur X Treffer gefunden.")` |
| Mistral API rate limit | `st.error("API-Limit erreicht. Bitte 30 Sekunden warten und erneut versuchen.")` |
| Network timeout | `st.error("Zeitüberschreitung. Bitte Internetverbindung prüfen und erneut versuchen.")` |

### Export errors

| Situation | UI Response |
|---|---|
| No summary generated | Redirect to Tab 2 with info message |
| Export file generation fails | `st.error("Export fehlgeschlagen. Bitte erneut versuchen.")` |

---

## 7. Happy Path (End-to-End)

```
1. Philipp opens app → Tab 1 visible

2. He drags Deutschbuch_Klasse10.pdf into uploader
   → enters "Deutschbuch Klasse 10" as title
   → selects "Deutsch" as subject
   → clicks "Buch verarbeiten"

3. Progress bar runs for ~2 minutes (498 pages)
   → "Verarbeitung abgeschlossen — 498 Seiten in 1.204 Chunks indexiert."

4. He clicks Tab 2
   → selects "Deutsch" → selects "Lyrik – Oberstufe"
   → clicks "Relevante Inhalte abrufen"

5. 10 results appear in ~8 seconds (query expansion + hybrid search)
   → He skims each excerpt, looks correct

6. He clicks "Zusammenfassung erstellen"
   → Summary appears in ~10 seconds, cites pages

7. He clicks Tab 3
   → Rates all 10 chunks → sees "8 von 10 relevant ✓"

8. He clicks Tab 4
   → Reviews summary, makes one small edit
   → Clicks "Als JSON exportieren"
   → File downloads: lyrik_oberstufe_2026-03-04.json

9. He uploads JSON to student PRO admin panel
   → Content live for teachers
```

Total time per topic (after books indexed): **~3–5 minutes**
