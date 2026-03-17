# Implementation Guide — student PRO PDF Retrieval Engine

**Version:** 1.2 | **Created:** 2026-03-04 | **Last updated:** 2026-03-17 | **Owner:** Jan

---

## 0. Current State (as of 2026-03-08) — LIVE

This section describes what is actually deployed. Sections 1–5 below describe the planned Phase 1+ architecture.

### Live DB schema (Supabase)

```sql
-- Indexed book chunks (one row per chunk; multiple chunks per page)
documents (id, filename, page_number, chunk_index int, content, embedding vector(1024), subject, created_at)
UNIQUE (filename, page_number, chunk_index)
-- 424 pages → 2126 chunks (avg ~5 chunks/page, 1500 chars, 200 overlap)

-- Lehrplan topics + Excel topics
topics (id, topic, subject, course_type, pinned bool, in_lehrplan bool,
        source, source_file, created_at)
UNIQUE (topic, subject, course_type)

-- Per-topic summary cache
summary_cache (topic, summary, sources jsonb, hits int, created_at)
UNIQUE (topic)

-- Style reference documents (RAG on examples)
examples (id, filename, subject, content, embedding vector(1024), topic_name, created_at)
UNIQUE (filename)

-- API cost log (one row per OCR/embed operation per book)
processing_log (id, filename, operation, pages, tokens_in, tokens_out, cost_usd, created_at)

-- Global editable settings (key-value store)
settings (key TEXT PRIMARY KEY, value TEXT)
-- keys: 'system_prompt' (summary), 'extraction_prompt' (lehrplan extraction)
```

### Live RPCs

```sql
match_documents(query_embedding vector, match_count int,
                subject_filter text DEFAULT NULL,
                filename_filter text[] DEFAULT NULL)
-- Returns top-N chunks by cosine similarity, scoped to subject + selected books

match_examples(query_embedding vector, match_count int DEFAULT 1)
-- Returns closest style reference document by cosine similarity
```

### Live UI — 5 tabs

| Tab | Purpose |
|---|---|
| 📚 Bücher hochladen | Multi-file PDF upload → OCR → chunk → embed → store; ingestion cache; delete button per book |
| 📄 Lehrplan hochladen | Upload Lehrplan PDF → OCR → Mistral extracts topics by EF/GK/LK; extraction cache; quality metrics; delete button per PDF |
| 📝 Beispiele hochladen | Upload DOCX/PDF style reference → embed → store; delete button per example |
| 🔍 Thema abfragen | Dropdown (from DB) → vector search → Mistral Large summary; summary cache; DOCX download |
| 📋 Projektübersicht | Status, test results, tech stack, cost breakdown |
| ❓ Wie funktioniert es? | System explanation in German (two-phase concept, cost table, levers explainer) |

### Live features
- **Chunking**: 1500 chars, 200 overlap, `chunk_text()` in `app_Claude.py`
- **Ingestion cache**: skip OCR if filename already in `documents`
- **Summary cache**: `summary_cache` table, bypass with "🔄 Neu generieren" (deletes from DB + auto-triggers fresh generation)
- **Lehrplan extraction cache**: load from DB if `source_file` already extracted
- **Style references**: closest example always injected into Mistral Large context (no similarity threshold)
- **Two editable system prompts** stored in `settings`: extraction + summary
- **Subject-scoped search**: Deutsch topics only search Deutsch books
- **Book selector**: checkboxes per book, grouped by subject
- **Topics colour coding**: ★ red = pinned · ✓ green = in Kernlehrplan + Excel · plain = Lehrplan only
- **Quality metrics** after Lehrplan extraction: keyword-overlap matching (≥55%) vs. Excel topics
- **Cost tracking**: `processing_log` for OCR + embed; live cost display (embed + chat) after each generation
- **DOCX export**: `generate_docx()` with Markdown parsing (headings, bold, bullets, sources list)
- **Delete buttons** for books (`documents` table), Lehrplan PDFs (`topics` table), examples (`examples` table)
- **Richer generation status**: spinners show which books are searched; captions show which examples are available + used; cost info after generation

### Live external scripts
- `ingest_Claude.py` — CLI ingestion for large PDFs (25-page batches, resume logic)
- `reindex_Claude.py` — re-indexes existing pages as chunks (used for the chunking migration)

---

## 1. System Architecture

```
┌─────────────────────────────────────────────────────────┐
│                    STREAMLIT UI (German)                 │
│  [Upload Book] [Query Topic] [Rate Results] [Export]    │
└────────────────────────┬────────────────────────────────┘
                         │ HTTP
┌────────────────────────▼────────────────────────────────┐
│                  PYTHON BACKEND (in-process)             │
│                                                          │
│  ingestion.py   retrieval.py   summarize.py   export.py │
└──────┬──────────────────┬──────────────────────────────┘
       │                  │
┌──────▼──────┐   ┌───────▼────────────────────────┐
│  Mistral    │   │        Supabase (pgvector)       │
│  OCR API    │   │                                  │
│  Embed API  │   │  books · chunks · topics         │
│  Large API  │   │  results · ratings               │
└─────────────┘   └──────────────────────────────────┘
```

### Data flow — Ingestion
```
PDF file → Mistral OCR → page-level markdown text
→ chunk (~500 tokens, 100 overlap) → Mistral Embed (1024-dim vector)
→ Supabase: chunks table (text + vector + metadata)
```

### Data flow — Query
```
Topic string → Query Expansion (Mistral Large, 3–5 synonyms)
→ Embed each expanded query → Supabase vector search (top-20 per query)
→ Merge + deduplicate → BM25 keyword re-score → Re-rank (top-10)
→ Mistral Large summarization (German, with page citations)
→ Display + optional binary rating → JSON/CSV export
```

---

## 2. Database Schema (Supabase)

```sql
-- Enable pgvector
CREATE EXTENSION IF NOT EXISTS vector;

-- Books: one row per uploaded PDF
CREATE TABLE books (
  id          uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  title       text NOT NULL,
  filename    text NOT NULL UNIQUE,
  subject     text,           -- 'deutsch' | 'biologie' | 'sozialwissenschaften'
  page_count  int,
  uploaded_at timestamptz DEFAULT now()
);

-- Chunks: text segments with embeddings
CREATE TABLE chunks (
  id           uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  book_id      uuid NOT NULL REFERENCES books(id) ON DELETE CASCADE,
  page_number  int NOT NULL,
  chunk_index  int NOT NULL,  -- position within page (0-based)
  content      text NOT NULL,
  embedding    vector(1024),
  created_at   timestamptz DEFAULT now(),
  UNIQUE(book_id, page_number, chunk_index)
);

-- Index for vector similarity search
CREATE INDEX chunks_embedding_idx
  ON chunks USING ivfflat (embedding vector_cosine_ops)
  WITH (lists = 100);

-- Full-text search index for BM25
CREATE INDEX chunks_content_fts
  ON chunks USING gin(to_tsvector('german', content));

-- Topics: the 103 NRW curriculum topics
CREATE TABLE topics (
  id          uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  subject     text NOT NULL,      -- 'deutsch' | 'biologie' | 'sozialwissenschaften'
  topic_name  text NOT NULL,      -- e.g. 'Lyrik', 'Zellbiologie'
  grade_level text,               -- e.g. 'Oberstufe', 'Klasse 10'
  UNIQUE(subject, topic_name)
);

-- Results: cached retrieval output per topic
CREATE TABLE results (
  id            uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  topic_id      uuid NOT NULL REFERENCES topics(id),
  summary_text  text,
  top_chunks    jsonb,            -- [{chunk_id, score, page, book_title}]
  created_at    timestamptz DEFAULT now(),
  exported_at   timestamptz,
  approved      boolean DEFAULT false
);

-- Ratings: binary relevance scores per chunk per result
CREATE TABLE ratings (
  id        uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  result_id uuid NOT NULL REFERENCES results(id) ON DELETE CASCADE,
  chunk_id  uuid NOT NULL REFERENCES chunks(id),
  relevant  boolean NOT NULL,     -- true = 1, false = 0
  rated_at  timestamptz DEFAULT now()
);
```

### Supabase RPC functions

```sql
-- Semantic search
CREATE OR REPLACE FUNCTION match_chunks(
  query_embedding vector(1024),
  match_count     int DEFAULT 20,
  filter_subject  text DEFAULT NULL
)
RETURNS TABLE (
  id          uuid,
  book_id     uuid,
  book_title  text,
  page_number int,
  content     text,
  similarity  float
)
LANGUAGE sql STABLE AS $$
  SELECT
    c.id, c.book_id, b.title AS book_title,
    c.page_number, c.content,
    1 - (c.embedding <=> query_embedding) AS similarity
  FROM chunks c
  JOIN books b ON b.id = c.book_id
  WHERE (filter_subject IS NULL OR b.subject = filter_subject)
  ORDER BY c.embedding <=> query_embedding
  LIMIT match_count;
$$;

-- Keyword search (BM25)
CREATE OR REPLACE FUNCTION keyword_search_chunks(
  query_text     text,
  match_count    int DEFAULT 20,
  filter_subject text DEFAULT NULL
)
RETURNS TABLE (
  id          uuid,
  book_id     uuid,
  book_title  text,
  page_number int,
  content     text,
  rank        float
)
LANGUAGE sql STABLE AS $$
  SELECT
    c.id, c.book_id, b.title AS book_title,
    c.page_number, c.content,
    ts_rank(to_tsvector('german', c.content),
            plainto_tsquery('german', query_text)) AS rank
  FROM chunks c
  JOIN books b ON b.id = c.book_id
  WHERE to_tsvector('german', c.content) @@ plainto_tsquery('german', query_text)
    AND (filter_subject IS NULL OR b.subject = filter_subject)
  ORDER BY rank DESC
  LIMIT match_count;
$$;
```

---

## 3. Python Module Structure

```
Mistral_Claude/
├── config_Claude.env          # API keys (never commit)
├── requirements_Claude.txt    # dependencies
├── app_Claude.py              # Streamlit entrypoint
│
├── ingestion/
│   ├── ocr.py                 # Mistral OCR upload + extraction
│   ├── chunker.py             # text → chunks with metadata
│   └── embedder.py            # chunks → vectors → Supabase
│
├── retrieval/
│   ├── expand.py              # query expansion (Mistral Large)
│   ├── search.py              # hybrid search (semantic + BM25)
│   └── rerank.py              # merge + re-rank top-10
│
├── generation/
│   └── summarize.py           # Mistral Large → German summary
│
├── export/
│   └── formatter.py           # JSON + CSV export
│
└── db/
    └── client.py              # Supabase client singleton
```

---

## 4. Core Feature Requirements

### Feature 1 — Book Ingestion
- Accept PDF upload via Streamlit file uploader (≤ 200 MB)
- If PDF > 50 MB: split into 100-page batches automatically before sending to Mistral OCR
- Extract markdown text per page via Mistral OCR (`mistral-ocr-latest`)
- Chunk each page: target 400–600 tokens, 100-token overlap, split on paragraph boundaries
- Store chunk metadata: book_id, page_number, chunk_index
- Embed each chunk with `mistral-embed-latest` (batched, max 20 per API call)
- Upsert into `chunks` table (idempotent — re-uploading same book is safe)
- Delete temp file from Mistral Files API after OCR
- Show progress bar during processing

### Feature 2 — Topic Query
- Dropdown populated from `topics` table (grouped by subject)
- On submit:
  1. **Query expansion**: ask Mistral Large to generate 3–5 German synonyms/related terms for the topic
  2. **Semantic search**: embed each expanded query → `match_chunks` RPC (top-20 per variant)
  3. **Keyword search**: `keyword_search_chunks` RPC with original topic name (top-20)
  4. **Merge + deduplicate** by chunk_id
  5. **Re-rank**: score = 0.7 × semantic_similarity + 0.3 × normalized_bm25_rank
  6. Return top-10 chunks
- Cache result in `results` table

### Feature 3 — Quality Rating
- Show Top-10 chunks side by side: book title, page number, text excerpt
- Per chunk: two buttons — ✓ Relevant / ✗ Nicht relevant
- Live precision counter: "X von 10 relevant (X%)"
- Save ratings to `ratings` table
- Highlight if precision < 80% with warning

### Feature 4 — Summary Generation
- On button press: send top-10 (or only relevant-rated) chunks to Mistral Large
- System prompt in German, instructing to cite book + page for every claim
- Display summary in scrollable text area
- Allow Philipp to edit summary inline before export

### Feature 5 — Export
- JSON format: `{topic, subject, grade_level, generated_at, summary, sources: [{book, page, excerpt}]}`
- CSV format: one row per source chunk with columns: topic, book, page, excerpt, relevance_score
- Download buttons for both formats

---

## 5. Chunking Strategy

```python
# Target parameters
CHUNK_SIZE = 500        # tokens (approx. 2,000 chars for German text)
CHUNK_OVERLAP = 100     # tokens
MIN_CHUNK_SIZE = 50     # discard chunks smaller than this

# Split hierarchy (LangChain RecursiveCharacterTextSplitter)
SEPARATORS = ["\n\n", "\n", ". ", " "]
```

German schoolbooks have:
- Chapter headings → keep as metadata
- Info boxes (often marked by special chars) → keep as single chunks
- Margin notes → strip or keep as separate short chunks
- Images → OCR returns alt text / captions only (acceptable)

---

## 6. Phased Implementation Plan

### Phase 0 — Foundation (done ✅)
- [x] Supabase project created, pgvector enabled
- [x] Mistral API key obtained
- [x] Basic Streamlit app: upload PDF → OCR → embed → store → keyword search → summary
- [x] Simple `documents` table (single-table schema)

### Phase 1 — Schema Upgrade
- [ ] Replace single `documents` table with full schema (books, chunks, topics, results, ratings)
- [ ] Run `setup_db_Claude.sql` upgrade in Supabase SQL Editor
- [ ] Migrate `ingestion` logic to use new `books` + `chunks` tables
- [ ] Load topics table with NRW Deutsch topics (manual seed or CSV import)

### Phase 2 — Retrieval Quality
- [ ] Implement query expansion (`retrieval/expand.py`)
- [ ] Implement hybrid search: semantic + BM25 (`retrieval/search.py`)
- [ ] Implement re-ranking with combined score (`retrieval/rerank.py`)
- [ ] Test on 5 Deutsch topics, measure precision manually

### Phase 3 — Full Operator UI
- [ ] Replace free-text keyword input with topics dropdown
- [ ] Add quality rating screen (Feature 3)
- [ ] Add summary generation button (Feature 4)
- [ ] Add JSON + CSV export (Feature 5)
- [ ] Add library view: list all indexed books

### Phase 4 — Acceptance Test
- [ ] Run acceptance test: 5 topics × top-10 → binary rating → ≥ 8/10
- [ ] Rachid code review
- [ ] Philipp walkthrough session
- [ ] Fix any identified gaps

### Phase 5 — Scale
- [ ] Load remaining 103 topics (Biologie, Sozialwissenschaften)
- [ ] Index all subject books
- [ ] End-to-end test across all 3 subjects

---

## 7. Dependencies

```
# requirements_Claude.txt
streamlit>=1.32
mistralai>=1.0
supabase>=2.3
python-dotenv>=1.0
langchain-text-splitters>=0.2   # for RecursiveCharacterTextSplitter
tiktoken>=0.7                    # token counting
```

---

## 8. Environment Variables

```env
# config_Claude.env
MISTRAL_API_KEY=...
SUPABASE_URL=https://xxxx.supabase.co
SUPABASE_ANON_KEY=...
SUPABASE_SERVICE_KEY=...   # backend only — never expose to browser
```

---

## 9. PDF Size Handling

Mistral OCR limit: **50 MB per file**.

For PDFs > 50 MB:
1. Use `pymupdf` to split into 100-page batches → temporary files
2. Process each batch sequentially through OCR
3. Merge page-level results, offset page numbers correctly
4. Delete all temp files after processing

```python
import fitz  # pymupdf
MAX_PAGES_PER_BATCH = 100

def split_pdf(path: str) -> list[bytes]:
    doc = fitz.open(path)
    batches = []
    for start in range(0, len(doc), MAX_PAGES_PER_BATCH):
        batch = fitz.open()
        batch.insert_pdf(doc, from_page=start, to_page=min(start + MAX_PAGES_PER_BATCH - 1, len(doc)-1))
        batches.append(batch.tobytes())
    return batches
```

---

## 10. API Cost Estimates

| Operation | Model | Cost per unit | Est. full corpus |
|---|---|---|---|
| OCR | mistral-ocr-latest | $2 / 1,000 pages | ~$18 (9,000 pages) |
| Embedding | mistral-embed-latest | $0.1 / 1M tokens | ~$2 (full corpus) |
| Query (per topic) | mistral-large-latest | ~$0.05–0.10 | ~$5–10 (103 topics) |
| **Total one-time** | | | **~$30** |
| **Monthly recurring** | | | **~€30–80** |
