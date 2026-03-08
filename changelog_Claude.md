# Changelog

All notable changes to this project will be documented in this file.

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

## [2026-03-08] Enable YOLO Mode (bypass permissions permanently)

### Added
- `.claude/settings.json` — sets `defaultMode: bypassPermissions` so Claude Code never asks for tool-use confirmations in this project

### Files affected
- `Mistral_Claude/.claude/settings.json` (new)

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
