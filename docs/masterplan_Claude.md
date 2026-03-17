# Masterplan — student PRO PDF Retrieval Engine

**Version:** 1.3 | **Created:** 2026-03-04 | **Last updated:** 2026-03-17 | **Owner:** Jan

---

## 1. Vision

Build a reliable, operator-run content production engine that extracts curriculum-relevant passages from large German schoolbook PDFs and compiles them into structured, exportable summaries — enabling Philipp Nitsche to populate the student PRO teacher app with high-quality NRW-curriculum content at scale.

This is **not** a teacher-facing live AI tool. It is a private internal workbench used exclusively by Philipp.

---

## 2. The Problem

Philipp runs **student PRO**, a Flutter/PWA platform that delivers NRW-curriculum content to teachers. The app and its admin upload panel already exist. What is missing is the **content itself**.

He needs to produce one compact content pack (~10 pages) for each of ~103 curriculum topics across three subjects (Deutsch, Biologie, Sozialwissenschaften). The source material is 3–6 large schoolbook PDFs per subject (~200 MB, 400–500 pages each). Topics are scattered throughout each book — there is no table of contents that maps to individual topics.

**The core challenge is retrieval precision.**
- OCR/parsing already works.
- Current precision: ~80% (estimated prior to this system).
- Philipp cannot assess subject-matter quality himself (he is non-specialist in most subjects).
- A wrong chunk that makes it into a content pack damages teacher trust.

---

## 3. Target User

**One user: Philipp Nitsche**

| Attribute | Detail |
|---|---|
| Technical level | Non-technical operator |
| Usage pattern | Batch sessions, one topic at a time |
| Workflow | Select topic → review results → export → upload to app admin panel |
| Subjects | Deutsch (pilot), Biologie, Sozialwissenschaften |
| Language | German (all UI and output in German) |
| Auth | None needed — private internal tool |

---

## 4. Value Proposition

> Give Philipp a one-screen tool where he selects a curriculum topic, gets the most relevant schoolbook content retrieved automatically, reviews it, and exports a ready-to-upload summary — without needing any technical knowledge.

Time saved: manually reading 500-page books for every topic would take weeks. This system does it in under a minute per topic.

---

## 5. Success Metrics

### Primary (contractually binding)
- **Retrieval precision:** Top-10 results, ≥ 8/10 rated relevant by Philipp, stable across ≥ 5 different topics.
- **Acceptance test:** Passed for Deutsch pilot before handover.

### Secondary
- All 103 topics processable without errors.
- Processing time per topic query: < 60 seconds end-to-end.
- Export produces valid JSON/CSV that Philipp's admin panel accepts.
- System is operable by Philipp without developer assistance after onboarding.

### Cost ceiling
- API costs: ≤ €100/month (Mistral OCR + Embed + Large).
- OCR one-time indexing cost for full corpus (~9,000 pages): ~€18 total.

---

## 6. Scope

### In scope
- PDF upload + OCR-based text extraction (Mistral OCR)
- Semantic + keyword hybrid search over embedded chunks
- Query expansion for German curriculum terminology
- Re-ranking of retrieval results
- LLM-generated summaries with page citations (Mistral Large)
- Binary relevance rating UI (quality check)
- DOCX export (live), JSON + CSV export (planned for admin panel integration)
- German-language UI (Streamlit)
- Multi-book search (search across all indexed books simultaneously)
- Style reference documents (RAG on examples)
- Cost tracking per book and per query

### Out of scope (for this project)
- Teacher-facing interface
- Real-time / live queries from end users
- DRM-locked PDFs
- Mathematical formula rendering (formula-heavy books are not in scope)
- Automated admin panel upload (Philipp uploads manually)
- Multi-user access / authentication
- Mobile interface

---

## 7. Architecture Decision

**Chosen: RAG pipeline (Option A)**

Rationale: Regular usage, new books added over time, and structured topic-based querying all require a persistent, scalable vector store. One-shot batch summarization (Option B) fails at 200MB PDFs and cannot be re-queried. Hybrid local approach (Option C) lacks the measurable retrieval quality needed for acceptance.

Stack:
- **OCR:** Mistral OCR (`mistral-ocr-latest`)
- **Embeddings:** Mistral Embed (`mistral-embed-latest`, 1024 dimensions)
- **Vector DB:** Supabase pgvector
- **LLM:** Mistral Large (`mistral-large-latest`)
- **Backend/UI:** Streamlit (Python) → Next.js upgrade if Philipp wants product-grade UI later
- **Hosting:** Streamlit Cloud (MVP) → Railway (if persistent backend needed)
- **Data sovereignty:** EU-hosted (Mistral), Supabase (Philipp has sole DB access)

---

## 8. Delivery Phases

| Phase | Goal | Status |
|---|---|---|
| **0 — Foundation** | Stack running, basic upload + search | ✅ Done |
| **0b — First real test** | Large PDF indexed, 3 queries pass at 88% | ✅ Done |
| **0c — Deployment + Caching** | Streamlit Cloud, summary cache, ingestion cache | ✅ Done |
| **0d — Operator UI** | Subject scoping, book selector, editable prompts, Lehrplan tab, topic DB, EF/GK/LK, keyword matching, chunking (2126 chunks) | ✅ Done |
| **0e — Examples RAG** | Style reference documents, `match_examples` RPC, always-inject closest example | ✅ Done |
| **0f — Multi-upload** | Multi-file upload in Bücher tab, deployment guide | ✅ Done |
| **0g — Cost Tracking** | `processing_log` table, cost per book, live cost display after generation | ✅ Done |
| **0h — DOCX Export** | `generate_docx()` with Markdown parsing, download button in Tab 2 | ✅ Done |
| **1 — Quality** | Hybrid search (BM25 + semantic), query expansion | ⬜ Next |
| **2 — Export for admin panel** | JSON/CSV for admin panel integration, binary rating UI | ⬜ Planned |
| **3 — Acceptance** | Rachid code review, Philipp sign-off on ≥ 8/10 for 5 topics | ⬜ Awaiting |
| **4 — Scale** | Biologie + Sozialwissenschaften books | ⬜ Planned |

**Current status (2026-03-17):** Phases 0–0h complete. System fully operational: 2 books (424 pages, 2126 chunks), DOCX export live, style reference documents, cost tracking. Ready for acceptance test.

---

## 9. Constraints

- DSGVO compliance required → all AI processing must stay EU-hosted (Mistral satisfies this)
- No third-party annotation tools for binary rating — built into the UI
- Philipp's existing admin panel format determines export schema
- Support SLA: 4 hours/month for 3 months post-handover
