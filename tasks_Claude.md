# Tasks — student PRO PDF Retrieval Engine

Source of truth for implementation order. Update status after every completed task.

**Status legend:** `[ ]` pending · `[x]` done · `[~]` in progress · `[!]` blocked

---

## Phase 0 — Foundation

- [x] Create Supabase project + enable pgvector
- [x] Get Mistral API key
- [x] Set up `config_Claude.env` with all credentials
- [x] Install Python dependencies (mistralai, streamlit, supabase, python-dotenv)
- [x] Write `setup_db_Claude.sql` — `documents` table + `match_documents` RPC
- [x] Build basic Streamlit app: upload PDF → OCR → embed → store → search → summary
- [x] Fix `files.upload()` API call (dict format, not tuple)
- [x] Write PRD docs (masterplan, implementation, design, app-flow)
- [x] Write changelog + tasks files
- [x] **Run `setup_db_Claude.sql` via Management API** — pgvector, documents table, match_documents RPC all live

---

---

## Phase 0b — First Real Test (done ✅)

- [x] Install Supabase MCP (personal access token: full user mode)
- [x] Run DB setup via Management API (no manual SQL Editor needed)
- [x] Write `ingest_Claude.py` — handles large PDFs: splits into 25-page batches, OCR → embed → store
- [x] Index `Klett._Deutsch kompetent EF.pdf` (169MB, 109 pages, 5 batches)
- [x] Run 3 test queries (Testthemen from xlsx):
  - Sprachvarietäten → top result p.100 @ 88% ✓
  - Lyrische Texte → top result p.94 @ 88% ✓
  - Kommunikationsmodelle → top result p.6 @ 88% ✓

---

## Phase 1 — Schema Upgrade & Real Pipeline

- [ ] Replace simple `documents` table with full schema:
  - `books` table (id, title, filename, subject, page_count, uploaded_at)
  - `chunks` table (id, book_id, page_number, chunk_index, content, embedding)
  - `topics` table (id, subject, topic_name, grade_level)
  - `results` table (id, topic_id, summary_text, top_chunks, approved)
  - `ratings` table (id, result_id, chunk_id, relevant)
- [ ] Add BM25 full-text index on chunks (German language config)
- [ ] Update ingestion to store per-book metadata + chunk-level granularity
- [ ] Implement proper text chunking (LangChain RecursiveCharacterTextSplitter, 500 tokens, 100 overlap)
- [ ] Seed `topics` table with NRW Deutsch topics (from Philipp's list or public Lehrplan)

---

## Phase 2 — Retrieval Quality

- [ ] Implement query expansion (`expand.py`): Mistral Large generates 3–5 synonyms per topic
- [ ] Implement hybrid search: semantic (pgvector) + BM25 (`ts_rank`) combined
- [ ] Implement re-ranking: score = 0.7 × semantic + 0.3 × BM25
- [ ] Test on 5 Deutsch topics → measure precision manually (target ≥ 8/10)
- [ ] Add large PDF handling: split PDFs > 50 MB into 100-page batches via PyMuPDF

---

## Phase 3 — Full Operator UI

- [ ] Replace free-text keyword input with topics dropdown (from `topics` table, grouped by subject)
- [ ] Add "Bücher verwalten" tab: book library view with delete option
- [ ] Add "Qualität prüfen" tab: binary rating per chunk (✓ / ✗), live precision counter
- [ ] Add "Exportieren" tab: editable summary + JSON/CSV download
- [ ] All UI labels in German

---

## Phase 4 — Acceptance Test

- [ ] Receive real PDFs from Philipp (await kickoff)
- [ ] Receive 103 topics list from Philipp (Excel/CSV)
- [ ] Index Deutsch books
- [ ] Run acceptance test: 5 topics × top-10 → Philipp binary rates → ≥ 8/10 each
- [ ] Rachid code review
- [ ] Philipp sign-off

---

## Phase 5 — Scale

- [ ] Load all 103 topics into `topics` table
- [ ] Index Biologie books
- [ ] Index Sozialwissenschaften books
- [ ] End-to-end test all 3 subjects
- [ ] Deployment (Streamlit Cloud or Railway)
- [ ] Handover: operations runbook for Philipp

---

## Decisions Log

| Date | Decision | Rationale |
|---|---|---|
| 2026-03-05 | Mistral OCR for PDF extraction (not PyMuPDF) | Better quality on real schoolbook PDFs; handles scanned pages |
| 2026-03-05 | Streamlit for UI (not Next.js) | Speed over polish; internal tool only |
| 2026-03-05 | mistral-embed-latest (1024 dim) | EU-hosted, DSGVO compliant, already in contract |
| 2026-03-05 | Supabase pgvector | Already agreed with Philipp; Philipp has full DB control |
| Pre-project | RAG pipeline (Option A) | Scalable; supports new books + recurring use |
