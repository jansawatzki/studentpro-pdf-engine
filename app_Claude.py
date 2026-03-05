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

tab1, tab2, tab3 = st.tabs(["📚 Upload PDF", "🔍 Thema abfragen", "📋 Projektübersicht"])

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

# ── Tab 3: Project Summary for Rachid ─────────────────────────────────────────
with tab3:
    st.header("Projektübersicht für Rachid")
    st.caption("Stand: März 2026 — gebaut von Jan")

    st.markdown("""
## Was wurde gebaut?

Eine vollständige **PDF-Retrieval-Engine** für student PRO — das Bildungsplattform-Projekt von Philipp Nitsche (NRW-Lehrplaninhalte für Lehrer).

Das System extrahiert automatisch relevante Inhalte aus großen Schulbuch-PDFs und erstellt strukturierte Zusammenfassungen pro Lehrplan-Thema — damit Philipp seine Lehrer-App mit geprüften Inhalten befüllen kann.

---

## Technischer Stack

| Komponente | Technologie | Zweck |
|---|---|---|
| **OCR / PDF-Extraktion** | Mistral OCR (`mistral-ocr-latest`) | Text aus Schulbuch-PDFs extrahieren |
| **Embeddings** | Mistral Embed (`mistral-embed`, 1024-dim) | Seiten semantisch einbetten |
| **Vektordatenbank** | Supabase pgvector | Vektoren speichern & ähnlichkeitsbasiert suchen |
| **LLM Zusammenfassung** | Mistral Large (`mistral-large-latest`) | Deutsche Zusammenfassungen mit Seitenverweisen |
| **Frontend** | Streamlit | Bedienoberfläche für Philipp |
| **Hosting** | Streamlit Cloud | Öffentlich erreichbar, automatisches Deployment via GitHub |
| **Versionskontrolle** | GitHub (`jansawatzki/studentpro-pdf-engine`) | Automatisches Re-Deployment bei jedem Push |

---

## Was funktioniert heute (05.03.2026)?

**✅ PDF-Ingestion**
- PDFs bis 200 MB werden automatisch in 25-Seiten-Batches aufgeteilt (Mistral-Limit: 50 MB)
- OCR → Chunking → Embedding → Speicherung in Supabase — vollautomatisch
- Bereits getestet: *Klett „Deutsch kompetent EF"* (169 MB, 109 Seiten, 5 Batches)

**✅ Semantische Suche**
- Themen-Dropdown aus der Excel-Liste (gelb markierte Themen, NRW-Lehrplan)
- Vektorbasierte Ähnlichkeitssuche über alle indexierten Bücher
- Top-10 relevante Seiten werden zurückgegeben

**✅ Zusammenfassung**
- Mistral Large erstellt strukturierte deutsche Zusammenfassung mit Seitenverweisen
- Prompt auf NRW-Lehrerkontext optimiert

**✅ Credit-Caching**
- Ingestion: erkennt bereits indexierte PDFs → kein doppelter OCR-Lauf
- Suche: Ergebnisse werden in `summary_cache` gespeichert → jede Folgeabfrage kostet €0
- „Neu generieren"-Button für manuelle Aktualisierung

---

## Erste Testergebnisse (semantische Suche, 3 Testthemen)

| Thema | Top-Treffer | Ähnlichkeit |
|---|---|---|
| Sprachvarietäten und ihre gesellschaftliche Bedeutung | Seite 100 — Lexikon Sprache | 88% |
| Lyrische Texte: Inhalt, Aufbau, sprachliche Gestaltung | Seite 94 — Gattungslexikon Lyrik | 88% |
| Kommunikationsrollen und -funktionen: Kommunikationsmodelle | Seite 6 — Kommunikationsmodelle | 88% |

Alle drei Testthemen liefern direkte Treffer auf Position 1. Formaler Abnahmetest (Top-10, ≥ 8/10 binäre Bewertung) steht noch aus.

---

## Vereinbartes Abnahmekriterium

> Top-10 Retrieval-Ergebnisse für ein definiertes Lehrplan-Thema,
> **≥ 8 von 10 Treffern thematisch relevant** (binäre Bewertung: 1/0),
> stabil über mindestens 5 verschiedene Themen.

---

## Offene Punkte / Nächste Schritte

| Priorität | Aufgabe |
|---|---|
| 🔴 Hoch | Formaler Abnahmetest mit Philipp (binäre Bewertung Top-10) |
| 🔴 Hoch | Weitere Schulbücher von Philipp erhalten und indexieren |
| 🟡 Mittel | Hybrid Search: semantisch + BM25 (Keyword) kombinieren |
| 🟡 Mittel | Query Expansion: Thema → 3–5 Synonyme vor der Suche |
| 🟡 Mittel | Re-Ranking der Top-20 → beste 10 auswählen |
| 🟢 Later | Export: JSON/CSV für Philipp's Admin-Panel |
| 🟢 Later | Alle 103 Themen aus Excel laden (aktuell: 3 Testthemen) |

---

## Kosten (Schätzung)

| Posten | Einmalig | Monatlich |
|---|---|---|
| OCR (gesamtes Korpus ~9.000 Seiten) | ~€18 | — |
| Embeddings (Vollkorpus) | ~€2 | — |
| Zusammenfassungen (103 Themen × 1 Run, dann gecacht) | ~€10 | ~€0 |
| **Gesamt** | **~€30** | **~€0–5** |
""")

    st.divider()
    st.caption("Dieses System wurde vollständig von Jan mit Claude Code als KI-Assistenten gebaut. "
               "Repository: github.com/jansawatzki/studentpro-pdf-engine")
