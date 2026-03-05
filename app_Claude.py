import os
import warnings
import streamlit as st
from dotenv import load_dotenv
from mistralai import Mistral
from supabase import create_client
import openpyxl

# suppress LibreSSL warning on macOS system Python
warnings.filterwarnings("ignore", category=UserWarning, module="urllib3")

# Load local .env (no-op on Streamlit Cloud)
load_dotenv(os.path.join(os.path.dirname(__file__), "config_Claude.env"))

# On Streamlit Cloud, pull secrets into env vars
try:
    for k in ["MISTRAL_API_KEY", "SUPABASE_URL", "SUPABASE_SERVICE_KEY"]:
        if k in st.secrets:
            os.environ[k] = st.secrets[k]
except Exception:
    pass

MISTRAL_API_KEY      = os.getenv("MISTRAL_API_KEY")
SUPABASE_URL         = os.getenv("SUPABASE_URL")
SUPABASE_SERVICE_KEY = os.getenv("SUPABASE_SERVICE_KEY")

mistral  = Mistral(api_key=MISTRAL_API_KEY)
supabase = create_client(SUPABASE_URL, SUPABASE_SERVICE_KEY)

YELLOW     = "FF92D050"
EXCEL_PATH = os.path.join(os.path.dirname(__file__), "themen_Claude.xlsx")

@st.cache_data
def load_yellow_topics():
    """Read topics highlighted yellow from the Excel file, grouped by sheet."""
    wb = openpyxl.load_workbook(EXCEL_PATH)
    groups = {}
    for sheet in wb.sheetnames:
        ws = wb[sheet]
        topics = []
        for row in ws.iter_rows():
            for cell in row:
                if (
                    cell.column == 3
                    and cell.fill
                    and cell.fill.fgColor
                    and cell.fill.fgColor.type == "rgb"
                    and cell.fill.fgColor.rgb == YELLOW
                    and cell.value
                ):
                    topic = str(cell.value).lstrip("• ").strip()
                    topics.append(topic)
        if topics:
            groups[sheet] = topics
    return groups

st.set_page_config(page_title="student PRO — PDF Engine", layout="wide")
st.title("student PRO — PDF Knowledge Engine")

tab1, tab2 = st.tabs(["📚 Upload PDF", "🔍 Search"])

# ── Tab 1: Upload ──────────────────────────────────────────────────────────────
with tab1:
    st.header("Upload & Index a PDF")
    uploaded_file = st.file_uploader("Choose a PDF file", type="pdf")

    if uploaded_file:
        st.write(f"**File:** {uploaded_file.name}  ({uploaded_file.size / 1_000_000:.1f} MB)")

        if st.button("Process PDF", type="primary"):
            file_bytes = uploaded_file.read()

            try:
                # Step 1: Upload file to Mistral (correct dict format)
                with st.spinner("Uploading to Mistral OCR..."):
                    mistral_file = mistral.files.upload(
                        file={
                            "file_name": uploaded_file.name,
                            "content": file_bytes,
                        },
                        purpose="ocr",
                    )
                    signed = mistral.files.get_signed_url(file_id=mistral_file.id)

                # Step 2: Run OCR
                with st.spinner("Running OCR (this may take 1–2 min for large PDFs)..."):
                    ocr_response = mistral.ocr.process(
                        model="mistral-ocr-latest",
                        document={"type": "document_url", "document_url": signed.url},
                    )
                    pages = ocr_response.pages

                st.info(f"OCR complete — {len(pages)} pages extracted")

                # Step 3: Embed + store each page
                progress = st.progress(0, text="Starting embedding...")
                skipped = 0

                for i, page in enumerate(pages):
                    text = page.markdown.strip() if page.markdown else ""
                    if not text:
                        skipped += 1
                        progress.progress((i + 1) / len(pages), text=f"Page {i + 1}/{len(pages)} — skipped (empty)")
                        continue

                    emb = mistral.embeddings.create(
                        model="mistral-embed",
                        inputs=[text[:8000]],
                    )
                    embedding = emb.data[0].embedding

                    supabase.table("documents").upsert(
                        {
                            "filename": uploaded_file.name,
                            "page_number": page.index + 1,
                            "content": text,
                            "embedding": embedding,
                        },
                        on_conflict="filename,page_number",
                    ).execute()

                    progress.progress(
                        (i + 1) / len(pages),
                        text=f"Page {i + 1}/{len(pages)} stored",
                    )

                # Cleanup Mistral temp file
                mistral.files.delete(file_id=mistral_file.id)

                st.success(
                    f"Done! {len(pages) - skipped} pages indexed "
                    f"({skipped} empty pages skipped) — '{uploaded_file.name}'"
                )

            except Exception as e:
                st.error(f"Error: {e}")
                raise

    # Show indexed documents
    st.divider()
    st.subheader("Indexed Documents")
    try:
        rows = supabase.table("documents").select("filename, page_number").execute()
        if rows.data:
            files = {}
            for r in rows.data:
                files.setdefault(r["filename"], 0)
                files[r["filename"]] += 1
            for fname, count in sorted(files.items()):
                st.write(f"- **{fname}** — {count} pages indexed")
        else:
            st.write("No documents indexed yet.")
    except Exception as e:
        st.warning(f"Could not load document list: {e}")

# ── Tab 2: Search ──────────────────────────────────────────────────────────────
with tab2:
    st.header("Thema abfragen")

    topic_groups = load_yellow_topics()

    # Build flat list with group labels for the selectbox
    options = []
    for sheet, topics in topic_groups.items():
        for t in topics:
            options.append((sheet, t))

    if not options:
        st.warning("Keine markierten Themen in der Excel-Datei gefunden.")
    else:
        col1, col2 = st.columns([3, 1])
        with col1:
            labels = [f"{t}  [{sheet}]" for sheet, t in options]
            selected_idx = st.selectbox(
                "Thema auswählen (gelb markierte Themen aus der Excel-Liste):",
                range(len(labels)),
                format_func=lambda i: labels[i],
            )
            keyword = options[selected_idx][1]
        with col2:
            top_k = st.number_input("Anzahl Ergebnisse", min_value=3, max_value=20, value=10)

    if options and st.button("Relevante Inhalte abrufen", type="primary"):

        try:
            # Embed the keyword
            with st.spinner("Embedding search query..."):
                emb = mistral.embeddings.create(
                    model="mistral-embed",
                    inputs=[keyword],
                )
                query_embedding = emb.data[0].embedding

            # Vector similarity search
            with st.spinner("Searching indexed documents..."):
                result = supabase.rpc(
                    "match_documents",
                    {"query_embedding": query_embedding, "match_count": int(top_k)},
                ).execute()
                chunks = result.data

            if not chunks:
                st.warning("No relevant pages found. Make sure you have uploaded and indexed at least one PDF.")
            else:
                # Build context
                context = "\n\n---\n\n".join(
                    [f"[{r['filename']}, Page {r['page_number']}]\n{r['content']}" for r in chunks]
                )

                # Generate summary
                with st.spinner("Generating summary with Mistral Large..."):
                    response = mistral.chat.complete(
                        model="mistral-large-latest",
                        messages=[
                            {
                                "role": "system",
                                "content": (
                                    "You are a helpful assistant for teachers preparing NRW curriculum content. "
                                    "Summarize the provided schoolbook excerpts that are relevant to the given topic. "
                                    "Structure your summary clearly. "
                                    "Always cite the source filename and page number for every key point. "
                                    "Write in German."
                                ),
                            },
                            {
                                "role": "user",
                                "content": f"Topic: {keyword}\n\nRelevant excerpts:\n{context}",
                            },
                        ],
                    )

                # Display summary
                st.subheader("Summary")
                st.markdown(response.choices[0].message.content)

                # Display sources
                st.divider()
                st.subheader(f"Source Pages ({len(chunks)} results)")
                for r in chunks:
                    with st.expander(
                        f"**{r['filename']}** — Page {r['page_number']}  "
                        f"(relevance: {r['similarity']:.0%})"
                    ):
                        st.write(r["content"][:800] + ("..." if len(r["content"]) > 800 else ""))

        except Exception as e:
            st.error(f"Search error: {e}")
            raise
