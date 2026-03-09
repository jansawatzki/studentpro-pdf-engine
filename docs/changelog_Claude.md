# Changelog

All notable changes to this project will be documented in this file.

---

## [2026-03-09] Chunking-Implementierung (Steps 2–6)

### Added
- `reindex_Claude.py` — einmaliges Re-Indexierungs-Skript: liest bestehende Seiten aus DB, splittet in Abschnitte (~1500 Zeichen, 200 Overlap), re-embeddet, upserted mit `chunk_index`
- `chunk_text()` Funktion in `ingest_Claude.py` + `app_Claude.py` — teilt langen Text an Wortgrenzen in überlappende Abschnitte auf

### Changed
- `ingest_Claude.py`: `embed_and_store()` nutzt jetzt `chunk_text()`, speichert mit `chunk_index`, `on_conflict="filename,page_number,chunk_index"`
- `app_Claude.py` Tab 1: Upload-Loop chunked jetzt pro Seite, zeigt "X Abschnitte" im Fortschrittsbalken; Bücherliste zeigt "109 Seiten (847 Abschnitte)"
- `app_Claude.py` Tab 2: Quellseiten zeigen jetzt "Seite 47 (Abschnitt 2)" wenn `chunk_index > 0` — sowohl bei gecachten als auch frischen Ergebnissen
- `docs/nextstepsandquality_Claude.md`: Implementation task list aktualisiert (Steps 2, 6, 7 ✅), Step 1 SQL um 4. Statement erweitert (RPC update für `chunk_index`)

### Pending (user action required)
- Step 1: 4 SQL-Statements in Supabase SQL Editor ausführen
- Step 4: `python3 reindex_Claude.py` starten (nach Step 1)
- Step 5: Verify row count + Test-Query im App

### Files affected
- `reindex_Claude.py` (neu), `ingest_Claude.py`, `app_Claude.py`, `docs/nextstepsandquality_Claude.md`, `docs/changelog_Claude.md`, `docs/tasks_Claude.md`

---

## [2026-03-09] template_strategy_Claude.md + docs/ Aufräumen

### Added
- `docs/template_strategy_Claude.md` — Wiederverwendungsstrategie: Zielgruppen (Recht, Pharma, HR, etc.), was 100% reusable ist, was pro Client angepasst wird (30–60 min), Preismodelle, Sales-Prozess, sofortige Maßnahmen im laufenden Projekt
- `docs/` Unterordner — alle PRD-Markdown-Dateien von Root nach `docs/` verschoben
- `design_Claude.md` v1.1 — Current State Abschnitt mit 5-Tab-Struktur + Farbsignalen

### Files affected
- `docs/template_strategy_Claude.md` (neu), alle `_Claude.md` Docs in `docs/` verschoben

---

## [2026-03-05] Initial Build — Working MVP

### Added
- `Mistral_Claude/app_Claude.py` — Streamlit app with 2 tabs: Upload PDF + Search by keyword
- `Mistral_Claude/config_Claude.env` — environment config with Mistral + Supabase credentials
- `Mistral_Claude/setup_db_Claude.sql` — Supabase schema: `documents` table + `match_documents` RPC function (pgvector)
- `Mistral_Claude/requirements_Claude.txt` — Python dependencies
- `Mistral_Claude/run_Claude.sh` — launch script (handles PATH for macOS system Python)
- `docs/masterplan_Claude.md` — product vision, users, success metrics, architecture decision
- `docs/implementation_Claude.md` — full technical spec: DB schema, module structure, chunking, phased plan, cost estimates
- `docs/design_Claude.md` — UI/UX guide: German language, layout, component patterns, tab structure
- `docs/app-flow_Claude.md` — screen-by-screen flows, state management, edge cases, happy path

### Changed
- Fixed `files.upload()` API call: changed from incorrect tuple format `(name, bytes, mimetype)` to correct dict format `{"file_name": ..., "content": ...}` (mistralai SDK v1.10 requirement)
- Improved error handling: all API calls wrapped in try/except with user-facing messages
- Load `.env` using absolute path relative to script location (fixes working directory issues)
- Added SSL warning suppression for macOS system Python 3.9 + LibreSSL

### Technical notes
- Python: system Python 3.9.6 (macOS)
- mistralai: 1.10.0
- supabase: 2.28.0
- streamlit: 1.50.0
- Packages installed to: `~/Library/Python/3.9/`
- Streamlit binary: `~/Library/Python/3.9/bin/streamlit`

---

## [2026-03-05] DB Setup + First Real Ingestion Test

### Added
- `Mistral_Claude/ingest_Claude.py` — standalone ingestion script: splits PDFs > 50MB into 25-page batches, runs Mistral OCR per batch, embeds (10 pages per API call), upserts into Supabase
- Supabase MCP installed (`~/.claude.json`) with personal access token — full user-mode access for future sessions

### Changed
- DB setup (pgvector extension + `documents` table + `match_documents` RPC) executed via Supabase Management API (no manual SQL Editor needed)

### Results
- Indexed: `Klett._Deutsch kompetent EF.pdf` — 169MB, 109 pages, 5 batches, ~4 min total
- Test query results (top-10 similarity search, 3 Testthemen from xlsx):
  - **Sprachvarietäten** → Page 100 @ 88%, Pages 69–80 all highly relevant ✓
  - **Lyrische Texte** → Page 94 @ 88%, dedicated Lyrik/Gattungslexikon pages ✓
  - **Kommunikationsmodelle** → Page 6 @ 88%, Pages 1–6 (Kapitel 1) all relevant ✓
- Initial precision looks strong — formal acceptance test pending Philipp's binary ratings

---

## [2026-03-05] Topic Dropdown + Streamlit Cloud Deployment + Credit Caching

### Added
- Topic dropdown in Tab 2: reads yellow-highlighted cells (color `FF92D050`, column 3) from `themen_Claude.xlsx` using openpyxl — replaces free-text input
- `themen_Claude.xlsx` — copy of Philipp's Excel added to repo so app can read topics on Streamlit Cloud
- `.streamlit/config.toml` — headless mode + light theme for cloud deployment
- Streamlit Cloud deployment: auto-deploys from `github.com/jansawatzki/studentpro-pdf-engine` on every push (~60s redeploy)
- **Ingestion cache**: `is_already_indexed()` checks if filename exists in `documents` before running OCR — skips re-ingestion entirely
- **Summary cache**: `summary_cache` Supabase table stores LLM output per topic; `get_cached_summary()` / `save_cached_summary()` functions — every repeat query costs €0
- "🔄 Neu generieren" button allows manual cache bypass
- "💾 Aus Cache geladen" info banner shown when cache hit
- Tab 3 "Projektübersicht" — German project summary for Rachid: tech stack table, what works today, test results, acceptance criteria, open tasks, cost breakdown

### Changed
- Secrets loading: reads from `st.secrets` first (Streamlit Cloud), falls back to `config_Claude.env` locally
- `requirements.txt` added (separate from `requirements_Claude.txt`) for Streamlit Cloud auto-install

### Fixed
- GitHub push auth: embedded PAT in remote URL to fix "Device not configured" error
- Streamlit Cloud TOML secrets invalid format: regenerated from terminal to ensure straight quotes
- Streamlit Cloud `supabase_url is required`: changed from `os.environ` injection to direct `st.secrets` read

---

## [2026-03-08] Project docs moved into Mistral_Claude/

### Changed
- All `_Claude.md` planning docs moved from `/docs/` and project root into `Mistral_Claude/` — colocated with the code
- `/docs/` folder deleted
- All 9 doc files committed to GitHub

### Files affected
- `masterplan_Claude.md`, `implementation_Claude.md`, `design_Claude.md`, `app-flow_Claude.md`, `tasks_Claude.md`, `changelog_Claude.md`, `rules_Claude.md`, `learnings_Claude.md`, `What_I_Need_To_Build_This_Claude.md`

---

## [2026-03-08] Paul D Oberstufe Gesamtband — full ingestion completed

### Added
- `Paul D Oberstufe Gesamtband_2024.pdf` fully indexed: 541MB, 315 pages, 13 batches, `subject = 'Deutsch'`
- Resume logic used: 125 pages already indexed from interrupted first run, remaining 190 pages picked up automatically
- All Paul D pages backfilled with `subject = 'Deutsch'` via SQL update

### Files affected
- Supabase `documents` table (315 new rows)

---

## [2026-03-08] Subject-Based Search Scoping + Paul D Ingestion

### Added
- `subject` column on `documents` table — stores curriculum area (e.g. `Deutsch`, `Mathematik`) for each indexed page
- Updated `match_documents` RPC to accept `subject_filter TEXT DEFAULT NULL` — queries are now scoped to the relevant subject area only (Deutsch topics never search Mathe books and vice versa)
- Resume logic in `ingest_Claude.py`: checks `max(page_number)` already in DB before starting — skips completed batches on interrupted runs (saves OCR credits)
- `SHEET_TO_SUBJECT` mapping in `app_Claude.py`: maps Excel sheet names (`Themenliste Deutsch SEK II` → `Deutsch`, `Themenliste Mathe SEK II` → `Mathematik`) to clean subject keys
- Started indexing `Paul D Oberstufe Gesamtband_2024.pdf` — 541MB, 315 pages, 13 batches — tagged `subject = 'Deutsch'`

### Changed
- `ingest_Claude.py` now requires `subject` as 2nd CLI argument: `python3 ingest_Claude.py <pdf> <subject>`
- `app_Claude.py` extracts `subject` from selected topic's sheet and passes it as `subject_filter` to `match_documents` RPC
- Topic dropdown labels now show clean subject name (e.g. `[Deutsch]`) instead of raw sheet name
- All existing Klett pages backfilled with `subject = 'Deutsch'` via SQL update

### Files affected
- `app_Claude.py`, `ingest_Claude.py`, Supabase DB (schema + RPC updated)

---

## [2026-03-08] Editierbarer System-Prompt mit Supabase-Persistenz

### Added
- `settings` Tabelle in Supabase (`key TEXT PRIMARY KEY, value TEXT`) — speichert globale Einstellungen
- `load_system_prompt()` / `save_system_prompt()` Funktionen — lesen/schreiben den Prompt aus der DB
- `DEFAULT_SYSTEM_PROMPT` — verbesserter Standard-Prompt: erklärt Mistral den Lehrer-Kontext (NRW Sek II, Unterrichtsmaterial erstellen, Schulbuch-Grundlage)
- Expander "⚙️ System-Prompt anpassen" in Tab 2: editierbares Textfeld + "💾 Prompt speichern"-Button

### Changed
- Mistral Large Aufruf lädt den System-Prompt jetzt live aus Supabase statt hardcoded

### Files affected
- `app_Claude.py`, Supabase DB (neue `settings` Tabelle)

---

## [2026-03-08] Lehrplan-Tab + topics-Tabelle + DB-Dropdown

### Added
- `topics` Tabelle in Supabase: `topic, subject, pinned, source, created_at`
- 3 Excel-Themen als `pinned=true, source='excel'` migriert
- `load_topics_from_db()` — lädt Themen aus DB, pinned zuerst
- `extract_topics_with_mistral()` — OCR + Mistral Large extrahiert Themenliste aus Lehrplan-PDF
- Neuer Tab "📄 Lehrplan hochladen": PDF upload → Extraktion → Checkboxen zur Auswahl → Speichern
- Übersicht aller gespeicherten Themen im Lehrplan-Tab
- Kernlehrplan Deutsch + Mathematik (NRW) direkt verarbeitet

### Changed
- Tab-Leiste: 5 Tabs — Bücher hochladen, Lehrplan hochladen, Thema abfragen, Projektübersicht, Wie funktioniert es?
- Tab 2 Dropdown lädt jetzt aus `topics` DB-Tabelle statt aus Excel
- ★ Prefix für pinned Themen im Dropdown (Philipps markierte oben)
- `load_yellow_topics()` entfernt — ersetzt durch `load_topics_from_db()`

### Files affected
- `app_Claude.py`, Supabase DB (`topics` Tabelle)

---

## [2026-03-08] course_type (EF/GK/LK) + auto-detection + full re-migration

### Added
- `course_type` column in `topics` table (EF / GK / LK)
- New unique constraint: `topic + subject + course_type`
- Mistral auto-detects subject AND course type from Lehrplan PDF — returns topics grouped by EF/GK/LK
- Extraction review UI shows topics per detected course type with checkboxes
- Dropdown labels now show `[Deutsch · EF]` format

### Changed
- `extract_topics_with_mistral()` returns `(subject, {"EF": [...], "GK": [...], "LK": [...]})` instead of flat list
- `load_topics_from_db()` includes course_type in returned tuples
- All Excel topics re-migrated with correct course_type — 93 topics total across 6 course groups
- Pinned protection includes course_type in key — no cross-course-type collisions
- Topics overview: grouped subject → EF → GK → LK in expanders

### Files affected
- `app_Claude.py`, Supabase DB (`topics` table: new column + constraint)

---

## [2026-03-08] Lehrplan-Tab: fixes + expandable subjects + auto-detect Fach

### Fixed
- Pinned topics overwritten by lehrplan upsert: upsert now checks pinned status before writing — pinned=true is never overwritten
- Re-pinned Philipps 3 Excel-Themen in DB (waren durch Lehrplan-upsert auf false gesetzt worden)
- Red highlighting now uses `<div>` instead of `<span>` for correct Streamlit HTML rendering

### Changed
- Subject dropdown removed — Mistral now auto-detects the subject from the PDF content
- Topics list replaced with expandable sections per subject (st.expander), showing topic count and pinned count in header
- Detected subject shown as confirmation after extraction

### Files affected
- `app_Claude.py`, Supabase DB (topics re-pinned)

---

## [2026-03-08] Lehrplan-Tab: farbige Hervorhebung + PDF-Quellliste

### Added
- `source_file` Spalte in `topics` Tabelle — speichert Dateiname des Lehrplan-PDFs pro Thema
- "Verwendete Lehrplan-PDFs" Liste im Lehrplan-Tab: zeigt welche PDFs verarbeitet wurden, Fach und Anzahl extrahierter Themen — analog zur Bücherliste
- Pinned Themen (Philipps Excel-Auswahl) werden rot hinterlegt angezeigt (`#ff4b4b`, weiße Schrift)

### Changed
- Beim Speichern von Themen wird `source_file` (Dateiname des hochgeladenen PDFs) mitgespeichert
- Kernlehrplan Deutsch + Mathematik mit `source_file` backgefüllt

### Files affected
- `app_Claude.py`, Supabase DB (`topics` Tabelle: neue Spalte `source_file`)

---

## [2026-03-08] UI-Texte bereinigt

### Changed
- Tab 4: Untertitel "Für Philipp & Rachid" entfernt
- Tab 4: Caption mit Kontakt-E-Mail entfernt
- Tab 3: Caption "Stand: März 2026 — gebaut von Jan" entfernt

### Files affected
- `app_Claude.py`

---

## [2026-03-08] Tab 4 "Wie funktioniert es?" + Projektübersicht generalisiert

### Added
- Tab 4 "❓ Wie funktioniert es?": erklärt das System auf Deutsch für Philipp & Rachid —
  Ingestion-Ablauf, Suchlogik, was Mistral aktuell bekommt, Qualitäts-Stellschrauben,
  Abnahmekriterium

### Changed
- Tab 3: "für Rachid" aus Header und Titel entfernt → jetzt allgemeine "Projektübersicht"
  für alle Beteiligten (Rachid, Philipp, Jan)

### Files affected
- `app_Claude.py`

---

## [2026-03-08] Book selector with subject grouping

### Added
- Book selector in Tab 2: all indexed books shown with checkboxes, grouped by subject (Deutsch, Mathematik, etc.), all ticked by default
- `load_indexed_books()` function: queries distinct `(filename, subject)` pairs live from DB
- `filename_filter text[]` parameter added to `match_documents` RPC — search is scoped to only the selected books
- "Relevante Inhalte abrufen" button disabled when no books are selected

### Changed
- `match_documents` RPC now accepts both `subject_filter` and `filename_filter` (both optional)

### Files affected
- `app_Claude.py`, Supabase RPC (`match_documents`)

---

## [2026-03-08] Enable YOLO Mode (bypass permissions permanently)

### Added
- `.claude/settings.json` — sets `defaultMode: bypassPermissions` so Claude Code never asks for tool-use confirmations in this project

### Files affected
- `Mistral_Claude/.claude/settings.json` (new)

---

## [2026-03-08] design_Claude.md aktualisiert

### Changed
- `design_Claude.md`: Version 1.1 — "Current State" Abschnitt ergänzt: 5-Tab-Struktur, Farbsignale (#ff4b4b rot, #21a354 grün, Cache-Banner)

### Files affected
- `design_Claude.md`

---

## [2026-03-08] nextstepsandquality_Claude.md erstellt

### Added
- `nextstepsandquality_Claude.md` — priorisierte Next-Steps-Liste + Qualitäts-Verbesserungsplan, geschrieben für technische und nicht-technische Leser (14-year-old level), mit Begründung und Aufwandsschätzung für jeden Punkt

### Files affected
- `nextstepsandquality_Claude.md` (neu)

---

## [2026-03-08] Projektübersicht + Masterplan aktualisiert

### Changed
- Tab 3 „Projektübersicht": vollständig auf Stand 08.03.2026 gebracht — alle 5 Tabs dokumentiert, DB-Stand-Tabelle, beide System-Prompts, Farbmarkierungen, Buchbestand, Themenübersicht
- `masterplan_Claude.md`: Version 1.2 — Phasentabelle mit Status ✅/⬜ aktualisiert, Phase 0b–0d als erledigt markiert, aktuellen Stand 2026-03-08 ergänzt

### Files affected
- `app_Claude.py` (Tab 3), `masterplan_Claude.md`

---

## [2026-03-08] Keyword-Matching + Subject-Normalisierung + UI-Fixes

### Added
- `normalize_subject()` — mappt Mistrals Freitext-Fach ("Mathematik Sekundarstufe II" → "Mathematik") auf DB-Key; verhindert 0-Treffer wenn Mistral leicht abweichende Bezeichnung zurückgibt
- `_kw()`, `get_excel_topics_keywords()`, `find_matching_excel_topic()` — Keyword-Overlap-Matching (≥55% Überschneidung) statt Exact-String-Match; findet Treffer auch wenn Formulierungen leicht abweichen
- `TOPIC_PLACEHOLDER` — filtert "Inhalticher Schwerpunkt / konkretes Unterrichtsthema" aus Extraktion + Metriken heraus
- Qualitätsmetriken zeigen jetzt pro Treffer: Excel-Formulierung vs. Lehrplan-Formulierung (aufklappbar)
- Speichern setzt jetzt `in_lehrplan=True` für alle Excel-Themen die gematcht wurden

### Fixed
- Mathe: Keyword-Matching findet jetzt Übereinstimmungen trotz langer/abweichender Formulierungen
- Fach-Erkennung: `extract_topics_with_mistral()` wendet jetzt `normalize_subject()` an

### Changed
- "Extraktions-Prompt" → "System-Prompt" im Lehrplan-Tab (konsistent mit Tab 2)
- System-Prompt Expander unterhalb des Datei-Uploaders verschoben
- Jan/GitHub Caption aus Tab 3 entfernt

### Files affected
- `app_Claude.py`

---

## [2026-03-08] Editierbarer Extraktions-Prompt + Mathe-Matching-Fix + Tab-Update

### Added
- `DEFAULT_EXTRACTION_PROMPT` — Extraktions-System-Prompt als editierbare Konstante (war hardcoded)
- `load_extraction_prompt()` / `save_extraction_prompt()` — lesen/schreiben aus `settings` Tabelle (key: `extraction_prompt`)
- Expander „⚙️ Extraktions-Prompt anpassen" im Lehrplan-Tab mit Speichern-Button — analog zum Zusammenfassungs-Prompt in Tab 2

### Fixed
- Mathe-Qualitätsmetrik: `get_excel_topics_set()` akzeptiert jetzt `subject` Parameter — Matching filtert auf das erkannte Fach statt alle 93 Themen (Deutsch + Mathe gemischt zu vergleichen)

### Changed
- `extract_topics_with_mistral()` lädt jetzt Prompt live aus Supabase statt hardcoded
- Tab „Wie funktioniert es?" vollständig überarbeitet: 3 Phasen, beide System-Prompts erklärt, Farbmarkierungen dokumentiert, Stellschrauben aktualisiert

### Files affected
- `app_Claude.py`

---

## [2026-03-08] Lehrplan-Cache + Qualitätsmetriken

### Added
- `load_lehrplan_from_cache()` — prüft ob PDF bereits extrahiert wurde (`source='lehrplan', source_file=filename`); lädt Topics aus DB statt Mistral neu aufzurufen
- `get_excel_topics_set()` — gibt lowercase Set aller Excel-Themen zurück für Matching
- "💾 Aus Cache geladen" Banner im Lehrplan-Tab wenn PDF schon verarbeitet wurde
- "🔄 Neu extrahieren" Button zum manuellen Cache-Bypass (löscht lehrplan-Zeilen, startet neu)
- Qualitätsmetriken nach Extraktion: 3 Metriken-Spalten — extrahierte Themen, Philipps Excel-Themen, Übereinstimmungen (X / Y)
- Aufklappbare Liste aller Übereinstimmungen
- ✓ Prefix für Excel-Übereinstimmungen in der Themen-Auswahlliste

### Files affected
- `app_Claude.py`

---

## [2026-03-08] Grüne Hervorhebung für Kernlehrplan-Themen

### Added
- `in_lehrplan` boolean column in `topics` table — marks Excel topics that also appear in extracted Kernlehrplan content (22 matches found: Deutsch EF/GK/LK)
- Green highlighting in topics overview: topics with `in_lehrplan=true` (and not pinned/red) shown with green background (#21a354) and ✓ symbol
- Expander header shows count of Kernlehrplan matches alongside Philipp's pinned count

### Changed
- Topics overview query now fetches `in_lehrplan` column
- Three-state display: ★ red (pinned by Philipp) · ✓ green (in Kernlehrplan) · plain (neither)

### Files affected
- `app_Claude.py`, Supabase DB (`topics` table: new `in_lehrplan` column)

---

**Format for new entries:**
- **Added** for new features
- **Changed** for changes in existing functionality
- **Fixed** for bug fixes
- **Removed** for deprecated or removed features
- **Security** for security improvements

**Rules:**
- Add a new entry after every completed task or group of related tasks
- Include the date, a short description, and files affected
- This is a historical log — never edit or delete past entries
