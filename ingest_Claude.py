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

BATCH_SIZE   = 25      # pages per OCR batch (keeps each batch well under 50 MB)
EMBED_BATCH  = 10      # pages per embedding API call
MAX_CHARS    = 8000    # truncate very long pages before embedding


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
    """Embed pages in batches and upsert into Supabase."""
    # Collect non-empty pages
    valid = []
    for page in pages:
        text = (page.markdown or "").strip()
        if text:
            valid.append({
                "filename": filename,
                "page_number": page_offset + page.index,
                "content": text[:MAX_CHARS],
                "subject": subject,
            })

    # Embed in batches
    for i in range(0, len(valid), EMBED_BATCH):
        chunk = valid[i : i + EMBED_BATCH]
        texts = [p["content"] for p in chunk]
        emb_resp = mistral.embeddings.create(model="mistral-embed", inputs=texts)
        for j, item in enumerate(chunk):
            item["embedding"] = emb_resp.data[j].embedding

        # Upsert
        supabase.table("documents").upsert(
            chunk,
            on_conflict="filename,page_number",
        ).execute()

    return len(valid)


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

    batches = split_pdf(pdf_path, BATCH_SIZE)
    total_stored = 0

    for idx, (pdf_bytes, start_page) in enumerate(batches, 1):
        end_page = min(start_page + BATCH_SIZE - 1, total)
        size_mb  = len(pdf_bytes) / 1_000_000

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
