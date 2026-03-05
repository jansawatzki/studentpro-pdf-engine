import os
import warnings
import streamlit as st
from dotenv import load_dotenv
from mistralai import Mistral
from supabase import create_client
import openpyxl

warnings.filterwarnings("ignore", category=UserWarning, module="urllib3")

# Streamlit Cloud: read from st.secrets — locally: read from .env file
try:
    MISTRAL_API_KEY      = st.secrets["MISTRAL_API_KEY"]
    SUPABASE_URL         = st.secrets["SUPABASE_URL"]
    SUPABASE_SERVICE_KEY = st.secrets["SUPABASE_SERVICE_KEY"]
except Exception:
    load_dotenv(os.path.join(os.path.dirname(__file__), "config_Claude.env"))
    MISTRAL_API_KEY      = os.getenv("MISTRAL_API_KEY")
    SUPABASE_URL         = os.getenv("SUPABASE_URL")
    SUPABASE_SERVICE_KEY = os.getenv("SUPABASE_SERVICE_KEY")

mistral  = Mistral(api_key=MISTRAL_API_KEY)
supabase = create_client(SUPABASE_URL, SUPABASE_SERVICE_KEY)

YELLOW     = "FF92D050"
EXCEL_PATH = os.path.join(os.path.dirname(__file__), "themen_Claude.xlsx")


@st.cache_data
def load_yellow_topics():
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
                    topics.append(str(cell.value).lstrip("• ").strip())
        if topics:
            groups[sheet] = topics
    return groups


def get_cached_summary(topic: str):
    """Return cached summary + sources if this topic was already run."""
    row = supabase.table("summary_cache").select("*").eq("topic", topic).execute()
    if row.data:
        # increment hit counter
        supabase.table("summary_cache").update(
            {"hits": row.data[0]["hits"] + 1}
        ).eq("topic", topic).execute()
        return row.data[0]["summary"], row.data[0]["sources"]
    return None, None


def save_cached_summary(topic: str, summary: str, sources: list):
    supabase.table("summary_cache").upsert(
        {"topic": topic, "summary": summary, "sources": sources, "hits": 1},
        on_conflict="topic",
    ).execute()


def is_already_indexed(filename: str) -> bool:
    row = supabase.table("documents").select("id").eq("filename", filename).limit(1).execute()
    return len(row.data) > 0


# ── Page config ────────────────────────────────────────────────────────────────
st.set_page_config(page_title="student PRO — PDF Engine", layout="wide")
st.title("student PRO — PDF Knowledge Engine")

tab1, tab2 = st.tabs(["📚 Upload PDF", "🔍 Thema abfragen"])

# ── Tab 1: Upload ──────────────────────────────────────────────────────────────
with tab1:
    st.header("PDF hochladen & indexieren")
    uploaded_file = st.file_uploader("PDF-Datei auswählen", type="pdf")

    if uploaded_file:
        st.write(f"**Datei:** {uploaded_file.name}  ({uploaded_file.size / 1_000_000:.1f} MB)")

        # ── Cache check for ingestion ──────────────────────────────────────────
        already_indexed = is_already_indexed(uploaded_file.name)
        if already_indexed:
            st.success(
                f"✅ **'{uploaded_file.name}'** ist bereits indexiert — "
                f"kein erneuter OCR-Lauf nötig. Mistral-Credits gespart."
            )
            if st.button("🔄 Trotzdem neu verarbeiten (überschreiben)"):
                already_indexed = False  # allow re-run if explicitly requested

        if not already_indexed and st.button("Buch verarbeiten", type="primary"):
            file_bytes = uploaded_file.read()
            try:
                with st.spinner("Hochladen zu Mistral OCR..."):
                    mistral_file = mistral.files.upload(
                        file={"file_name": uploaded_file.name, "content": file_bytes},
                        purpose="ocr",
                    )
                    signed = mistral.files.get_signed_url(file_id=mistral_file.id)

                with st.spinner("OCR läuft (kann 1–2 Minuten dauern)..."):
                    ocr_response = mistral.ocr.process(
                        model="mistral-ocr-latest",
                        document={"type": "document_url", "document_url": signed.url},
                    )
                    pages = ocr_response.pages

                st.info(f"OCR abgeschlossen — {len(pages)} Seiten erkannt")

                progress = st.progress(0, text="Starte Einbettung...")
                skipped = 0
                for i, page in enumerate(pages):
                    text = page.markdown.strip() if page.markdown else ""
                    if not text:
                        skipped += 1
                        progress.progress((i + 1) / len(pages), text=f"Seite {i+1}/{len(pages)} — leer, übersprungen")
                        continue

                    emb = mistral.embeddings.create(model="mistral-embed", inputs=[text[:8000]])
                    embedding = emb.data[0].embedding

                    supabase.table("documents").upsert(
                        {"filename": uploaded_file.name, "page_number": page.index + 1,
                         "content": text, "embedding": embedding},
                        on_conflict="filename,page_number",
                    ).execute()

                    progress.progress((i + 1) / len(pages), text=f"Seite {i+1}/{len(pages)} gespeichert")

                mistral.files.delete(file_id=mistral_file.id)
                st.success(
                    f"Fertig! {len(pages) - skipped} Seiten indexiert "
                    f"({skipped} leere Seiten übersprungen) — '{uploaded_file.name}'"
                )

            except Exception as e:
                st.error(f"Fehler: {e}")
                raise

    st.divider()
    st.subheader("Indexierte Bücher")
    try:
        rows = supabase.table("documents").select("filename, page_number").execute()
        if rows.data:
            files = {}
            for r in rows.data:
                files.setdefault(r["filename"], 0)
                files[r["filename"]] += 1
            for fname, count in sorted(files.items()):
                st.write(f"- **{fname}** — {count} Seiten indexiert")
        else:
            st.write("Noch keine Bücher indexiert.")
    except Exception as e:
        st.warning(f"Bücherliste konnte nicht geladen werden: {e}")

# ── Tab 2: Search ──────────────────────────────────────────────────────────────
with tab2:
    st.header("Thema abfragen")

    topic_groups = load_yellow_topics()
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

        # ── Cache check for summary ────────────────────────────────────────────
        cached_summary, cached_sources = get_cached_summary(keyword)
        if cached_summary:
            st.info("💾 **Aus Cache geladen** — keine Mistral-Credits verbraucht.")
            st.subheader("Zusammenfassung")
            st.markdown(cached_summary)
            if cached_sources:
                st.divider()
                st.subheader(f"Quellseiten ({len(cached_sources)} Treffer)")
                for r in cached_sources:
                    with st.expander(f"**{r['filename']}** — Seite {r['page_number']}  (Relevanz: {r['similarity']:.0%})"):
                        st.write(r["content"][:800] + ("..." if len(r["content"]) > 800 else ""))

            if st.button("🔄 Neu generieren (Cache überschreiben)"):
                cached_summary = None  # fall through to fresh run

        if not cached_summary and st.button("Relevante Inhalte abrufen", type="primary"):
            try:
                with st.spinner("Suchanfrage wird eingebettet..."):
                    emb = mistral.embeddings.create(model="mistral-embed", inputs=[keyword])
                    query_embedding = emb.data[0].embedding

                with st.spinner("Dokumente werden durchsucht..."):
                    result = supabase.rpc(
                        "match_documents",
                        {"query_embedding": query_embedding, "match_count": int(top_k)},
                    ).execute()
                    chunks = result.data

                if not chunks:
                    st.warning("Keine relevanten Seiten gefunden. Bitte zuerst ein Buch hochladen.")
                else:
                    context = "\n\n---\n\n".join(
                        [f"[{r['filename']}, Seite {r['page_number']}]\n{r['content']}" for r in chunks]
                    )

                    with st.spinner("Zusammenfassung wird erstellt (Mistral Large)..."):
                        response = mistral.chat.complete(
                            model="mistral-large-latest",
                            messages=[
                                {
                                    "role": "system",
                                    "content": (
                                        "Du bist ein hilfreicher Assistent für Lehrer, die NRW-Lehrplaninhalte aufbereiten. "
                                        "Fasse die bereitgestellten Schulbuchauszüge zum angegebenen Thema strukturiert zusammen. "
                                        "Nenne bei jedem wichtigen Punkt die Quelle (Dateiname und Seitenzahl). "
                                        "Antworte auf Deutsch."
                                    ),
                                },
                                {"role": "user", "content": f"Thema: {keyword}\n\nRelevante Auszüge:\n{context}"},
                            ],
                        )

                    summary_text = response.choices[0].message.content
                    sources = [
                        {"filename": r["filename"], "page_number": r["page_number"],
                         "similarity": r["similarity"], "content": r["content"]}
                        for r in chunks
                    ]

                    # Save to cache
                    save_cached_summary(keyword, summary_text, sources)

                    st.subheader("Zusammenfassung")
                    st.markdown(summary_text)

                    st.divider()
                    st.subheader(f"Quellseiten ({len(chunks)} Treffer)")
                    for r in chunks:
                        with st.expander(
                            f"**{r['filename']}** — Seite {r['page_number']}  "
                            f"(Relevanz: {r['similarity']:.0%})"
                        ):
                            st.write(r["content"][:800] + ("..." if len(r["content"]) > 800 else ""))

            except Exception as e:
                st.error(f"Fehler bei der Suche: {e}")
                raise
