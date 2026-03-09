"""
One-time re-indexing script — splits existing page content into chunks and re-embeds.

IMPORTANT: Run the SQL migration in Supabase (Step 1) BEFORE running this script.
See docs/nextstepsandquality_Claude.md for the SQL.

Usage: python3 reindex_Claude.py
"""

import os
import warnings
import time

warnings.filterwarnings("ignore")

from dotenv import load_dotenv
load_dotenv(os.path.join(os.path.dirname(__file__), "config_Claude.env"))

from mistralai import Mistral
from supabase import create_client

MISTRAL_API_KEY = os.getenv("MISTRAL_API_KEY")
SUPABASE_URL    = os.getenv("SUPABASE_URL")
SUPABASE_KEY    = os.getenv("SUPABASE_SERVICE_KEY")

mistral  = Mistral(api_key=MISTRAL_API_KEY)
supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

CHUNK_CHARS   = 1500    # target chunk size in characters (~500 words)
OVERLAP_CHARS = 200     # overlap between adjacent chunks
EMBED_BATCH   = 10      # chunks per embedding API call


def chunk_text(text: str) -> list[str]:
    """Split text into overlapping chunks, breaking at word boundaries."""
    if len(text) <= CHUNK_CHARS:
        return [text]
    chunks = []
    start = 0
    while start < len(text):
        end = start + CHUNK_CHARS
        if end < len(text):
            break_at = text.rfind(' ', start + CHUNK_CHARS // 2, end)
            if break_at == -1:
                break_at = end
            end = break_at
        chunk = text[start:end].strip()
        if chunk:
            chunks.append(chunk)
        start = end - OVERLAP_CHARS
        if start >= len(text):
            break
    return chunks if chunks else [text]


def main():
    print("\n" + "="*60)
    print("student PRO — Re-indexing Script")
    print("="*60)
    print("\nFetching existing pages from database...")

    # Fetch all original pages (chunk_index = 0 after SQL migration)
    rows = supabase.table("documents") \
        .select("id, filename, page_number, content, subject") \
        .eq("chunk_index", 0) \
        .order("filename") \
        .order("page_number") \
        .execute().data

    if not rows:
        print("\n⚠️  No pages found. Did you run the SQL migration first?")
        print("   See docs/nextstepsandquality_Claude.md for the SQL commands.")
        return

    print(f"Found {len(rows)} pages across all books.\n")

    # Find which pages already have chunks (chunk_index > 0 means that page is done)
    done_pages_raw = supabase.table("documents").select("filename, page_number") \
        .gt("chunk_index", 0).execute().data
    done_pages = set((r["filename"], r["page_number"]) for r in done_pages_raw)
    if done_pages:
        print(f"Found {len(done_pages)} pages already chunked — will skip those.\n")

    filenames = sorted(set(r["filename"] for r in rows))
    total_chunks_all = 0

    for fname in filenames:
        pages = [r for r in rows if r["filename"] == fname]
        pending = [p for p in pages if (fname, p["page_number"]) not in done_pages]
        print(f"\n{'='*60}")
        print(f"File   : {fname}")
        print(f"Pages  : {len(pages)} total, {len(pages)-len(pending)} already done, {len(pending)} to process")

        if not pending:
            existing = supabase.table("documents").select("id", count="exact") \
                .eq("filename", fname).execute()
            print(f"  → fully chunked ({existing.count} rows) — skipping")
            total_chunks_all += existing.count
            continue

        # Build all chunk rows for pending pages
        all_new_rows = []
        for page in pending:
            text = (page["content"] or "").strip()
            if not text:
                continue
            chunks = chunk_text(text)
            for ci, chunk_content in enumerate(chunks):
                all_new_rows.append({
                    "filename": page["filename"],
                    "page_number": page["page_number"],
                    "chunk_index": ci,
                    "content": chunk_content,
                    "subject": page["subject"],
                })

        avg_chunks = len(all_new_rows) / len(pages) if pages else 0
        print(f"Chunks : {len(all_new_rows)} (~{avg_chunks:.1f} per page)")
        print(f"Estimated cost: ~€{len(all_new_rows) * 500 / 1_000_000 * 0.10:.4f}\n")

        # Embed + upsert in batches (with retry on rate limit)
        t0 = time.time()
        for i in range(0, len(all_new_rows), EMBED_BATCH):
            batch = all_new_rows[i : i + EMBED_BATCH]
            texts = [r["content"] for r in batch]
            for attempt in range(5):
                try:
                    emb_resp = mistral.embeddings.create(model="mistral-embed", inputs=texts)
                    break
                except Exception as e:
                    if "429" in str(e) and attempt < 4:
                        wait = 2 ** attempt * 5  # 5, 10, 20, 40s
                        print(f"\n  Rate limit — waiting {wait}s...", end=" ", flush=True)
                        time.sleep(wait)
                    else:
                        raise
            for j, item in enumerate(batch):
                item["embedding"] = emb_resp.data[j].embedding
            supabase.table("documents").upsert(
                batch,
                on_conflict="filename,page_number,chunk_index",
            ).execute()
            done = min(i + EMBED_BATCH, len(all_new_rows))
            print(f"  → {done}/{len(all_new_rows)} chunks embedded & stored", end="\r")
            time.sleep(0.3)  # gentle pacing to avoid rate limits

        elapsed = time.time() - t0
        print(f"  → ✓ {len(all_new_rows)} chunks stored for '{fname}'  ({elapsed:.0f}s)       ")
        total_chunks_all += len(all_new_rows)

    print(f"\n{'='*60}")
    print(f"✓ Re-indexing complete")
    print(f"  Pages processed : {len(rows)}")
    print(f"  Total chunks    : {total_chunks_all}")
    print(f"  Avg chunks/page : {total_chunks_all / len(rows):.1f}")
    print(f"{'='*60}\n")
    print("Next: run a test query in the app to verify quality improvement.")


if __name__ == "__main__":
    main()
