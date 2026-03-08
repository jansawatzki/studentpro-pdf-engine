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
