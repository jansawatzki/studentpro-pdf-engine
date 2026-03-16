# App Flow — student PRO PDF Retrieval Engine

**Version:** 2.0 | **Created:** 2026-03-04 | **Last updated:** 2026-03-16 | **Owner:** Jan

---

## 0. Current Tab Structure (as of 2026-03-16 — LIVE)

```
📚 Bücher hochladen  |  📄 Lehrplan hochladen  |  📝 Beispiele hochladen  |  🔍 Thema abfragen  |  ❓ Wie funktioniert es?
```

---

## 1. The Two-Phase Concept — sachliche Wiedergabe vs. stilisierter Text

This is the most important thing to understand about how the system works.

Philipp's goal:
> „Es ist mein Ziel, dass sie sich nach der rein sachlichen Wiedergabe mithilfe von KI,
> die endgültigen Texte als Upload in einer weiteren Phase an diesen Beispielen orientieren."

The system already has these two phases built in — they just need to be understood clearly.

---

### Phase 1 — Sachliche Wiedergabe (was das System heute liefert)

**What it is:** The raw, unmodified text from the schoolbooks — exactly what Mistral OCR read off the pages.

**Where it lives in the UI:** The **„📚 Quellseiten"** expander in Tab „Thema abfragen". Each entry shows:
- Book title + page number
- Relevance score (how well this page matches the topic)
- The original text from that page (first 800 characters)

**How it's produced:**
```
Topic keyword
  → embed (1024-dimensional fingerprint)
  → compare against all stored page fingerprints
  → return Top-N most similar chunks
  → display raw text as-is
```

No AI rewriting happens here. This IS the sachliche Wiedergabe — the factual content as it appears in the source.

---

### Phase 2 — KI-Stilisierung (was Mistral Large daraus macht)

**What it is:** Mistral Large reads the Top-10 chunks and writes a structured summary in the teacher-facing style.

**Where it lives in the UI:** The **„📝 Zusammenfassung"** expander in Tab „Thema abfragen".

**How it's produced:**
```
Top-10 chunks (raw text)
  + System-Prompt (Anweisung: NRW-Kontext, du-Form, Emojis, Content-Struktur)
  + [optional] Beispieldokument als Stilvorlage
  → Mistral Large generates the summary
  → displayed + cached
```

This is where the AI transforms the sachliche Wiedergabe into structured teacher content.

---

### Can these two phases be separated?

**They already are — technically.** The Quellseiten and the Zusammenfassung are two separate things in the UI today.

**What's currently NOT separated:** The button „Relevante Inhalte abrufen" triggers both phases in one click — it retrieves the chunks AND immediately generates the summary.

**A future split could look like this:**

```
Button: [Sachliche Wiedergabe abrufen]   ← Phase 1 only
   → shows Quellseiten (raw book text)
   → no LLM call yet, costs ~€0.00

Button: [Zusammenfassung erstellen]      ← Phase 2 only
   → takes the retrieved chunks
   → calls Mistral Large with system prompt + example
   → costs ~€0.01–0.02
```

This would let Philipp (or a teacher) review the raw source material before committing to an LLM generation. It also makes the cost split explicit — you only pay for Phase 2 when you actually want the styled output.

**Recommendation:** Build this two-button split in Phase 1 of the roadmap. It aligns exactly with Philipp's workflow vision and makes the factual vs. styled distinction transparent.

---

### The role of Beispieldokumente (Phase 2 quality control)

Philipp's example documents (Tab „Beispiele hochladen") are the bridge between the two phases.

```
Beispieldokument = Philipps eigener, fertig geschriebener Text zu einem Thema
                   (das Ziel-Format für die Zusammenfassung)
```

When a summary is generated, the system:
1. Finds the Beispieldokument most similar to the current topic
2. If similarity ≥ 50%, injects it into the Mistral Large prompt:
   _„Orientiere dich am Aufbau und Stil dieses Beispiels"_

The Beispieldokument does NOT change the System-Prompt. It is appended to the user message alongside the source chunks.

**Mistral Large sees three things at once:**
```
[System-Prompt]  → general instructions (NRW, du-Form, structure)
[User message]   → Topic: Lyrische Texte
                   Relevant chunks: [10 book pages]
                   Style reference: [Philipps example document]
```

---

## 2. Tab-by-Tab Flow

---

### Tab 1 — 📚 Bücher hochladen

**Purpose:** Index schoolbooks (one-time per book).

```
Upload PDF
  → Cache check: filename already in documents table?
      YES → "bereits indexiert" banner + skip option
      NO  → [Buch verarbeiten] button

Processing:
  → Upload to Mistral Files API
  → OCR (mistral-ocr-latest) → list of pages with markdown text
  → Log OCR cost to processing_log (pages × $0.002)
  → For each page:
      → chunk_text() → overlapping 1500-char chunks
      → mistral.embeddings.create() → 1024-dim vector per chunk
      → accumulate embed token count
      → upsert into documents table (filename, page_number, chunk_index, content, embedding)
  → Log embed cost to processing_log (tokens × $0.10/1M)
  → Delete file from Mistral Files API
  → Show success: "X Seiten → Y Abschnitte — 💰 $Z"

Bottom: Indexed books list
  → shows filename, page count, chunk count, total cost from processing_log
```

**Key facts:**
- Chunking: ~5 chunks per page, 1500 chars each, 200-char overlap
- Each book is processed exactly once — cache prevents re-OCR
- Subject is NOT manually entered — it's inferred from the Excel sheet mapping or set on the Lehrplan

---

### Tab 2 — 📄 Lehrplan hochladen

**Purpose:** Extract curriculum topics from NRW Lehrplan PDFs (one-time per Lehrplan).

```
[Optional] Edit extraction prompt (saved in Supabase settings table)

Upload PDF
  → Cache check: source_file already in topics table?
      YES → "💾 Aus Cache" banner + show cached topics
           → [🔄 Neu extrahieren] to override
      NO  → [Themen extrahieren] button

Processing:
  → OCR (mistral-ocr-latest) → full text
  → mistral-large-latest with extraction prompt:
      → auto-detect subject (Deutsch, Mathematik, ...)
      → auto-detect course type (EF / GK / LK)
      → extract concrete topic names
  → Parse response: FACH: + === EF === / === GK === / === LK === sections
  → Show extracted topics in review UI

Review UI:
  → Quality metrics: X extracted / Y from Philipps Excel / Z Übereinstimmungen
  → Matching topics highlighted ✓ (green)
  → Pinned topics highlighted ★ (red — Philipps personal priority list)
  → Checkbox per topic to include/exclude

[Ausgewählte Themen speichern]
  → upsert into topics table (subject, course_type, topic, source, source_file)
  → pinned=true is protected — never overwritten by upsert

Bottom: All topics grouped by subject → EF / GK / LK expanders
```

---

### Tab 3 — 📝 Beispiele hochladen

**Purpose:** Upload Philipps hand-crafted example documents as style references for Phase 2.

```
File uploader (docx or pdf, multiple files allowed)
  → Skip check: filename already in examples table?

For each new file:
  → .docx: extract_text_from_docx() [stdlib only, no python-docx]
  → .pdf:  Mistral OCR → full text
  → mistral.embeddings.create() → 1024-dim vector of full text
  → Detect subject from filename (deutsch/mathe keywords)
  → upsert into examples table (filename, topic_name, subject, content, embedding)

Bottom: List of stored examples with delete button
```

**How examples are used at query time (Tab 4):**
```
find_closest_example(query_embedding, subject=subject)
  → match_examples RPC → cosine similarity against all examples
  → if best match similarity ≥ 50%: inject as style reference
  → if < 50%: no example used (summary still generated, just without style guide)
```

---

### Tab 4 — 🔍 Thema abfragen

**Purpose:** The daily-use tab. Select a topic, get source material + AI summary.

```
Book selector:
  → checkboxes per book, grouped by subject, all pre-checked
  → at least one book must be selected

Topic selector:
  → dropdown from topics table
  → pinned topics (★) shown first
  → format: "★ Lyrische Texte  [Deutsch · EF]"
  → top_k slider: 3–20 results (default 10)

[Optional] Edit system prompt (saved in Supabase settings table)

Cache check: topic already in summary_cache?
  YES → "💾 Aus Cache" banner
      → 📝 Zusammenfassung expander (open)
      → 📚 Quellseiten expander (closed)
      → [🔄 Neu generieren] to bypass cache

  NO  → [Relevante Inhalte abrufen] button

On button click (PHASE 1 + PHASE 2 combined today):
  PHASE 1 — Retrieval (sachliche Wiedergabe):
    → embed topic keyword (mistral-embed)
    → match_documents RPC (pgvector cosine similarity)
        filters: subject_filter + filename_filter (selected books)
    → return Top-N chunks (filename, page_number, chunk_index, content, similarity)

  PHASE 2 — Generation (stilisierter Text):
    → find_closest_example() → if similarity ≥ 50%: add as style block
    → load system_prompt from Supabase settings
    → mistral-large-latest:
        system: [system_prompt]
        user:   "Thema: {keyword}\n\nRelevante Auszüge:\n{chunks}\n\n{example_block}"
    → cache result in summary_cache (topic, summary, sources, hits)

Display:
    → 📝 Zusammenfassung expander (open by default)
        → caption: "📄 Stilvorlage: {example_filename} (Ähnlichkeit: X%)" if used
        → st.markdown(summary_text)
    → 📚 Quellseiten (N Treffer) expander (closed by default)
        → nested expanders per chunk: filename, page, similarity, text preview
```

---

### Tab 5 — ❓ Wie funktioniert es?

**Purpose:** Plain-language explanation for Philipp and anyone new to the system.

Contents (all in expanders except the intro):
- 📚 Schritt 1 — Bücher hochladen
- 📄 Schritt 2 — Lehrplan hochladen
- 🔍 Schritt 3 — Thema abfragen
- 📝 Schritt 4 — Beispieldokumente hochladen
- 💰 Was kostet was? (expandable)
- 🎯 Wann ist das System "fertig"?
- 📊 Was ist gerade in der Datenbank?
- 🔧 Technischer Stack

---

## 3. Data Model (current)

| Table | What's in it | Key columns |
|---|---|---|
| `documents` | All book pages + chunks | filename, subject, page_number, chunk_index, content, embedding |
| `topics` | Curriculum topics | subject, course_type, topic, source, source_file, pinned, in_lehrplan |
| `examples` | Philipps style reference docs | filename, subject, topic_name, content, embedding |
| `summary_cache` | Cached query results | topic, summary, sources (JSON), hits |
| `settings` | Editable prompts | key (system_prompt / extraction_prompt), value |
| `processing_log` | Per-operation cost log | filename, operation, pages, tokens_in, tokens_out, cost_usd |

---

## 4. Happy Path (current, end-to-end)

```
ONE-TIME SETUP (per subject):

1. Tab 1 — Upload Klett_Deutsch.pdf
   → 109 Seiten, ~2 min, costs $0.22
   → 2126 Abschnitte indexiert

2. Tab 2 — Upload NRW Kernlehrplan Deutsch.pdf
   → Mistral erkennt: Fach Deutsch, EF + GK + LK
   → Review + speichern → 93 Themen in DB

3. Tab 3 — Upload Philipps Beispieldokument (Lyrische Texte.docx)
   → Text extrahiert, Fingerabdruck gespeichert

DAILY USE (per topic):

4. Tab 4 — Thema auswählen: "Lyrische Texte [Deutsch · EF]"
   → alle Bücher ausgewählt, top_k = 10
   → [Relevante Inhalte abrufen]
   → PHASE 1: Top-10 Buchseiten aus pgvector (88% similarity)
   → PHASE 2: Mistral Large + Philipps Stilvorlage (89% Ähnlichkeit)
   → 📝 Zusammenfassung: fertig in ~15 Sek
   → 📚 Quellseiten: 10 Einträge, aufklappbar

5. Philipp reviewed → Ergebnis passt → gecacht für alle Folgeabfragen
```

---

## 5. What is NOT built yet (planned)

| Feature | Phase | Notes |
|---|---|---|
| Two-button split: Phase 1 (retrieve) separate from Phase 2 (generate) | Phase 1 | Aligns with sachliche Wiedergabe concept |
| Quality rating tab (✓/✗ per chunk, precision counter) | Phase 3 | Acceptance test prep |
| Export tab (JSON/CSV download) | Phase 3 | Contractual requirement |
| Hybrid search (BM25 + semantic) | Phase 2 | Biggest pending quality improvement |
| Query expansion (synonyms via Mistral) | Phase 2 | ~1h dev, now unblocked on paid plan |
| Re-ranking (second Mistral pass on Top-20) | Phase 2 | ~2h dev |
| More books: Cornelsen, Westermann, Mathe | Phase 4+ | Philipp to supply PDFs |

---

## 6. Open Questions for Discussion

1. **Two-button split** — Should Phase 1 (raw source material) and Phase 2 (summary) be triggered separately? This would make the sachliche Wiedergabe visible and reviewable before any LLM generation happens.

2. **Editable sachliche Wiedergabe** — Should Philipp be able to edit/select which of the Top-10 chunks go into the summary prompt? (e.g. deselect 2 irrelevant ones before clicking "Zusammenfassung erstellen")

3. **Teacher upload flow (Philipps Phase 2 vision)** — Teachers upload their own final text → it gets stored → future summaries use it as a style reference (same mechanism as Beispieldokumente today, but teacher-contributed). Is this the right read of his goal?

4. **Acceptance test** — When does Philipp formally rate Top-10 for 5 topics?
