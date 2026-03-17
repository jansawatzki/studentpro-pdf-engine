# Design Guide — student PRO PDF Retrieval Engine

**Version:** 1.2 | **Created:** 2026-03-04 | **Last updated:** 2026-03-17 | **Owner:** Jan

---

## 0. Current State (as of 2026-03-17) — LIVE

The live app has **6 tabs**. Sections 1–10 below describe design patterns still in use. The planned 4-tab layout in Section 3 is superseded by the current structure:

```
📚 Bücher hochladen | 📄 Lehrplan hochladen | 📝 Beispiele hochladen | 🔍 Thema abfragen | 📋 Projektübersicht | ❓ Wie funktioniert es?
```

Current live features beyond the original design:
- **Delete buttons** on all three content tabs (books, Lehrplan PDFs, examples)
- **DOCX export** — download button after every summary (cached + fresh)
- **Style references** — uploaded example documents are always used as style input for Mistral Large
- **Cost display** — live cost breakdown (embed + chat) shown after each fresh generation
- **Richer spinners** — show which books are being searched, which examples are available

Colour signals:
- `#ff4b4b` red badge — pinned topics (★)
- `#21a354` green badge — topics in both Excel and Kernlehrplan (✓)
- `st.info` blue — cache-hit banners ("💾 Aus Cache geladen")
- `st.success` green — fresh generation banner ("✅ Neu generiert")

---

## 1. Design Philosophy

This is a **private internal workbench**, not a consumer product. Design decisions prioritize:

1. **Clarity over beauty** — Philipp needs to trust the output, not be wowed by the interface
2. **Transparency** — always show where data came from (book, page number, score)
3. **Minimal friction** — fewest clicks from intent to export
4. **German throughout** — all labels, messages, and generated text in German

Do not over-engineer aesthetics. Streamlit defaults are acceptable. The goal is a tool that Rachid reviews and calls "clean and professional."

---

## 2. Language

**All UI text is in German.** No English labels, placeholders, or error messages exposed to Philipp.

| Element | German | English (dev reference only) |
|---|---|---|
| Upload button | "PDF hochladen" | Upload PDF |
| Process button | "Buch verarbeiten" | Process book |
| Search label | "Thema auswählen" | Select topic |
| Search button | "Relevante Inhalte abrufen" | Retrieve content |
| Generate button | "Zusammenfassung erstellen" | Generate summary |
| Export JSON | "Als JSON exportieren" | Export as JSON |
| Export CSV | "Als CSV exportieren" | Export as CSV |
| Relevant | "✓ Relevant" | Relevant |
| Not relevant | "✗ Nicht relevant" | Not relevant |
| Progress | "Seite X von Y wird verarbeitet..." | Processing page X of Y |
| Success | "Verarbeitung abgeschlossen — X Seiten indexiert." | Done |
| No results | "Keine relevanten Inhalte gefunden." | No results found |
| Warning (precision) | "Achtung: Weniger als 8 von 10 Treffern sind relevant." | Warning: precision below threshold |

---

## 3. Layout & Structure

### Page config
```python
st.set_page_config(
    page_title="student PRO — Inhalts-Engine",
    layout="wide",
    initial_sidebar_state="collapsed",
)
```

### Navigation: 4 tabs (Streamlit `st.tabs`)

```
[📚 Bücher verwalten] [🔍 Thema abfragen] [⭐ Qualität prüfen] [📤 Exportieren]
```

Tab 1 — Bücher verwalten (Book Management)
Tab 2 — Thema abfragen (Topic Query)
Tab 3 — Qualität prüfen (Quality Rating)
Tab 4 — Exportieren (Export)

The 4-tab layout keeps each major workflow in its own context without requiring a multi-page app.

---

## 4. Tab Layouts

### Tab 1 — Bücher verwalten

```
┌─────────────────────────────────────────────────────────┐
│  Neues Buch hochladen                                   │
│  ┌────────────────────────────────────────────┐         │
│  │  PDF hierher ziehen oder klicken           │         │
│  └────────────────────────────────────────────┘         │
│                                                         │
│  Buchtitel: [________________]                          │
│  Fach:      [Deutsch ▼]                                 │
│                                                         │
│  [Buch verarbeiten]                                     │
│  ████████████░░░░  Seite 47 von 120 wird verarbeitet... │
│                                                         │
├─────────────────────────────────────────────────────────┤
│  Indexierte Bücher                                      │
│  Buch                   Fach       Seiten  Datum        │
│  ─────────────────────────────────────────────────      │
│  Deutschbuch Kl. 10     Deutsch    498     01.03.2026   │
│  Lesebuch Oberstufe     Deutsch    312     02.03.2026   │
└─────────────────────────────────────────────────────────┘
```

### Tab 2 — Thema abfragen

```
┌─────────────────────────────────────────────────────────┐
│  Fach: [Deutsch ▼]   Thema: [Lyrik – Oberstufe ▼]      │
│                                                         │
│  [Relevante Inhalte abrufen]                            │
│                                                         │
├─────────────────────────────────────────────────────────┤
│  Top-10 Treffer                                         │
│                                                         │
│  #1  Deutschbuch Kl. 10 — Seite 47   [97% Relevanz]    │
│  "Das Sonett ist eine lyrische Form mit 14 Versen..."   │
│                                                         │
│  #2  Lesebuch Oberstufe — Seite 203  [94% Relevanz]     │
│  "Reimschema und Metrum sind zentrale Merkmale..."      │
│  ...                                                    │
│                                                         │
│  [Zusammenfassung erstellen]                            │
└─────────────────────────────────────────────────────────┘
```

### Tab 3 — Qualität prüfen

```
┌─────────────────────────────────────────────────────────┐
│  Thema: Lyrik – Oberstufe          Präzision: 8/10 ✓   │
│                                                         │
│  #1  Deutschbuch Kl. 10 — Seite 47                     │
│  "Das Sonett ist eine lyrische Form..."                 │
│  [✓ Relevant]  [✗ Nicht relevant]                       │
│                                                         │
│  #2  Lesebuch Oberstufe — Seite 203                    │
│  "Reimschema und Metrum sind..."                        │
│  [✓ Relevant]  [✗ Nicht relevant]                       │
│  ...                                                    │
└─────────────────────────────────────────────────────────┘
```

### Tab 4 — Exportieren

```
┌─────────────────────────────────────────────────────────┐
│  Thema: Lyrik – Oberstufe                               │
│                                                         │
│  Zusammenfassung (bearbeitbar):                         │
│  ┌─────────────────────────────────────────────────┐   │
│  │ Das Thema Lyrik umfasst folgende Kernaspekte:   │   │
│  │ ...                                             │   │
│  └─────────────────────────────────────────────────┘   │
│                                                         │
│  [📄 Als JSON exportieren]  [📊 Als CSV exportieren]    │
└─────────────────────────────────────────────────────────┘
```

---

## 5. Component Patterns

### Progress during processing
Use `st.progress()` with descriptive text. Never leave Philipp staring at a spinner with no information.
```python
progress = st.progress(0, text="Starte Verarbeitung...")
# update on each page
progress.progress(n/total, text=f"Seite {n} von {total} wird verarbeitet...")
```

### Chunk display card
Each retrieved chunk is displayed as an `st.expander` with:
- Header: `{book_title} — Seite {page_number}  ({similarity:.0%} Relevanz)`
- Body: first 500 chars of content, truncated with "..."
- Rating buttons (in quality tab only)

### Precision badge
```
≥ 8/10  →  green badge   "8 von 10 relevant ✓"
< 8/10  →  orange badge  "6 von 10 relevant — Schwellenwert nicht erreicht ⚠️"
```

### Error messages
Always in German, always actionable:
- "Das Buch konnte nicht verarbeitet werden. Bitte prüfen Sie, ob die PDF-Datei nicht geschützt ist."
- "Keine Treffer gefunden. Versuchen Sie ein allgemeineres Stichwort."
- "Verbindungsfehler. Bitte Seite neu laden."

---

## 6. Color Usage (Streamlit defaults)

Streamlit's default light theme is used without customization. The only color signals added:

| Signal | Color | Use case |
|---|---|---|
| Success | Green (`st.success`) | Indexing complete, export done |
| Warning | Orange (`st.warning`) | Precision below 80% |
| Error | Red (`st.error`) | API failure, unreadable PDF |
| Info | Blue (`st.info`) | Neutral status updates |

No custom CSS unless Streamlit defaults are clearly insufficient.

---

## 7. Typography

Streamlit default fonts. No overrides needed.

Text hierarchy:
- `st.title` — page title only
- `st.header` — section headers within a tab
- `st.subheader` — sub-sections
- `st.markdown` — body text, summary display
- `st.caption` — metadata (date, token count, cost estimate)

---

## 8. Responsive Behavior

The app is **desktop-only**. Philipp uses this at a desk. No mobile optimization required.

Minimum viable viewport: 1280 × 800 px.

Use `st.columns([1, 2])` for side-by-side layouts (e.g., filter controls + results).

---

## 9. Accessibility

- All buttons have descriptive labels (no icon-only buttons)
- Error and warning states use both color and text/icon
- Tab titles use emoji as visual aid, not as sole indicator
- No time-limited interactions (no auto-dismiss toasts)

---

## 10. Future Design Upgrade (Next.js)

If Philipp later wants a production-grade UI:
- Move to Next.js + Tailwind CSS
- student PRO brand colors (to be provided by Philipp)
- Consistent card components for chunk display
- Persistent sidebar navigation instead of tabs
- The backend API endpoints remain identical — only the frontend changes

Until that decision is made, Streamlit is the correct tool.
