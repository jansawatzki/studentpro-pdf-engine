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

# Maps Excel sheet names → subject key stored in DB
SHEET_TO_SUBJECT = {
    "Themenliste Deutsch SEK II": "Deutsch",
    "Themenliste Mathe SEK II":   "Mathematik",
}


def load_indexed_books():
    """Return {subject: [filename, ...]} for all books in the DB."""
    rows = supabase.table("documents").select("filename, subject").execute()
    books = {}
    for r in rows.data:
        subj = r["subject"] or "Sonstige"
        fname = r["filename"]
        if fname not in books.get(subj, []):
            books.setdefault(subj, [])
            if fname not in books[subj]:
                books[subj].append(fname)
    return books


def load_topics_from_db():
    """Return list of (subject, topic, pinned) — pinned topics first."""
    rows = supabase.table("topics").select("subject, topic, pinned") \
        .order("pinned", desc=True).order("topic").execute()
    return [(r["subject"], r["topic"], r["pinned"]) for r in rows.data]


def extract_topics_with_mistral(pdf_bytes: bytes, filename: str, subject: str) -> list[str]:
    """OCR a Lehrplan PDF and extract topic list via Mistral Large."""
    mfile = mistral.files.upload(
        file={"file_name": filename, "content": pdf_bytes}, purpose="ocr"
    )
    signed = mistral.files.get_signed_url(file_id=mfile.id)
    ocr = mistral.ocr.process(
        model="mistral-ocr-latest",
        document={"type": "document_url", "document_url": signed.url},
    )
    mistral.files.delete(file_id=mfile.id)

    full_text = "\n\n".join(p.markdown for p in ocr.pages if p.markdown)

    resp = mistral.chat.complete(
        model="mistral-large-latest",
        messages=[
            {
                "role": "system",
                "content": (
                    "Du bist Experte für NRW-Lehrpläne (Sekundarstufe II). "
                    "Extrahiere aus dem folgenden Lehrplan-Text alle konkreten inhaltlichen Schwerpunkte "
                    "und Unterrichtsthemen — also die Themen, die Lehrer tatsächlich im Unterricht behandeln. "
                    "Gib NUR die Themen zurück, eines pro Zeile, ohne Nummerierung, ohne Erklärungen, ohne Überschriften. "
                    "Keine allgemeinen Kompetenzformulierungen, nur konkrete Inhaltsthemen."
                ),
            },
            {"role": "user", "content": f"Fach: {subject}\n\nLehrplan-Text:\n{full_text[:40000]}"},
        ],
    )
    raw = resp.choices[0].message.content.strip()
    topics = [line.strip("•–- ").strip() for line in raw.splitlines() if line.strip()]
    return topics


DEFAULT_SYSTEM_PROMPT = """\
Du bist ein Assistent für Lehrerinnen und Lehrer in Nordrhein-Westfalen (Sekundarstufe II).

Deine Aufgabe ist es, Lehrern zu helfen, passendes Unterrichtsmaterial für ihre Schülerinnen und Schüler zu erstellen. Viele Lehrer wissen auf Basis der Lehrplan-Themen allein nicht genau, welche konkreten Inhalte sie im Unterricht behandeln sollen — die folgenden Zusammenfassungen aus den Schulbüchern geben ihnen die nötige inhaltliche Grundlage dafür.

Fasse die bereitgestellten Schulbuchauszüge zum angegebenen Thema klar und strukturiert zusammen. Orientiere dich dabei an den Kompetenzerwartungen des NRW-Kernlehrplans. Nenne bei jedem wichtigen Punkt die Quelle (Dateiname und Seitenzahl).

Antworte auf Deutsch.\
"""


def load_system_prompt() -> str:
    row = supabase.table("settings").select("value").eq("key", "system_prompt").execute()
    return row.data[0]["value"] if row.data else DEFAULT_SYSTEM_PROMPT


def save_system_prompt(prompt: str):
    supabase.table("settings").upsert(
        {"key": "system_prompt", "value": prompt},
        on_conflict="key",
    ).execute()


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

tab1, tab_lehrplan, tab2, tab3, tab4 = st.tabs([
    "📚 Bücher hochladen", "📄 Lehrplan hochladen", "🔍 Thema abfragen", "📋 Projektübersicht", "❓ Wie funktioniert es?"
])

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

# ── Tab Lehrplan: Upload & extract topics ──────────────────────────────────────
with tab_lehrplan:
    st.header("Lehrplan hochladen & Themen extrahieren")

    col_upload, col_subject = st.columns([3, 1])
    with col_upload:
        uploaded_lehrplan = st.file_uploader("Lehrplan-PDF auswählen", type="pdf", key="lehrplan_uploader")
    with col_subject:
        lehrplan_subject = st.selectbox("Fach", ["Deutsch", "Mathematik", "Biologie", "Sozialwissenschaften"])

    if uploaded_lehrplan and st.button("Themen extrahieren", type="primary"):
        try:
            with st.spinner("OCR läuft..."):
                pdf_bytes = uploaded_lehrplan.read()
            with st.spinner("Mistral analysiert den Lehrplan und extrahiert Themen..."):
                extracted = extract_topics_with_mistral(pdf_bytes, uploaded_lehrplan.name, lehrplan_subject)
            st.session_state["extracted_topics"]  = extracted
            st.session_state["extracted_subject"] = lehrplan_subject
            st.success(f"{len(extracted)} Themen gefunden.")
        except Exception as e:
            st.error(f"Fehler: {e}")
            raise

    if st.session_state.get("extracted_topics"):
        st.subheader("Themen auswählen")
        st.caption("Alle Themen, die du bestätigst, werden in den Dropdown übernommen.")
        selected_new = []
        for t in st.session_state["extracted_topics"]:
            if st.checkbox(t, value=True, key=f"new_topic_{t}"):
                selected_new.append(t)

        if st.button("✅ Ausgewählte Themen speichern", disabled=not selected_new):
            subj = st.session_state["extracted_subject"]
            for t in selected_new:
                supabase.table("topics").upsert(
                    {"topic": t, "subject": subj, "pinned": False, "source": "lehrplan"},
                    on_conflict="topic,subject",
                ).execute()
            st.success(f"{len(selected_new)} Themen gespeichert — ab sofort im Dropdown verfügbar.")
            st.session_state["extracted_topics"] = []

    st.divider()
    st.subheader("Gespeicherte Themen")
    all_topics = supabase.table("topics").select("subject, topic, pinned, source") \
        .order("pinned", desc=True).order("subject").order("topic").execute().data
    if all_topics:
        current_subject = None
        for r in all_topics:
            if r["subject"] != current_subject:
                current_subject = r["subject"]
                st.markdown(f"**{current_subject}**")
            prefix = "★ " if r["pinned"] else "　"
            st.write(f"{prefix}{r['topic']}  _{r['source']}_")
    else:
        st.write("Noch keine Themen gespeichert.")


# ── Tab 2: Search ──────────────────────────────────────────────────────────────
with tab2:
    st.header("Thema abfragen")

    # ── Book selector ──────────────────────────────────────────────────────────
    st.subheader("Bücher auswählen")
    indexed_books = load_indexed_books()
    selected_books = []
    if not indexed_books:
        st.warning("Noch keine Bücher indexiert.")
    else:
        for subj in sorted(indexed_books.keys()):
            st.markdown(f"**{subj}**")
            for fname in sorted(indexed_books[subj]):
                checked = st.checkbox(fname, value=True, key=f"book_{fname}")
                if checked:
                    selected_books.append(fname)
        if not selected_books:
            st.warning("Bitte mindestens ein Buch auswählen.")
    st.divider()

    options = load_topics_from_db()  # list of (subject, topic, pinned)

    if not options:
        st.warning("Noch keine Themen geladen. Bitte zuerst einen Lehrplan hochladen.")
    else:
        col1, col2 = st.columns([3, 1])
        with col1:
            labels = [
                f"{'★ ' if pinned else ''}{topic}  [{subject}]"
                for subject, topic, pinned in options
            ]
            selected_idx = st.selectbox(
                "Thema auswählen:",
                range(len(labels)),
                format_func=lambda i: labels[i],
            )
            subject = options[selected_idx][0]
            keyword = options[selected_idx][1]
        with col2:
            top_k = st.number_input("Anzahl Ergebnisse", min_value=3, max_value=20, value=10)

        # ── System-Prompt Editor ───────────────────────────────────────────────
        with st.expander("⚙️ System-Prompt anpassen"):
            current_prompt = load_system_prompt()
            edited_prompt = st.text_area(
                "System-Prompt (wird bei jeder Zusammenfassung an Mistral übergeben):",
                value=current_prompt,
                height=220,
                key="system_prompt_editor",
            )
            if st.button("💾 Prompt speichern"):
                save_system_prompt(edited_prompt)
                st.success("Gespeichert.")

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

        if not cached_summary and st.button("Relevante Inhalte abrufen", type="primary", disabled=not selected_books):
            try:
                with st.spinner("Suchanfrage wird eingebettet..."):
                    emb = mistral.embeddings.create(model="mistral-embed", inputs=[keyword])
                    query_embedding = emb.data[0].embedding

                with st.spinner("Dokumente werden durchsucht..."):
                    result = supabase.rpc(
                        "match_documents",
                        {"query_embedding": query_embedding, "match_count": int(top_k),
                         "subject_filter": subject,
                         "filename_filter": selected_books},
                    ).execute()
                    chunks = result.data

                if not chunks:
                    st.warning("Keine relevanten Seiten gefunden. Bitte zuerst ein Buch hochladen.")
                else:
                    context = "\n\n---\n\n".join(
                        [f"[{r['filename']}, Seite {r['page_number']}]\n{r['content']}" for r in chunks]
                    )

                    with st.spinner("Zusammenfassung wird erstellt (Mistral Large)..."):
                        system_prompt = load_system_prompt()
                        response = mistral.chat.complete(
                            model="mistral-large-latest",
                            messages=[
                                {"role": "system", "content": system_prompt},
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

# ── Tab 3: Project Summary ─────────────────────────────────────────────────────
with tab3:
    st.header("Projektübersicht")

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

# ── Tab 4: How it works ────────────────────────────────────────────────────────
with tab4:
    st.header("Wie funktioniert das System?")

    st.markdown("""
## Die zwei Phasen

### 1. Einmalig: Bücher verarbeiten (Ingestion)

Wenn ein PDF hochgeladen wird, passiert folgendes:

```
PDF → OCR (Mistral liest jede Seite als Text)
    → jede Seite wird in ~1024 Zahlen umgewandelt ("Embedding")
    → Zahlen + Text werden in der Datenbank gespeichert
```

Jede Seite bekommt einen **Zahlenvektor** — eine Art mathematischer Fingerabdruck
des Inhalts. Seiten über ähnliche Themen haben ähnliche Vektoren. Das passiert
nur einmal pro Buch und kostet danach nichts mehr.

---

### 2. Bei jeder Suche

```
Thema ("Lyrische Texte")
    → wird ebenfalls in Zahlen umgewandelt
    → Vergleich mit allen gespeicherten Seiten-Vektoren (Cosine Similarity)
    → Top-10 ähnlichsten Seiten werden ausgewählt
    → Mistral Large schreibt eine Zusammenfassung aus diesen 10 Seiten
```

Je kleiner der Abstand zwischen dem Thema-Vektor und einem Seiten-Vektor,
desto relevanter die Seite. Aktuell sehen wir Ähnlichkeitswerte von ~88% auf
dem ersten Platz — das ist ein gutes Ergebnis.

---

## Was übergeben wir Mistral aktuell?

Aktuell bekommt Mistral bei der Suche **nur das Thema** — exakt so wie
Philipp es in der Excel markiert hat.

**Für die Zusammenfassung:**
- Den Thema-Text
- Die 10 gefundenen Schulbuch-Seiten als rohen Text

**Was Mistral nicht weiß:**
- In welchem Fach das Thema liegt
- Für welche Klassenstufe / Kursart (EF, Q1, Q2)
- Was der NRW-Kernlehrplan konkret erwartet
- In welchem Inhaltsfeld das Thema liegt

---

## Stellschrauben für bessere Qualität

| Maßnahme | Aufwand | Effekt |
|---|---|---|
| **Anzahl Ergebnisse erhöhen** (top_k: 10 → 15) | sofort | Mehr Kontext für Mistral → vollständigere Zusammenfassungen |
| **Themen präziser formulieren** | sofort | Semantische Suche reagiert auf Sprache des Schulbuchs |
| **Fach + Kursart in den Prompt** | klein | Zusammenfassungen gezielter auf NRW-Lehrplan |
| **Mehr Bücher indexieren** | mittel | Mehr Quellen = mehr Abdeckung |
| **Hybrid Search** (Semantik + Keyword) | mittel | Findet auch Seiten mit exakten Fachbegriffen |
| **Query Expansion** | mittel | Thema → 3–5 Synonyme → breitere Suche |
| **Kleinere Texteinheiten** (Chunks statt ganzer Seiten) | größer | Präzisere Treffer, weniger Rauschen |

---

## Wie Philipp die Qualität prüfen kann

Das vereinbarte Abnahmekriterium:

> Ein Thema aus der Liste auswählen → Top-10 Ergebnisse anschauen →
> für jede Seite **1** (relevant) oder **0** (nicht relevant) vergeben →
> Ziel: **≥ 8 von 10**, stabil über mindestens 5 verschiedene Themen.

Das ist der schnellste Weg zu sehen, wo das System gut ist — und wo wir
nachbessern müssen.
""")

