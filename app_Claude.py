import os
import re
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
    """Return list of (subject, course_type, topic, pinned) — pinned first."""
    rows = supabase.table("topics").select("subject, course_type, topic, pinned") \
        .order("pinned", desc=True).order("subject").order("course_type").order("topic").execute()
    return [(r["subject"], r["course_type"] or "", r["topic"], r["pinned"]) for r in rows.data]


# ── Subject normalization ───────────────────────────────────────────────────────
_SUBJECT_ALIASES = {
    "mathematik": "Mathematik",
    "mathe":      "Mathematik",
    "deutsch":    "Deutsch",
    "german":     "Deutsch",
}

def normalize_subject(raw: str) -> str:
    """Map Mistral's free-text subject string to the canonical DB key."""
    lower = raw.lower()
    for alias, canonical in _SUBJECT_ALIASES.items():
        if alias in lower:
            return canonical
    return raw.strip()


# ── Topic keyword matching ──────────────────────────────────────────────────────
_STOP = {
    "und", "oder", "der", "die", "das", "von", "in", "an", "auf", "zu", "mit",
    "für", "aus", "bei", "nach", "über", "unter", "vor", "durch", "eine", "eines",
    "einem", "einen", "sowie", "auch", "als", "ihrer", "ihren", "ihrem",
}
TOPIC_PLACEHOLDER = "inhalticher schwerpunkt / konkretes unterrichtsthema"


def _kw(text: str) -> set[str]:
    return {w for w in re.split(r'[\s,;:()\[\]→±/]+', text.lower())
            if len(w) > 3 and w not in _STOP}


def get_excel_topics_keywords(subject: str = None) -> dict[str, set[str]]:
    """Return {topic: keywords} for Excel topics (placeholder row excluded)."""
    q = supabase.table("topics").select("topic").eq("source", "excel")
    if subject:
        q = q.eq("subject", subject)
    return {
        r["topic"]: _kw(r["topic"])
        for r in q.execute().data
        if r["topic"].lower().strip() != TOPIC_PLACEHOLDER
    }


def find_matching_excel_topic(extracted: str, excel_kw: dict[str, set[str]]) -> str | None:
    """Return best-matching Excel topic when keyword overlap ≥ 55%, else None."""
    ext_kw = _kw(extracted)
    if not ext_kw:
        return None
    best_match, best_score = None, 0.0
    for excel_topic, exc_kw in excel_kw.items():
        if not exc_kw:
            continue
        overlap = len(ext_kw & exc_kw)
        min_len  = min(len(ext_kw), len(exc_kw))
        score    = overlap / min_len if min_len else 0
        if score > best_score:
            best_score, best_match = score, excel_topic
    return best_match if best_score >= 0.55 else None


DEFAULT_EXTRACTION_PROMPT = """\
Du bist Experte für NRW-Lehrpläne (Sekundarstufe II).
Analysiere den Lehrplan und gib deine Antwort exakt in diesem Format zurück:

FACH: [Fachname, z.B. Deutsch]

=== EF ===
- Thema 1
- Thema 2

=== GK ===
- Thema 1

=== LK ===
- Thema 1

Regeln:
- EF = Einführungsphase, GK = Qualifikationsphase Grundkurs, LK = Qualifikationsphase Leistungskurs
- Nur konkrete inhaltliche Schwerpunkte, keine allgemeinen Kompetenzformulierungen
- Wenn ein Kurstyp im Dokument nicht vorkommt, lass ihn weg
- Keine Nummerierung, keine Erklärungen außer den Themen selbst\
"""


def load_extraction_prompt() -> str:
    row = supabase.table("settings").select("value").eq("key", "extraction_prompt").execute()
    return row.data[0]["value"] if row.data else DEFAULT_EXTRACTION_PROMPT


def save_extraction_prompt(prompt: str):
    supabase.table("settings").upsert(
        {"key": "extraction_prompt", "value": prompt},
        on_conflict="key",
    ).execute()


def extract_topics_with_mistral(pdf_bytes: bytes, filename: str) -> tuple[str, dict]:
    """OCR a Lehrplan PDF, auto-detect subject + course types, extract topics.
    Returns (subject, {"EF": [...], "GK": [...], "LK": [...]})."""
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

    extraction_prompt = load_extraction_prompt()
    resp = mistral.chat.complete(
        model="mistral-large-latest",
        messages=[
            {"role": "system", "content": extraction_prompt},
            {"role": "user", "content": f"Lehrplan-Text:\n{full_text[:40000]}"},
        ],
    )
    raw = resp.choices[0].message.content.strip()

    # Parse subject
    subject = "Unbekannt"
    for line in raw.splitlines():
        if line.startswith("FACH:"):
            subject = normalize_subject(line.replace("FACH:", "").strip())
            break

    # Parse course type sections
    by_course: dict[str, list[str]] = {}
    current = None
    for line in raw.splitlines():
        stripped = line.strip()
        if stripped in ("=== EF ===", "=== GK ===", "=== LK ==="):
            current = stripped.replace("=", "").strip()
        elif current and stripped.startswith("-"):
            topic = stripped.lstrip("- ").strip()
            if topic:
                by_course.setdefault(current, []).append(topic)

    return subject, by_course


DEFAULT_SYSTEM_PROMPT = """\
Du bist ein Assistent für Lehrerinnen und Lehrer in Nordrhein-Westfalen (Sekundarstufe II).

Deine Aufgabe ist es, Lehrern zu helfen, passendes Unterrichtsmaterial für ihre Schülerinnen und Schüler zu erstellen. Viele Lehrer wissen auf Basis der Lehrplan-Themen allein nicht genau, welche konkreten Inhalte sie im Unterricht behandeln sollen — die folgenden Zusammenfassungen aus den Schulbüchern geben ihnen die nötige inhaltliche Grundlage dafür.

Fasse die bereitgestellten Schulbuchauszüge zum angegebenen Thema klar und strukturiert zusammen. Orientiere dich dabei an den Kompetenzerwartungen des NRW-Kernlehrplans. Nenne bei jedem wichtigen Punkt die Quelle (Dateiname und Seitenzahl).

**Stil und Format:**
- Schreibe in aktivierender, niederschwelliger Sprache — direkt und verständlich, kein akademischer Jargon
- Sprich die Leserin / den Leser mit „du" an
- Strukturiere die Zusammenfassung in mehrere Abschnitte (z. B. „Content 1", „Content 2" usw.), jeder Abschnitt behandelt einen klar abgegrenzten Teilaspekt des Themas
- Beginne jeden Abschnitt mit einer aussagekräftigen Überschrift mit passendem Emoji (z. B. ✅ 🗣️ ⚡️ 📌)
- Hebe wichtige Fachbegriffe mit **Fettdruck** oder `Backticks` hervor
- Falls ein Beispieldokument als Referenzstil beigefügt ist, orientiere dich eng an dessen Aufbau und Tonalität

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


# ── Example documents (few-shot style references) ──────────────────────────────

def extract_text_from_docx(file_bytes: bytes) -> str:
    """Extract plain text from a .docx file (no external library needed)."""
    import zipfile
    import xml.etree.ElementTree as ET
    with zipfile.ZipFile(file_bytes) as z:
        xml_content = z.read("word/document.xml")
    root = ET.fromstring(xml_content)
    ns = "{http://schemas.openxmlformats.org/wordprocessingml/2006/main}"
    paragraphs = []
    for para in root.iter(f"{ns}p"):
        parts = [t.text for t in para.iter(f"{ns}t") if t.text]
        line = "".join(parts).strip()
        if line:
            paragraphs.append(line)
    return "\n".join(paragraphs)


def list_examples() -> list[dict]:
    """Return all uploaded example documents (without embeddings)."""
    rows = supabase.table("examples") \
        .select("id, filename, topic_name, subject, uploaded_at") \
        .order("uploaded_at", desc=True).execute()
    return rows.data or []


def delete_example(example_id: int):
    supabase.table("examples").delete().eq("id", example_id).execute()


def is_example_uploaded(filename: str) -> bool:
    row = supabase.table("examples").select("id").eq("filename", filename).limit(1).execute()
    return len(row.data) > 0


def find_closest_example(query_embedding: list, subject: str = None) -> dict | None:
    """Return the example with highest cosine similarity, or None if table is empty."""
    try:
        params = {"query_embedding": query_embedding, "match_count": 1}
        if subject:
            params["subject_filter"] = subject
        rows = supabase.rpc("match_examples", params).execute()
        if rows.data:
            return rows.data[0]
    except Exception:
        pass
    return None


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


def load_lehrplan_from_cache(filename: str):
    """Return (subject, by_course_dict) if this PDF was already extracted, else (None, None)."""
    rows = supabase.table("topics").select("subject, course_type, topic") \
        .eq("source", "lehrplan").eq("source_file", filename).execute().data
    if not rows:
        return None, None
    subject = rows[0]["subject"]
    by_course: dict[str, list[str]] = {}
    for r in rows:
        by_course.setdefault(r["course_type"] or "EF", []).append(r["topic"])
    return subject, by_course




# ── Page config ────────────────────────────────────────────────────────────────
st.set_page_config(page_title="student PRO — PDF Engine", layout="wide")
st.title("student PRO — PDF Knowledge Engine")

tab1, tab_lehrplan, tab_beispiele, tab2, tab3, tab4 = st.tabs([
    "📚 Bücher hochladen", "📄 Lehrplan hochladen", "📝 Beispiele hochladen",
    "🔍 Thema abfragen", "📋 Projektübersicht", "❓ Wie funktioniert es?"
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
                total_chunks_stored = 0
                for i, page in enumerate(pages):
                    text = page.markdown.strip() if page.markdown else ""
                    if not text:
                        skipped += 1
                        progress.progress((i + 1) / len(pages), text=f"Seite {i+1}/{len(pages)} — leer, übersprungen")
                        continue

                    page_chunks = chunk_text(text[:8000])
                    texts_to_embed = [c for c in page_chunks]
                    emb_resp = mistral.embeddings.create(model="mistral-embed", inputs=texts_to_embed)
                    for ci, chunk_content in enumerate(page_chunks):
                        embedding = emb_resp.data[ci].embedding
                        supabase.table("documents").upsert(
                            {"filename": uploaded_file.name, "page_number": page.index + 1,
                             "chunk_index": ci, "content": chunk_content, "embedding": embedding},
                            on_conflict="filename,page_number,chunk_index",
                        ).execute()
                    total_chunks_stored += len(page_chunks)

                    progress.progress((i + 1) / len(pages), text=f"Seite {i+1}/{len(pages)} ({len(page_chunks)} Abschnitte) gespeichert")

                mistral.files.delete(file_id=mistral_file.id)
                st.success(
                    f"Fertig! {len(pages) - skipped} Seiten → {total_chunks_stored} Abschnitte indexiert "
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
            pages_per_file: dict[str, set] = {}
            chunks_per_file: dict[str, int] = {}
            for r in rows.data:
                pages_per_file.setdefault(r["filename"], set()).add(r["page_number"])
                chunks_per_file[r["filename"]] = chunks_per_file.get(r["filename"], 0) + 1
            for fname in sorted(pages_per_file.keys()):
                n_pages  = len(pages_per_file[fname])
                n_chunks = chunks_per_file[fname]
                if n_chunks > n_pages:
                    st.write(f"- **{fname}** — {n_pages} Seiten ({n_chunks} Abschnitte indexiert)")
                else:
                    st.write(f"- **{fname}** — {n_pages} Seiten indexiert")
        else:
            st.write("Noch keine Bücher indexiert.")
    except Exception as e:
        st.warning(f"Bücherliste konnte nicht geladen werden: {e}")

# ── Tab Lehrplan: Upload & extract topics ──────────────────────────────────────
with tab_lehrplan:
    st.header("Lehrplan hochladen & Themen extrahieren")

    uploaded_lehrplan = st.file_uploader("Lehrplan-PDF auswählen", type="pdf", key="lehrplan_uploader")

    # ── System-Prompt editor ───────────────────────────────────────────────────
    with st.expander("⚙️ System-Prompt anpassen"):
        current_extraction_prompt = load_extraction_prompt()
        edited_extraction_prompt = st.text_area(
            "System-Prompt für Themen-Extraktion (wird bei jedem Lehrplan-Upload an Mistral übergeben):",
            value=current_extraction_prompt,
            height=250,
            key="extraction_prompt_editor",
        )
        if st.button("💾 Prompt speichern", key="save_extraction_prompt"):
            save_extraction_prompt(edited_extraction_prompt)
            st.success("Gespeichert.")

    if uploaded_lehrplan:
        # ── Cache check ────────────────────────────────────────────────────────
        cached_subject, cached_by_course = load_lehrplan_from_cache(uploaded_lehrplan.name)
        if cached_by_course:
            st.info("💾 **Aus Cache geladen** — keine Mistral-Credits verbraucht.")
            st.session_state["extracted_by_course"] = cached_by_course
            st.session_state["extracted_subject"]   = cached_subject
            st.session_state["extracted_filename"]  = uploaded_lehrplan.name
            total = sum(len(v) for v in cached_by_course.values())
            course_summary = ", ".join(f"{ct}: {len(ts)}" for ct, ts in cached_by_course.items())
            st.success(f"Fach: **{cached_subject}** — {total} Themen ({course_summary})")
            if st.button("🔄 Neu extrahieren (Cache überschreiben)"):
                # Delete existing lehrplan rows for this file so re-extraction saves fresh
                supabase.table("topics").delete() \
                    .eq("source", "lehrplan").eq("source_file", uploaded_lehrplan.name).execute()
                st.session_state["extracted_by_course"] = {}
                st.rerun()
        elif st.button("Themen extrahieren", type="primary"):
            try:
                with st.spinner("OCR läuft..."):
                    pdf_bytes = uploaded_lehrplan.read()
                with st.spinner("Mistral erkennt Fach, Kurstyp und extrahiert Themen..."):
                    detected_subject, by_course = extract_topics_with_mistral(pdf_bytes, uploaded_lehrplan.name)
                total = sum(len(v) for v in by_course.values())
                st.session_state["extracted_by_course"] = by_course
                st.session_state["extracted_subject"]   = detected_subject
                st.session_state["extracted_filename"]  = uploaded_lehrplan.name
                course_summary = ", ".join(f"{ct}: {len(ts)}" for ct, ts in by_course.items())
                st.success(f"Fach erkannt: **{detected_subject}** — {total} Themen ({course_summary})")
            except Exception as e:
                st.error(f"Fehler: {e}")
                raise

    if st.session_state.get("extracted_by_course"):
        by_course_now = st.session_state["extracted_by_course"]

        # ── Quality metrics (keyword-overlap matching) ─────────────────────────
        detected_subj = st.session_state.get("extracted_subject")
        excel_kw = get_excel_topics_keywords(subject=detected_subj)
        all_extracted = [
            t for tlist in by_course_now.values() for t in tlist
            if t.lower().strip() != TOPIC_PLACEHOLDER
        ]
        # For each extracted topic find best-matching Excel topic
        matched_pairs: dict[str, str] = {}   # excel_topic → extracted_topic
        for ext in all_extracted:
            match = find_matching_excel_topic(ext, excel_kw)
            if match and match not in matched_pairs:
                matched_pairs[match] = ext
        matched_extracted = set(matched_pairs.values())

        col_a, col_b, col_c = st.columns(3)
        col_a.metric("Extrahierte Themen", len(all_extracted))
        col_b.metric("Philipps Excel-Themen", len(excel_kw))
        col_c.metric("Übereinstimmungen", f"{len(matched_pairs)} / {len(excel_kw)}")
        if matched_pairs:
            with st.expander(f"✓ {len(matched_pairs)} Übereinstimmungen anzeigen"):
                for excel_t, ext_t in sorted(matched_pairs.items()):
                    st.markdown(f"**Excel:** {excel_t}  \n→ *Lehrplan:* {ext_t}")
                    st.divider()

        st.subheader("Themen auswählen")
        st.caption("Alle Themen, die du bestätigst, werden in den Dropdown übernommen. "
                   "✓ = auch in Philipps Excel.")
        selected_new = []  # list of (course_type, topic)
        for ct, topics_list in by_course_now.items():
            st.markdown(f"**{ct}** — {len(topics_list)} Themen")
            for t in topics_list:
                if t.lower().strip() == TOPIC_PLACEHOLDER:
                    continue
                label = f"✓ {t}" if t in matched_extracted else t
                if st.checkbox(label, value=True, key=f"new_topic_{ct}_{t}"):
                    selected_new.append((ct, t))

        if st.button("✅ Ausgewählte Themen speichern", disabled=not selected_new):
            subj  = st.session_state["extracted_subject"]
            fname = st.session_state.get("extracted_filename", "")
            pinned_keys = {
                (r["topic"], r["subject"], r["course_type"])
                for r in supabase.table("topics").select("topic, subject, course_type")
                    .eq("pinned", True).execute().data
            }
            for ct, t in selected_new:
                if (t, subj, ct) in pinned_keys:
                    supabase.table("topics").update({"source_file": fname}) \
                        .eq("topic", t).eq("subject", subj).eq("course_type", ct).execute()
                else:
                    supabase.table("topics").upsert(
                        {"topic": t, "subject": subj, "course_type": ct,
                         "pinned": False, "source": "lehrplan", "source_file": fname},
                        on_conflict="topic,subject,course_type",
                    ).execute()
            # Mark matched Excel topics as in_lehrplan=True
            for excel_topic in matched_pairs.keys():
                supabase.table("topics").update({"in_lehrplan": True}) \
                    .eq("topic", excel_topic).eq("source", "excel").execute()
            st.success(f"{len(selected_new)} Themen gespeichert — {len(matched_pairs)} Excel-Themen als 'im Lehrplan' markiert.")
            st.session_state["extracted_by_course"] = {}

    st.divider()

    # ── Verwendete Lehrplan-PDFs ───────────────────────────────────────────────
    st.subheader("Verwendete Lehrplan-PDFs")
    lehrplan_files = supabase.table("topics").select("source_file, subject") \
        .eq("source", "lehrplan").execute().data
    if lehrplan_files:
        file_counts = {}
        for r in lehrplan_files:
            key = (r["source_file"] or "Unbekannt", r["subject"])
            file_counts[key] = file_counts.get(key, 0) + 1
        for (fname, subj), count in sorted(file_counts.items()):
            st.write(f"- **{fname}** ({subj}) — {count} Themen extrahiert")
    else:
        st.write("Noch keine Lehrplan-PDFs verarbeitet.")

    st.divider()

    # ── Gespeicherte Themen ────────────────────────────────────────────────────
    st.subheader("Gespeicherte Themen")
    all_topics = supabase.table("topics").select("subject, course_type, topic, pinned, in_lehrplan") \
        .order("pinned", desc=True).order("subject").order("course_type").order("topic").execute().data
    if all_topics:
        # Group by subject → course_type
        by_subject: dict[str, dict[str, list]] = {}
        for r in all_topics:
            subj = r["subject"]
            ct   = r["course_type"] or "Sonstige"
            by_subject.setdefault(subj, {}).setdefault(ct, []).append(r)

        CT_ORDER = ["EF", "GK", "LK", "Sonstige"]
        for subj in sorted(by_subject.keys()):
            ct_dict = by_subject[subj]
            total   = sum(len(v) for v in ct_dict.values())
            n_pin   = sum(1 for v in ct_dict.values() for r in v if r["pinned"])
            n_lp    = sum(1 for v in ct_dict.values() for r in v if r.get("in_lehrplan") and not r["pinned"])
            with st.expander(f"{subj} — {total} Themen ({n_pin} von Philipp markiert, {n_lp} im Kernlehrplan)"):
                for ct in CT_ORDER:
                    if ct not in ct_dict:
                        continue
                    st.markdown(f"**{ct}**")
                    for r in ct_dict[ct]:
                        if r["pinned"]:
                            st.markdown(
                                f'<div style="background-color:#ff4b4b; color:white; '
                                f'padding:4px 12px; border-radius:4px; margin:2px 0; '
                                f'font-size:0.9em;">★ {r["topic"]}</div>',
                                unsafe_allow_html=True,
                            )
                        elif r.get("in_lehrplan"):
                            st.markdown(
                                f'<div style="background-color:#21a354; color:white; '
                                f'padding:4px 12px; border-radius:4px; margin:2px 0; '
                                f'font-size:0.9em;">✓ {r["topic"]}</div>',
                                unsafe_allow_html=True,
                            )
                        else:
                            st.write(f"　{r['topic']}")
    else:
        st.write("Noch keine Themen gespeichert.")


# ── Tab Beispiele: Upload style-reference documents ────────────────────────────
with tab_beispiele:
    st.header("Beispieldokumente hochladen")
    st.caption(
        "Lade hier Philipps Beispieldokumente hoch (docx oder pdf). "
        "Das System findet beim Abfragen automatisch das passendste Beispiel "
        "und gibt es Mistral als Stilvorlage mit — so orientiert sich die Zusammenfassung "
        "an Philipps eigenem Format (Content 1 / Content 2 usw.)."
    )

    uploaded_examples = st.file_uploader(
        "Beispieldokumente auswählen (.docx oder .pdf) — mehrere gleichzeitig möglich",
        type=["docx", "pdf"],
        accept_multiple_files=True,
        key="example_uploader",
    )

    if uploaded_examples:
        new_files = [f for f in uploaded_examples if not is_example_uploaded(f.name)]
        already_uploaded = [f for f in uploaded_examples if is_example_uploaded(f.name)]

        if already_uploaded:
            st.info(f"ℹ️ {len(already_uploaded)} Datei(en) bereits vorhanden: {', '.join(f.name for f in already_uploaded)}")

        if new_files:
            st.write(f"**{len(new_files)} neue Datei(en) bereit zum Verarbeiten:**")
            for f in new_files:
                st.write(f"　· {f.name}")

        if st.button(
            f"Alle verarbeiten & speichern ({len(new_files)} neu)" if new_files else "Alle erneut hochladen (überschreiben)",
            type="primary",
            key="process_examples",
            disabled=not uploaded_examples,
        ):
            import io
            files_to_process = new_files if new_files else uploaded_examples
            progress = st.progress(0, text="Starte...")
            for idx, uploaded_file in enumerate(files_to_process):
                progress.progress(idx / len(files_to_process), text=f"Verarbeite {uploaded_file.name} ({idx+1}/{len(files_to_process)})...")
                file_bytes = uploaded_file.read()
                try:
                    if uploaded_file.name.lower().endswith(".docx"):
                        content = extract_text_from_docx(io.BytesIO(file_bytes))
                    else:
                        mfile = mistral.files.upload(
                            file={"file_name": uploaded_file.name, "content": file_bytes},
                            purpose="ocr",
                        )
                        signed = mistral.files.get_signed_url(file_id=mfile.id)
                        ocr = mistral.ocr.process(
                            model="mistral-ocr-latest",
                            document={"type": "document_url", "document_url": signed.url},
                        )
                        mistral.files.delete(file_id=mfile.id)
                        content = "\n\n".join(p.markdown for p in ocr.pages if p.markdown)

                    if not content.strip():
                        st.warning(f"⚠️ {uploaded_file.name} — kein Text extrahiert, übersprungen.")
                        continue

                    emb_resp = mistral.embeddings.create(
                        model="mistral-embed",
                        inputs=[content[:8000]],
                    )
                    embedding = emb_resp.data[0].embedding

                    lower_name = uploaded_file.name.lower()
                    detected_subject = "Deutsch" if "deutsch" in lower_name else \
                                       "Mathematik" if any(x in lower_name for x in ["mathe", "math"]) else None
                    raw_topic = uploaded_file.name.replace(".docx", "").replace(".pdf", "")

                    supabase.table("examples").upsert(
                        {"filename": uploaded_file.name, "topic_name": raw_topic,
                         "subject": detected_subject, "content": content, "embedding": embedding},
                        on_conflict="filename",
                    ).execute()
                    st.success(f"✅ {uploaded_file.name} gespeichert (Fach: {detected_subject or 'unbekannt'})")

                except Exception as e:
                    st.error(f"Fehler bei {uploaded_file.name}: {e}")

            progress.progress(1.0, text="Fertig!")
            st.rerun()

    st.divider()
    st.subheader("Gespeicherte Beispieldokumente")
    examples = list_examples()
    if not examples:
        st.write("Noch keine Beispiele hochgeladen.")
    else:
        for ex in examples:
            col_a, col_b = st.columns([5, 1])
            with col_a:
                subj_label = f"  ·  Fach: {ex['subject']}" if ex["subject"] else ""
                st.write(f"**{ex['filename']}**{subj_label}")
            with col_b:
                if st.button("🗑️ Löschen", key=f"del_example_{ex['id']}"):
                    delete_example(ex["id"])
                    st.rerun()

    # ── Supabase unique constraint for examples.filename ──────────────────────
    # (Created once via Management API — documented here for reference)
    # ALTER TABLE examples ADD CONSTRAINT examples_filename_key UNIQUE (filename);


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

    options = load_topics_from_db()  # list of (subject, course_type, topic, pinned)

    if not options:
        st.warning("Noch keine Themen geladen. Bitte zuerst einen Lehrplan hochladen.")
    else:
        col1, col2 = st.columns([3, 1])
        with col1:
            labels = [
                f"{'★ ' if pinned else ''}{topic}  [{subject} · {course_type}]"
                for subject, course_type, topic, pinned in options
            ]
            selected_idx = st.selectbox(
                "Thema auswählen:",
                range(len(labels)),
                format_func=lambda i: labels[i],
            )
            subject     = options[selected_idx][0]
            course_type = options[selected_idx][1]
            keyword     = options[selected_idx][2]
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
                    chunk_label = f" (Abschnitt {r['chunk_index']+1})" if r.get('chunk_index', 0) > 0 else ""
                    with st.expander(f"**{r['filename']}** — Seite {r['page_number']}{chunk_label}  (Relevanz: {r['similarity']:.0%})"):
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

                    # ── Find closest example for style reference ───────────────
                    closest_example = find_closest_example(query_embedding, subject=subject)
                    if closest_example and closest_example["similarity"] >= 0.5:
                        example_block = (
                            f"\n\n---\n\n**Beispieldokument als Stilvorlage** "
                            f"(orientiere dich an Aufbau und Tonalität, nicht am Inhalt):\n\n"
                            f"{closest_example['content'][:4000]}"
                        )
                        example_note = f"📄 Stilvorlage: **{closest_example['filename']}** (Ähnlichkeit: {closest_example['similarity']:.0%})"
                    else:
                        example_block = ""
                        example_note = None

                    with st.spinner("Zusammenfassung wird erstellt (Mistral Large)..."):
                        system_prompt = load_system_prompt()
                        user_message = (
                            f"Thema: {keyword}\n\nRelevante Auszüge:\n{context}"
                            f"{example_block}"
                        )
                        response = mistral.chat.complete(
                            model="mistral-large-latest",
                            messages=[
                                {"role": "system", "content": system_prompt},
                                {"role": "user", "content": user_message},
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
                    if example_note:
                        st.caption(example_note)
                    st.markdown(summary_text)

                    st.divider()
                    st.subheader(f"Quellseiten ({len(chunks)} Treffer)")
                    for r in chunks:
                        chunk_label = f" (Abschnitt {r.get('chunk_index', 0)+1})" if r.get('chunk_index', 0) > 0 else ""
                        with st.expander(
                            f"**{r['filename']}** — Seite {r['page_number']}{chunk_label}  "
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
| **OCR / PDF-Extraktion** | Mistral OCR (`mistral-ocr-latest`) | Text aus Schulbuch- und Lehrplan-PDFs extrahieren |
| **Embeddings** | Mistral Embed (`mistral-embed`, 1024-dim) | Seiten semantisch einbetten |
| **Vektordatenbank** | Supabase pgvector | Vektoren + Metadaten speichern & suchen |
| **LLM Zusammenfassung & Extraktion** | Mistral Large (`mistral-large-latest`) | Zusammenfassungen + Lehrplan-Themen-Extraktion |
| **Frontend** | Streamlit | Bedienoberfläche |
| **Hosting** | Streamlit Cloud | Öffentlich erreichbar, Auto-Deployment via GitHub |

---

## Was funktioniert heute (Stand: 08.03.2026)

**✅ Bücher indexieren** (Tab 1)
- Große PDFs automatisch in 25-Seiten-Batches aufgeteilt (Mistral-Limit: 50 MB)
- OCR → Embedding → Supabase — vollautomatisch, mit Fach-Tagging
- Cache: bereits indexierte Bücher werden übersprungen
- Indexiert: *Klett „Deutsch kompetent EF"* (109 S.) + *Paul D Oberstufe Gesamtband* (315 S.)

**✅ Lehrplan verarbeiten** (Tab 2)
- Lehrplan-PDF hochladen → Mistral erkennt Fach + EF/GK/LK automatisch
- Themen zur Überprüfung mit Checkboxen — vor dem Speichern prüfbar
- Qualitätsmetrik: wie viele von Philipps Excel-Themen hat Mistral gefunden? (Keyword-Matching)
- Cache: bereits verarbeitete PDFs werden aus DB geladen, kein zweiter Mistral-Aufruf
- Verarbeitet: Kernlehrplan Deutsch NRW + Kernlehrplan Mathematik NRW

**✅ Thema abfragen** (Tab 3)
- Dropdown mit allen gespeicherten Themen (Format: `[Fach · EF/GK/LK]`)
- Pinned-Themen (★ rot, Philipps Excel-Auswahl) erscheinen oben
- Fachbasierte Suche: Deutsch-Themen durchsuchen nur Deutsch-Bücher
- Buchauswahl per Checkbox möglich (alle vorgewählt)
- Zusammenfassung mit Seitenverweisen und aufklappbaren Quellseiten
- Cache: Folgeabfragen kosten €0

**✅ Zwei editierbare System-Prompts**
- Extraktions-Prompt (Lehrplan-Tab) — steuert wie Mistral Themen aus dem Lehrplan liest
- Zusammenfassungs-Prompt (Abfrage-Tab) — steuert den Lehrer-Kontext für Zusammenfassungen
- Beide in Supabase gespeichert, bleiben bei App-Neustarts erhalten

**✅ Themenübersicht mit Farbmarkierung**
- ★ Rot — von Philipp in der Excel markiert
- ✓ Grün — im Kernlehrplan gefunden UND in Philipps Excel
- Ohne Markierung — nur im Kernlehrplan

---

## Datenbank-Stand

| Tabelle | Inhalt |
|---|---|
| `documents` | 424 Seiten (109 Klett + 315 Paul D), alle Fach: Deutsch |
| `topics` | 93 Excel-Themen (Deutsch + Mathe, EF/GK/LK) + Lehrplan-Themen Deutsch |
| `summary_cache` | Gecachte Zusammenfassungen (wächst mit jeder Abfrage) |
| `settings` | 2 System-Prompts (Extraktion + Zusammenfassung) |

---

## Erste Testergebnisse

| Thema | Top-Treffer | Ähnlichkeit |
|---|---|---|
| Sprachvarietäten und ihre gesellschaftliche Bedeutung | Seite 100 — Lexikon Sprache | 88% |
| Lyrische Texte: Inhalt, Aufbau, sprachliche Gestaltung | Seite 94 — Gattungslexikon Lyrik | 88% |
| Kommunikationsrollen: Kommunikationsmodelle | Seite 6 — Kommunikationsmodelle | 88% |

Alle drei Testthemen liefern direkte Treffer auf Position 1. Formaler Abnahmetest (Top-10, ≥ 8/10) ausstehend.

---

## Vereinbartes Abnahmekriterium

> Top-10 Retrieval-Ergebnisse für ein Lehrplan-Thema,
> **≥ 8 von 10 Treffern relevant** (binäre Bewertung),
> stabil über mindestens 5 verschiedene Themen.

---

## Kosten (Schätzung)

| Posten | Einmalig | Monatlich |
|---|---|---|
| OCR (gesamtes Korpus ~9.000 Seiten) | ~€18 | — |
| Embeddings (Vollkorpus) | ~€2 | — |
| Zusammenfassungen (103 Themen, dann gecacht) | ~€10 | ~€0 |
| **Gesamt** | **~€30** | **~€0–5** |
""")


# ── Tab 4: How it works ────────────────────────────────────────────────────────
with tab4:
    st.header("Wie funktioniert das System?")

    st.markdown("""
## Die drei Phasen

### 1. Einmalig: Bücher verarbeiten (Tab „Bücher hochladen")

```
PDF hochladen
    → OCR (Mistral liest jede Seite als Text)
    → jede Seite wird in ~1024 Zahlen umgewandelt („Embedding")
    → Zahlen + Text + Fach werden in der Datenbank gespeichert
```

Jede Seite bekommt einen **Zahlenvektor** — eine Art mathematischer Fingerabdruck
des Inhalts. Das passiert nur einmal pro Buch und kostet danach nichts mehr.
Bereits indexierte Bücher werden automatisch übersprungen (Cache).

---

### 2. Einmalig: Lehrplan verarbeiten (Tab „Lehrplan hochladen")

```
Lehrplan-PDF hochladen
    → OCR (Mistral liest den gesamten Lehrplan)
    → Mistral Large erkennt automatisch: Fach + EF / GK / LK
    → Extrahierte Themen werden zur Überprüfung angezeigt
    → Qualitätscheck: wie viele von Philipps Excel-Themen wurden gefunden?
    → Bestätigte Themen werden in der DB gespeichert
```

Bereits verarbeitete Lehrplan-PDFs werden automatisch aus dem Cache geladen — kein
erneuter Mistral-Aufruf nötig. Der Extraktions-Prompt ist editierbar und wird in
Supabase gespeichert.

**Markierungen in der Themenübersicht:**
- ★ Rot — von Philipp in der Excel markiert (höchste Priorität)
- ✓ Grün — im Kernlehrplan gefunden UND in Philipps Excel
- Ohne Markierung — nur im Kernlehrplan, nicht in der Excel

---

### 3. Bei jeder Suche (Tab „Thema abfragen")

```
Thema auswählen
    → wird in Zahlen umgewandelt (Embedding)
    → Vergleich mit allen gespeicherten Seiten-Vektoren (Cosine Similarity)
    → Top-10 ähnlichsten Seiten werden ausgewählt
    → Mistral Large schreibt Zusammenfassung aus diesen 10 Seiten
    → Ergebnis wird gecacht → Folgeabfragen kosten €0
```

Die Suche ist automatisch auf das richtige Fach eingeschränkt — Deutsch-Themen
durchsuchen nur Deutsch-Bücher, Mathe-Themen nur Mathe-Bücher.
Einzelne Bücher können per Checkbox de-/aktiviert werden.

---

## Zwei editierbare System-Prompts

| Prompt | Wo | Zweck |
|---|---|---|
| **Extraktions-Prompt** | Tab „Lehrplan hochladen" → ⚙️ | Steuert wie Mistral Themen aus dem Lehrplan-PDF extrahiert |
| **Zusammenfassungs-Prompt** | Tab „Thema abfragen" → ⚙️ | Steuert wie Mistral die Schulbuch-Auszüge zusammenfasst |

Beide Prompts werden in Supabase gespeichert und überleben App-Neustarts.

---

## Stellschrauben für bessere Qualität

| Maßnahme | Aufwand | Effekt |
|---|---|---|
| **Extraktions-Prompt anpassen** | sofort | Mistral findet mehr / präzisere Themen aus dem Lehrplan |
| **Anzahl Ergebnisse erhöhen** (top_k: 10 → 15) | sofort | Mehr Kontext → vollständigere Zusammenfassungen |
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
""")

