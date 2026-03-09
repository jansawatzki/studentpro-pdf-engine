"""
Ingestion script — splits large PDFs and indexes them into Supabase.
Usage: python3 ingest_Claude.py <path_to_pdf> <subject>
  subject: e.g. "Deutsch" or "Mathematik"
"""

import os
import sys
import warnings
import tempfile
import time

warnings.filterwarnings("ignore")

from dotenv import load_dotenv
load_dotenv(os.path.join(os.path.dirname(__file__), "config_Claude.env"))

import fitz  # pymupdf
from mistralai import Mistral
from supabase import create_client

MISTRAL_API_KEY = os.getenv("MISTRAL_API_KEY")
SUPABASE_URL    = os.getenv("SUPABASE_URL")
SUPABASE_KEY    = os.getenv("SUPABASE_SERVICE_KEY")

mistral  = Mistral(api_key=MISTRAL_API_KEY)
supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

BATCH_SIZE    = 25      # pages per OCR batch (keeps each batch well under 50 MB)
EMBED_BATCH   = 10      # chunks per embedding API call
MAX_CHARS     = 8000    # truncate very long pages before embedding
CHUNK_CHARS   = 1500    # target chunk size in characters (~500 words)
OVERLAP_CHARS = 200     # overlap between adjacent chunks


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


def split_pdf(pdf_path: str, batch_size: int) -> list[tuple[bytes, int]]:
    """Return list of (pdf_bytes, start_page_1based) tuples."""
    doc = fitz.open(pdf_path)
    total = len(doc)
    batches = []
    for start in range(0, total, batch_size):
        end = min(start + batch_size - 1, total - 1)
        batch_doc = fitz.open()
        batch_doc.insert_pdf(doc, from_page=start, to_page=end)
        batches.append((batch_doc.tobytes(), start + 1))  # 1-based start page
        batch_doc.close()
    doc.close()
    return batches


def ocr_batch(pdf_bytes: bytes, filename: str) -> list[dict]:
    """Upload batch to Mistral OCR, return list of {page_number, text}."""
    # Upload
    mfile = mistral.files.upload(
        file={"file_name": filename, "content": pdf_bytes},
        purpose="ocr",
    )
    signed = mistral.files.get_signed_url(file_id=mfile.id)

    # OCR
    resp = mistral.ocr.process(
        model="mistral-ocr-latest",
        document={"type": "document_url", "document_url": signed.url},
    )

    # Cleanup
    mistral.files.delete(file_id=mfile.id)

    return resp.pages


def embed_and_store(pages: list, filename: str, page_offset: int, subject: str):
    """Chunk pages, embed in batches and upsert into Supabase."""
    all_rows = []
    for page in pages:
        text = (page.markdown or "").strip()
        if not text:
            continue
        chunks = chunk_text(text[:MAX_CHARS])
        for ci, chunk_content in enumerate(chunks):
            all_rows.append({
                "filename": filename,
                "page_number": page_offset + page.index,
                "chunk_index": ci,
                "content": chunk_content,
                "subject": subject,
            })

    for i in range(0, len(all_rows), EMBED_BATCH):
        batch = all_rows[i : i + EMBED_BATCH]
        texts = [r["content"] for r in batch]
        emb_resp = mistral.embeddings.create(model="mistral-embed", inputs=texts)
        for j, item in enumerate(batch):
            item["embedding"] = emb_resp.data[j].embedding
        supabase.table("documents").upsert(
            batch,
            on_conflict="filename,page_number,chunk_index",
        ).execute()

    return len(all_rows)


def ingest(pdf_path: str, subject: str):
    filename = os.path.basename(pdf_path)
    doc      = fitz.open(pdf_path)
    total    = len(doc)
    doc.close()

    print(f"\n{'='*60}")
    print(f"File   : {filename}")
    print(f"Subject: {subject}")
    print(f"Pages  : {total}")
    print(f"Batches: {-(-total // BATCH_SIZE)} × {BATCH_SIZE} pages")
    print(f"{'='*60}\n")

    # Find the highest page already indexed for this file (resume support)
    resume_row = supabase.table("documents").select("page_number") \
        .eq("filename", filename).order("page_number", desc=True).limit(1).execute()
    last_indexed = resume_row.data[0]["page_number"] if resume_row.data else 0
    if last_indexed:
        print(f"Resume : pages 1–{last_indexed} already indexed, skipping those batches\n")

    batches = split_pdf(pdf_path, BATCH_SIZE)
    total_stored = 0

    for idx, (pdf_bytes, start_page) in enumerate(batches, 1):
        end_page = min(start_page + BATCH_SIZE - 1, total)
        size_mb  = len(pdf_bytes) / 1_000_000

        if end_page <= last_indexed:
            print(f"[Batch {idx}/{len(batches)}] Pages {start_page}–{end_page}  → already indexed, skipping")
            continue

        print(f"[Batch {idx}/{len(batches)}] Pages {start_page}–{end_page}  ({size_mb:.1f} MB)")
        print(f"  → Uploading to Mistral OCR...", end=" ", flush=True)

        t0    = time.time()
        pages = ocr_batch(pdf_bytes, f"{filename}_batch{idx}.pdf")
        print(f"done ({time.time()-t0:.0f}s, {len(pages)} pages)")

        print(f"  → Embedding + storing...", end=" ", flush=True)
        t0      = time.time()
        stored  = embed_and_store(pages, filename, start_page, subject)
        total_stored += stored
        print(f"done ({time.time()-t0:.0f}s, {stored} pages stored)")

    print(f"\n✓ Complete — {total_stored}/{total} pages indexed for '{filename}'\n")


if __name__ == "__main__":
    if len(sys.argv) < 3:
        print('Usage: python3 ingest_Claude.py <path_to_pdf> <subject>')
        print('  subject examples: "Deutsch", "Mathematik"')
        sys.exit(1)
    ingest(sys.argv[1], sys.argv[2])
