# Next Steps & Quality Improvements — student PRO PDF Engine

**Created:** 2026-03-08 | **Owner:** Jan

This document explains what we should build next and how we can make the results better.
Written so that anyone — technical or not — can follow along.

---

## How the system works right now (quick recap)

Think of it like a really smart library assistant.

1. We feed it schoolbooks (the PDFs). It reads every single page and gives each page a **secret code** — a list of 1024 numbers that describes what that page is about. Similar pages get similar codes. This is called an *embedding*.

2. When Philipp picks a topic (e.g. "Lyrische Texte"), we turn that topic into a secret code too.

3. The system finds the pages whose codes are closest to the topic's code — like finding the shelf in the library that's most similar to what you're looking for.

4. Mistral then reads those top-10 pages and writes a summary in German.

That's the full pipeline. Now here's what comes next and how to make it better.

---

## Part 1 — What to build next

*(Sorted by importance: most critical at the top)*

---

### 🔴 1. Export — save results as a file Philipp can upload

**What:** Add a button that saves the summary + source pages as a JSON or CSV file — exactly the format Philipp's admin panel expects.

**Why this is #1:**
The whole point of this system is to get content *into Philipp's teacher app*. Right now we produce nice summaries on screen but they go nowhere. Without export, we're like a chef who cooks a meal and then throws it in the bin. Export is what turns a demo into a working tool.

**How hard:** Small. 1–2 hours of work.

---

### 🔴 2. Formal acceptance test with Philipp

**What:** Philipp picks 5 topics, looks at the top-10 pages retrieved for each, and marks each one as ✓ (relevant) or ✗ (not relevant). Goal: at least 8 out of 10 correct per topic.

**Why this is #2:**
This is the contractual agreement. We cannot close the project without it. The test also tells us *exactly* where the system is wrong — which topics fail, which books are missing coverage. Without it we're guessing. With it we know precisely what to fix.

**Blocked on:** Philipp needs to sit down and do the rating. Export (#1) should be done first so he sees the full workflow.

---

### 🔴 3. More books — especially Mathe

**What:** Philipp sends us the Mathematik schoolbook PDFs. We index them with `ingest_Claude.py`.

**Why this is #3:**
Right now there are zero Mathe books in the database. Every single Mathe topic in the dropdown returns no results. It's like asking the library assistant to find a chemistry book in a library that only has history books. We need the source material before anything else works for Mathe.

**Blocked on:** Philipp providing the files.

---

### 🟡 4. Smaller text pieces (chunks instead of whole pages)

**What:** Instead of storing one whole page per database row, cut each page into smaller overlapping pieces of about 500 words (with 100-word overlap between pieces).

**Why this is #4 — and the biggest quality win:**

Imagine you're searching for "Binomialverteilung" and the system finds a page that has one paragraph about it — but also three paragraphs about something completely different. Right now it returns the *whole page*, including the irrelevant parts. Mistral then has to summarize all of it, including the noise.

With smaller chunks:
- Each chunk is about one thing only
- The search finds the *exact* relevant paragraph, not the whole page
- Mistral writes a tighter, more accurate summary
- Fewer irrelevant results in the top-10

---

**❓ How does re-indexing actually work? Does it cost money? Can we do it now?**

Good question — and the answer is better than you'd expect.

**Step 1 — OCR (reading the PDF):** Already done. The text of all 424 pages is sitting in our database right now. We never need to do this again.

**Step 2 — Chunking (splitting the text):** Just a Python function that cuts long text into 500-word pieces. Runs locally, takes seconds, costs €0.

**Step 3 — Embedding (turning text into numbers):** This is the only step that costs Mistral credits. But embedding is the *cheapest* Mistral API — €0.10 per 1 million words. Our 424 pages would produce roughly 800 chunks × 500 words each = ~400,000 words total. That's **€0.04**. Basically free.

**Step 4 — Store in database:** A small schema change (add a `chunk_index` column, update the unique key) and then write the new rows. 30 minutes of work.

**Can we do it right now?**
Yes. Technically nothing stops us. The reason it's listed at #4 and not #1 is purely that export and the acceptance test are *contractual* blockers — they need to happen first to close the project. But if Philipp is very interested in quality, we could flip #4 and #1 — chunking is fast, cheap, and the impact is immediate.

**Total cost of re-indexing all current books:** ~€0.04. **Time to implement:** ~2–3 hours dev work.

---

**How hard:** Medium (2–3 hours dev). Re-indexing cost: ~€0.04.

---

### 🟡 5. Two-type search: semantic + keyword combined (Hybrid Search)

**What:** Right now we only use the "secret code" similarity search (semantic). Add a second search method: plain keyword search (like Google). Combine both results.

**Why this is #5:**

Semantic search is great at finding pages that *talk about* a topic even if they don't use the exact word. But it can miss pages that contain a very specific technical term (like "Schülerexperiment" or "Sekante") without much surrounding context.

Keyword search is the opposite — it finds exact words instantly but misses synonyms.

By combining both (70% semantic score + 30% keyword score), you get the best of both worlds. This is especially important for Mathe, where technical terms like "Ableitungsregel" or "Integralrechnung" need to be found exactly.

**❓ Does this cost extra credits?**
No. BM25 is a standard database feature (PostgreSQL supports it natively). It runs entirely inside Supabase — no Mistral calls needed at search time.

**❓ Why not do it right now?**
It requires adding a text search index to the database and updating the `match_documents` function. About 2 hours of dev work. No blockers otherwise.

**How hard:** Medium (2 hours dev). Extra cost: €0.

---

### 🟡 6. A rating screen inside the app

**What:** Add a ✓ / ✗ button next to each source page in the results. Philipp can rate relevance directly in the browser. The ratings get saved in the database.

**Why this is #6:**
This makes the acceptance test (#2) much easier — Philipp doesn't need spreadsheets or paper. It also creates a feedback loop: every rating improves our understanding of where the system works and where it doesn't. Over time this data could be used to re-train or re-rank results.

**How hard:** Medium. 2–3 hours.

---

### 🟢 7. Query expansion — search with synonyms automatically

**What:** Before searching, ask Mistral to generate 3–5 related terms for the topic. Then search for all of them and merge the results.

**Example:** "Lyrische Texte" → also search for "Gedicht", "Lyrik", "Strophe", "Vers", "poetische Texte"

**Why this is #7:**

Sometimes the schoolbook uses slightly different words than the topic name. A page about "Gedichtanalyse" won't score high if you search for "Lyrische Texte" — even though it's exactly what you want.

Query expansion fixes this by casting a wider net. It's less impactful than chunking or hybrid search, but it's a nice addition once the foundations are solid.

**How hard:** Small. The Mistral API call is one extra step.

---

### 🟢 8. Biologie and Sozialwissenschaften

**What:** Get books and topic lists from Philipp for the other two subjects. Index them. The system already supports multiple subjects — it's purely about adding the data.

**Why this is #8:**
Nothing technical to build. Completely blocked on Philipp delivering the PDFs. This is Phase 5 in the project plan — comes after Deutsch is accepted.

---

## Part 2 — How to improve quality specifically

*(This is what Philipp is most interested in)*

Quality = how often the top-10 pages are actually relevant to the topic. Here's every lever we have, sorted from most to least impactful.

---

### ⭐⭐⭐ Most impactful

#### Cut pages into smaller chunks (see #4 above)
One whole page = many topics mixed together = noise. One 500-word chunk = usually one topic = precise hit. This is the #1 quality lever.

#### Add more books
More books = more coverage. If the answer exists in a book we haven't indexed, the system will never find it. Simple as that.

---

### ⭐⭐ Very impactful

#### Combine keyword + semantic search (see #5 above)
Catches exact technical terms that semantic search misses. Especially important for Mathe.

#### Tune the system prompt
The prompt that Mistral gets when writing the summary is editable in the app. Small changes here can have a big effect on the output quality. For example:
- Tell Mistral the course type (EF, GK, LK) so it can adjust the complexity level
- Tell Mistral which textbook series it's reading from
- Ask it to flag if it's uncertain about something

This costs €0 and can be done immediately.

---

### ⭐ Good to have

#### Query expansion with synonyms (see #7 above)
Casts a wider net. Finds relevant pages that use different words than the topic name.

#### Re-ranking
After getting the top-20 results, use Mistral to score each one again specifically for the topic — and keep only the top-10 from that second pass. Like having a second opinion judge review the first judge's shortlist. Adds one extra Mistral call per query (~€0.01).

#### Increase top_k temporarily
Quick win: change the "Anzahl Ergebnisse" slider from 10 to 15 or 20. Mistral gets more context → more complete summaries. Trade-off: slightly higher cost per query and slightly longer summaries.

---

## Summary table

| # | What | Quality impact | Effort | Blocked on |
|---|---|---|---|---|
| 1 | Export JSON/CSV | — (delivery) | Small | Nothing |
| 2 | Acceptance test | — (validation) | Small | Philipp |
| 3 | More books | ⭐⭐⭐ | Small | Philipp |
| 4 | Smaller chunks | ⭐⭐⭐ | Medium | Nothing |
| 5 | Hybrid search | ⭐⭐ | Medium | Nothing |
| 6 | Rating UI | ⭐ (feedback) | Medium | Nothing |
| 7 | Query expansion | ⭐ | Small | Nothing |
| 8 | Biologie/SoWi | ⭐⭐⭐ (scope) | Small | Philipp |
