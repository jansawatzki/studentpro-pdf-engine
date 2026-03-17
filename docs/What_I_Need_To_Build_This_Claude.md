# What I Need From You to Build This Project

This file tells you exactly what questions you need to answer and what materials you need to gather before I can build the full student PRO PDF Retrieval Engine with Mistral OCR.

Everything is grouped by who needs to provide it and how urgent it is.

---

## Part 1 — Accounts & API Keys
*You need these before I can write a single line of working code.*

| What | Where to get it | Notes |
|---|---|---|
| **Mistral API Key** | platform.mistral.ai | Needs access to `mistral-ocr-latest` + `mistral-embed-latest` + `mistral-large-latest` |
| **Supabase Project URL** | supabase.com → your project → Settings → API | Looks like `https://xxxx.supabase.co` |
| **Supabase Anon Key** | Same page as above | Public key, used in the frontend |
| **Supabase Service Role Key** | Same page, keep this secret | Used in the backend only |

**Question for you:** Do these accounts already exist, or do I need to walk you through creating them?

---

## Part 2 — Inputs From Philipp
*These come from Philipp. You need to ask him for them at the kickoff call.*

### 2.1 The School Book PDFs
- **How many PDFs** does he have right now and for which subjects?
- Are they **text-native PDFs** (born digital) or **scanned** (photographed pages)?
- Can he share **2–3 sample PDFs** immediately for me to build and test against?
- Are any of the PDFs **DRM-protected / copy-locked**? (Mistral OCR cannot process those)

### 2.2 The 103 Topics List
- Does this list exist as a **structured file** (Excel, CSV) or only as a PDF?
- What columns does it have? At minimum I need: **Subject · Topic Name · Grade Level**
- If it's only a PDF, can he export it or type it out? I will need it as a structured file to build the dropdown menu in the UI.

### 2.3 The Pilot Topics
- Which **3–5 specific topics** should be used for the first quality test?
- For each pilot topic: which **book(s)** should be searched?
- Who will do the **binary relevance rating** (1 = relevant, 0 = not relevant) on the Top-10 results — Philipp himself, or a subject expert?

### 2.4 The Output Document
- What exactly should the **downloadable document** contain per topic?
  - Option A: Raw extracted pages (what OCR found, no rewriting)
  - Option B: A clean summary written by the LLM, citing the source pages
  - Option C: Both — summary on top, raw pages attached as appendix
- What **file format** does Philipp want to download?
  - PDF
  - Word (.docx)
  - Markdown / HTML
- Does every output page need a **source reference** (e.g. "Book: Deutschbuch Klasse 10, Page 47")?

---

## Part 3 — Product Decisions
*You and Rachid decide these. They shape how the UI is built.*

### 3.1 The User Interface
- Should Philipp be able to **type a free topic** or only **select from a dropdown** of the 103 predefined topics?
- Should the UI show Philipp the **individual extracted pages** before he downloads, so he can deselect irrelevant ones manually?
- Does the UI need a **login / password** or is it internal-only with no auth?
- What language should the UI be in — **German or English**?

### 3.2 The Books
- Should Philipp be able to **upload new books himself** through the UI, or will you upload them for him on the backend?
- Should the system support **multiple books per topic query** (search across 3 books simultaneously) or one book at a time?

### 3.3 Quality Control
- Do you want to keep the **binary rating screen** (1/0 per chunk) inside the UI so Philipp can formally sign off on quality?
- Or is quality reviewed by you and Rachid separately before handing it to Philipp?

---

## Part 4 — Technical Decisions
*These are your calls as the developer.*

| Decision | Options | My Recommendation |
|---|---|---|
| **Frontend framework** | Streamlit (fast) or Next.js (polished) | Streamlit first, switch later if Philipp wants it to look like a product |
| **Backend hosting** | Railway, Render, or local-only for now | Railway — simple deployment, no DevOps overhead |
| **PDF splitting** (books are ~200MB, OCR limit is 50MB) | Split into 100-page batches automatically | Yes, handle this automatically — transparent to Philipp |
| **Embedding model** | `mistral-embed-latest` | Confirmed — DSGVO-compliant, EU-hosted |
| **LLM for compilation** | `mistral-large-latest` | Confirmed — EU-hosted, already in contract |
| **Retrieval approach** | Hybrid: Mistral Embed (semantic) + BM25 (keyword) | Both — semantic alone is not enough for German technical terms |

---

## Part 5 — The One Question That Changes Everything

**How many total pages will Philipp process across all subjects and books?**

Rough estimate:
- 6 books × 500 pages = 3,000 pages per subject
- 3 subjects = ~9,000 pages total

At $2 per 1,000 pages → **~$18 one-time OCR cost** for the entire corpus. That's negligible.

But I need to confirm this with you so I can give Philipp an honest cost estimate.

---

## Summary — Your Checklist Before I Start Building

### You need to do right now:
- [ ] Create Mistral account + get API key (with OCR access)
- [ ] Create Supabase project + copy URL + keys
- [ ] Decide: Streamlit or Next.js for first version?
- [ ] Decide: login/auth required or not?

### You need from Philipp (kickoff call):
- [ ] 2–3 sample PDFs for testing
- [ ] 103 topics as Excel/CSV
- [ ] 3–5 pilot topics named explicitly
- [ ] Preferred output format (PDF / Word / Markdown)
- [ ] Confirmation: are any PDFs DRM-locked?

### Once I have all of the above:
I can build the complete working system. No blockers.

---

## Wie du die Anforderungsphase beim nächsten Projekt besser gestaltest

*Rückblick nach Projektabschluss (März 2026). Was hätte diese Phase effizienter gemacht?*

---

### 1. Output zuerst definieren — dann Input

Die wichtigste Frage in diesem Projekt kam zu spät: "In welchem Format soll die Zusammenfassung heruntergeladen werden?" Das bestimmt alles andere — welche Tabellen du brauchst, welche APIs, welche UI-Komponenten.

Beim nächsten Projekt: Beschreibe zuerst das fertige Endprodukt aus Nutzersicht. "Der Nutzer klickt hier, bekommt das, speichert es dort." Dann rückwärts planen was dafür gebaut werden muss.

---

### 2. "Was ist der teuerste Fehler wenn ich das nicht frage?"

Für jede Zeile in diesem Dokument hätte man diese Frage stellen können. Das Ergebnis wäre eine priorisierte Liste gewesen statt einer gleichwertigen Checkliste.

Beispiel: "Sind die PDFs DRM-geschützt?" — wenn ja, ist das gesamte Projekt unbaubar. Das ist die wichtigste Frage in Part 2 und sollte ganz oben stehen, nicht irgendwo in der Mitte. Beim nächsten Anforderungsdokument: sortiere nach "was blockiert alles andere?"

---

### 3. Akzeptanzkriterien als prüfbare Sätze formulieren

"≥ 8/10 relevant" wurde in diesem Projekt früh vereinbart — das ist gut. Das Problem war, dass "relevant" nie definiert wurde. Wer bewertet? Nach welchen Kriterien? Was passiert wenn das Ergebnis 7/10 ist?

Bessere Formulierung: "Das Projekt ist abgenommen wenn [Wer] [Was konkret tut] und [Messbares Ergebnis] eintritt. Bei < 8/10 wird [Eskalationspfad] eingeschlagen."

---

### 4. Claude als Interviewer nutzen

Statt selbst eine Anforderungsliste zu schreiben, kannst du Claude damit beauftragen. Formulierung die gut funktioniert:

> "Ich plane ein neues Projekt: [1-2 Sätze Beschreibung]. Stelle mir die Fragen die ich beantworten muss bevor wir mit dem Bau beginnen. Priorisiere nach: was blockiert alles andere, was verursacht die teuersten Fehler wenn unklar."

Claude kennt häufige Fallstricke bei ähnlichen Projekten und fragt nach Dingen die du vergessen hast — Authentifizierung, Export-Format, Fehlerszenarien, Skalierung.

---

### 5. Technische Entscheidungen von Produktentscheidungen trennen

Dieses Dokument mischt beides — was Philipp braucht (Produkt) mit welche Technologie dafür (Technik). Das ist für ein einzelnes Projekt okay, erschwert aber die spätere Wiederverwendung.

Für das nächste Projekt: zwei separate Abschnitte. "Was braucht der Nutzer?" ist eine Frage für den Kunden. "Wie bauen wir das?" ist eine Frage für dich und Claude.

---

## Allgemeine Konzepte (Anforderungsphase)

---

### Was Requirements Engineering ist

Requirements Engineering ist die Disziplin, aus vagen Wünschen messbare Anforderungen zu machen.

- **Vage Anforderung:** "Ich will eine App die relevante Schulbuchinhalte findet."
- **Messbare Anforderung:** "Für jeden der 103 Lehrplan-Themen liefert die App eine Liste von mindestens 10 Buchseiten, von denen ≥ 8 als thematisch relevant bewertet werden."

Der Unterschied: die messbare Anforderung sagt dir wann das Projekt fertig ist. Die vage Anforderung nie.

---

### Was "Scope Creep" ist und warum er passiert

Scope Creep bedeutet: ein Projekt wächst über seinen ursprünglichen Rahmen hinaus, ohne dass Kosten, Zeit oder Qualitätsziele angepasst werden.

In diesem Projekt: das Original-Scope war "OCR → embed → search → summary". Lehrplan-Upload, Beispieldokumente, Cost Tracking, DOCX Export — alles sinnvolle Ergänzungen, alle nicht im ursprünglichen Scope. Das Ergebnis: der Akzeptanztest verzögerte sich, weil immer noch etwas "fehlte."

Scope Creep ist nicht per se schlecht. Schlechte Features die keinen Wert liefern sind schlecht. Der Unterschied: wenn eine Erweiterung bewusst entschieden und dokumentiert wird, bleibt der Überblick erhalten. Wenn sie einfach passiert, verliert man den Bezug zum ursprünglichen Ziel.

---

### Warum der Akzeptanztest vor der Implementierung vereinbart werden muss

Wenn das Abnahmekriterium erst nach dem Bau festgelegt wird, passt es sich dem an was gebaut wurde — nicht dem was gebraucht wird. Das nennt sich "moving the goalposts."

In diesem Projekt war "≥ 8/10" von Anfang an klar und schriftlich vereinbart. Das verhinderte, dass schlechtere Ergebnisse als "gut genug" abgenommen wurden.

---

### Was ein MVP ist (und was es nicht ist)

MVP = Minimum Viable Product. Die kleinste Version eines Produkts die echten Wert für den Nutzer liefert und die Kernhypothese testet.

In diesem Projekt war der MVP: ein Buch indexieren + ein Thema abfragen + Ergebnis anzeigen. Alles andere (Caching, Lehrplan-Upload, Export) sind wertvolle Ergänzungen, aber nicht der MVP.

Die Frage "ist das MVP?" ist ein gutes Werkzeug gegen Scope Creep: wenn die Antwort nein ist, ist die Erweiterung optional und sollte bewusst entschieden werden.
