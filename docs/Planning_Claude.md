# Planning Claude – student PRO PDF Retrieval Engine

**Erstellt:** 26.02.2026 | **Aktualisiert:** 26.02.2026
**Kontext:** Projekt startklar, Zahlung ausstehend
**Ziel für Jan:** Eigenständig eine saubere Lösung bauen, die Rachid als "fertig, nichts zu ergänzen" abnimmt.

---

## 1. Was Philipp wirklich braucht

Philipp betreibt **student PRO** – eine Plattform, die Lehrern Unterrichtsinhalte nach NRW-Lehrplan bereitstellt. Er hat bereits eine fertige Lehrer-App (Flutter, PWA + Native), die die Inhalte anzeigt. Was fehlt, ist die **Content-Produktion**: Er muss für jeden Lehrplan-Themen-Eintrag den relevanten Inhalt aus Schulbüchern extrahieren und in die App einspeisen.

**Konkret:**
- ~103 Lehrplan-Themen (Deutsch, Bio, Sozialwissenschaften, weitere Fächer)
- Quellen: 3–6 Schulbücher pro Fach als PDFs (~200 MB, 400–500 Seiten pro Buch)
- Die Bücher enthalten alle Themen gemischt/verstreut – keine klare Struktur pro Thema
- Philipp will per Thema eine kompakte, saubere Zusammenfassung (~10 Seiten) haben
- Diese Zusammenfassungen lädt er manuell in das Admin-Panel seiner App
- **Kein Live-System für Lehrer** – Philipp bedient das Tool allein, einmalig pro Thema

**Das eigentliche Problem ist Retrieval-Präzision:**
- OCR/Parsing funktioniert bereits
- Aktuell ~80% Precision → Ziel: ≥ 80% (Top-10-Ergebnisse, ≥ 8/10 thematisch relevant)
- Philipp ist Fachfremder für die meisten Fächer → er kann fehlerhafte Ergebnisse nicht selbst beurteilen → Präzision ist kritisch

---

## 2. Vereinbarte Lösung (Status Quo)

Laut Mails und Calls wurde folgendes vereinbart:

| Komponente | Details |
|---|---|
| Embeddings | Vektordatenbank in Supabase |
| Retrieval | Semantische Suche + Chain-of-Thought Prompting |
| LLM-Hosting | Mistral (Europa, DSGVO-konform) |
| Export | JSON / CSV |
| Kosten | ~100 EUR/Monat API-Kosten (sinkend) |
| Abnahmekriterium | Top-10 Retrieval, ≥ 8/10 relevant, stabil über mehrere Themen |
| Prototyp | studentpro.lovable.app |
| Experte | Rachid |
| Budget | 4.000 EUR Projekt + 1.200 EUR Support (3 Monate, 4h/Monat) |
| Förderung | Go-to-Market-Gutschein (Förderanforderungen wurden erfüllt) |

---

## 3. Architektur-Optionen: Die drei Wege

### Option A — RAG-Pipeline mit Vektordatenbank (vereinbarte Lösung)
**Was es ist:** Klassisches Retrieval-Augmented Generation Setup. PDFs werden gechunkt, in Embeddings umgewandelt, in Supabase gespeichert. Bei einer Anfrage (Lehrplan-Thema) wird semantisch gesucht, die Top-k Chunks werden an ein LLM gegeben, das eine Zusammenfassung erstellt.

**Stack:**
- PDF-Parsing: LlamaIndex oder Unstructured.io
- Embeddings: Mistral Embed oder OpenAI Ada
- Vektordatenbank: Supabase (pgvector)
- LLM: Mistral Large (Europa-Hosting)
- Interface: einfaches Web-UI oder n8n-Workflow für Philipp

**Pros:**
- Skalierbar – funktioniert auch wenn neue Bücher/Fächer hinzukommen
- Lehrplan-Themen als strukturierte Queries → direkt mappbar
- Kein vollständiges Dokument muss ins Context Window → auch bei 200MB-PDFs stabil
- Rachid hat diese Pipeline bereits mehrfach gebaut (Enterprise-Erfahrung)
- Philipp hat volle Datenkontrolle (Supabase, nur sein Zugang)
- Modell-agnostisch: Backend kann getauscht werden (Mistral → Claude → GPT4 etc.)

**Cons:**
- Chunking-Qualität ist entscheidend – schlechte Chunks = schlechtes Retrieval
- Mehr Infrastruktur-Overhead als einfachere Lösungen
- Initiales Setup komplex; Philipp kann nicht selbst debuggen
- Bei mathematischen Formeln/Tabellen/Grafiken braucht es spezielles Parsing (Mathpix o.ä.)
- Laufende API-Kosten (~100 EUR/Monat)
- Halluzinationsrisiko bei schlechtem Retrieval (falsche Chunks → LLM erfindet)

---

### Option B — Batch-Summarization mit direktem LLM-Kontext (kein RAG)
**Was es ist:** Statt Vektordatenbank werden pro Thema die thematisch relevanten Buchseiten direkt manuell oder regelbasiert ausgewählt und als Volltext in ein LLM mit großem Context Window (z.B. Gemini 1.5 Pro 1M Token, Claude 3.5 mit 200k Token) gegeben. Das LLM fasst direkt zusammen.

**Stack:**
- PDF-Parsing: LlamaIndex / Docling
- Keine Vektordatenbank nötig
- LLM: Gemini 1.5 Pro, Claude 3.5, GPT-4o (je nach Kontext-Größe)
- Interface: n8n-Workflow oder einfaches Python-Script

**Pros:**
- Deutlich einfacher – keine Vektor-Infrastruktur
- Geringeres Halluzinationsrisiko (kompletter Kontext, kein Retrieval-Fehler)
- Für ~103 Themen, einmalig durchgeführt: sehr gut machbar
- Günstiger im Setup
- Kein persistentes System nötig – einmalig ausführen, fertig

**Cons:**
- Skaliert schlecht: Bei 200MB-PDFs / 500 Seiten passt nicht alles ins Context Window
- Philipp kann nicht selbst iterieren – bei neuen Themen/Fächern abhängig von Entwickler
- Teuer pro Run wenn viele Tokens (Gemini 1.5 Pro hat zwar 1M Token aber kostet pro Batch)
- Wenn sich Lehrplan ändert: kompletter Re-run nötig
- Kein strukturiertes Retrieval = keine stabile Qualitätsmessung wie beim vereinbarten Kriterium

---

### Option C — Hybridansatz: Grobe Filterung + Direktes Summarizing
**Was es ist:** Zweistufiger Prozess. Stufe 1: Regelbasierte/semantische Vorfilterung (welche Seiten/Abschnitte könnten relevant sein). Stufe 2: Direktes LLM-Summarizing der gefilterten Seiten (wie Option B, aber mit wesentlich weniger Material).

**Stack:**
- PDF-Parsing + Kapitelstruktur-Extraktion: LlamaIndex
- Grob-Filterung: Keyword-Matching + light Embeddings (kein pgvector nötig, z.B. FAISS lokal)
- LLM für Zusammenfassung: Mistral / Claude
- Interface: n8n oder einfaches Python-UI

**Pros:**
- Kein Datenbankinfrastruktur-Overhead
- Halluzinationsrisiko niedrig (nur relevante Seiten kommen rein)
- Flexibel: Philipp kann Thema eingeben, bekommt gefilterte Seiten + Zusammenfassung
- Günstiger als volles RAG-Setup
- Für 103 Themen, einmalig: realistisch in 2–3 Wochen umsetzbar

**Cons:**
- Weniger skalierbar als Option A
- Wenn Lehrplan sich ändert: teilweise manuell neu konfigurieren
- Qualitätsmessung (Top-10 ≥ 8/10) schwerer zu implementieren ohne sauberes Retrieval

---

## 4. Bewertungsmatrix

| Kriterium | Option A (RAG) | Option B (Batch) | Option C (Hybrid) |
|---|---|---|---|
| Retrieval-Qualität (≥ 80%) | ✅ hoch (wenn gut gebaut) | ⚠️ mittel (kontextabhängig) | ✅ hoch |
| Aufwand Setup | 🔴 hoch | 🟢 niedrig | 🟡 mittel |
| Skalierbarkeit | ✅ sehr gut | ❌ schlecht | 🟡 okay |
| Beherrschbarkeit durch Philipp | 🟡 mit UI okay | 🟢 einfach | 🟡 okay |
| Kosten laufend | 🟡 ~100€/Monat | 🟡 per-run-Kosten | 🟢 gering |
| Risiko Halluzination | 🟡 mittel (retrieval-abhängig) | 🟢 niedrig | 🟢 niedrig |
| Passt zu Förderungsrahmen | ✅ ja | ✅ ja | ✅ ja |
| Bereits vereinbart / Vertrauen | ✅ ja (mit Rachid) | ❌ nein | ❌ nein |
| Zukunftssicher bei Lehrplan-Änderung | ✅ ja | ❌ nein | 🟡 bedingt |

---

## 5. Geklärte Rahmenbedingungen

| Frage | Antwort |
|---|---|
| PDF-Qualität | Text-PDFs, deutsche Schulbücher, einige Grafiken (keine Formel-Bücher) |
| Nutzung | Regelmäßig – neue Bücher sollen immer gegen die 103 Themen zugeordnet werden |
| Interface | Web-UI, kein n8n, möglichst wenige externe Tools |
| Wer baut | Jan – eigenständig, Rachid erst am Ende zur Validation |
| Stand | Greenfield – noch nichts gebaut |

---

## 6. Entscheidung & Technischer Bauplan

**Entscheidung: Option A (RAG + Vektordatenbank)** — weil regelmäßige Nutzung und neue Bücher eine persistente, skalierbare Pipeline zwingend erfordern. Option B/C scheiden aus.

### Empfohlener Stack (minimalistisch, ohne n8n)

```
PDF Upload
    ↓
PDF Parsing (PyMuPDF / Docling)
    ↓
Chunking (semantisch, ~500 Token, 50 Token Overlap)
    ↓
Embedding (Mistral Embed API)
    ↓
Supabase (pgvector) — persistente Vektordatenbank
    ↓
Web-UI (Next.js oder einfaches Python/FastAPI + einfaches HTML-Frontend)
    ↑
Themen-Query (aus 103-Themen-Liste) → Retrieval → Top-10 Chunks
    ↓
LLM Zusammenfassung (Mistral Large / Claude)
    ↓
Export JSON/CSV für App-Upload
```

### Warum diese Komponenten

| Komponente | Tool | Warum |
|---|---|---|
| PDF-Parsing | **PyMuPDF** (fitz) | Schnell, zuverlässig für Text-PDFs, kostenlos, Python-native. Grafiken werden ignoriert/übersprungen. |
| Chunking | **LangChain RecursiveTextSplitter** oder custom | Kein extra Service nötig, läuft lokal im Backend |
| Embeddings | **Mistral Embed** | DSGVO-konform (EU), günstig, bereits im Vertrag mit Philipp vereinbart |
| Vektordatenbank | **Supabase pgvector** | Bereits vereinbart, Philipp hat Kontrolle, kein extra Infrastruktur-Service |
| LLM | **Mistral Large** (Primary) | EU-Hosting, vereinbart. Fallback: Claude Sonnet via API |
| Backend | **FastAPI (Python)** | Einfach, kein Overhead, direkte Integration aller Python-Libs |
| Frontend | **Next.js (React)** oder einfaches **Streamlit** | Streamlit wenn Speed > Design; Next.js wenn es professionell aussehen soll |
| Hosting | **Railway / Render** (Backend) + **Vercel** (Frontend) | Einfachstes Deployment, kein DevOps-Overhead |

### Streamlit vs. Next.js — die wichtigste Interface-Entscheidung

**Streamlit (empfohlen für ersten Launch):**
- Python-only, kein JavaScript nötig
- In 1–2 Tagen ein voll funktionsfähiges UI
- Sieht intern aus, nicht wie ein Produkt — aber Philipp braucht kein Produkt, er braucht ein Werkzeug
- Rachid wird es als pragmatisch und clean anerkennen

**Next.js:**
- Professionelleres Aussehen, aber deutlich mehr Aufwand
- Sinnvoll wenn das Interface später auch anderen gezeigt werden soll
- Empfehlung: erst Streamlit, dann Next.js wenn Philipp es will

---

## 7. System-Architektur im Detail

### 7.1 Datenmodell (Supabase)

```sql
-- Bücher-Tabelle
books (
  id uuid PRIMARY KEY,
  title text,
  subject text,        -- 'deutsch', 'biologie', 'sozialwissenschaften'
  uploaded_at timestamptz,
  page_count int
)

-- Chunks-Tabelle (mit Vektor)
chunks (
  id uuid PRIMARY KEY,
  book_id uuid REFERENCES books(id),
  page_number int,
  chunk_text text,
  embedding vector(1024),    -- Mistral Embed Dimension
  created_at timestamptz
)

-- Themen-Tabelle
topics (
  id uuid PRIMARY KEY,
  subject text,
  topic_name text,           -- z.B. "Lyrik", "Zellbiologie"
  grade_level text           -- z.B. "Oberstufe", "Klasse 10"
)

-- Ergebnisse (gecachte Retrieval-Ergebnisse)
results (
  id uuid PRIMARY KEY,
  topic_id uuid REFERENCES topics(id),
  summary_text text,
  top_chunks jsonb,          -- die Top-10 Chunk-IDs + Scores
  created_at timestamptz,
  approved boolean DEFAULT false
)
```

### 7.2 Die drei Kernfunktionen der Web-UI

**1. Buch hochladen & indexieren**
- Philipp zieht eine PDF rein
- System parst, chunked, embeddet → alles landet in Supabase
- Progress-Bar, fertig

**2. Thema abfragen**
- Philipp wählt ein Thema aus der Dropdown-Liste (103 Themen)
- System retrievet Top-10 Chunks, zeigt sie an
- Philipp sieht: welche Buchseiten wurden gefunden, Relevanz-Score
- Drückt "Zusammenfassung generieren" → LLM schreibt Summary
- Kann Summary editieren, dann "Exportieren" (JSON/CSV)

**3. Qualitäts-Check (Abnahme-Ansicht)**
- Für ein Thema: alle Top-10 Chunks werden angezeigt
- Philipp markiert 1 (relevant) oder 0 (nicht relevant)
- System zeigt Precision-Score live an → direkt das Abnahmekriterium messbar

### 7.3 Chunking-Strategie für Schulbücher

Schulbücher haben typisch: Kapitel → Unterkapitel → Absätze + Infokästen + Marginalien

```
Chunk-Size: 400–600 Token
Overlap: 50–100 Token (damit Kontext über Seitengrenzen nicht verloren geht)
Metadaten je Chunk: Buch-ID, Seitenzahl, Kapitelüberschrift wenn erkennbar
```

Grafiken: PyMuPDF extrahiert nur Text → Grafiken werden ignoriert, Bildunterschriften bleiben erhalten. Das ist für diesen Use Case akzeptabel.

### 7.4 Retrieval-Verbesserungen (damit ≥ 80% erreicht werden)

Standard-RAG allein reicht oft nicht. Folgende Techniken machen den Unterschied:

1. **Hybrid Search:** Semantische Suche (Embeddings) + Keyword-Suche (BM25) kombiniert. Supabase unterstützt das nativ mit `ts_rank`. Bei Fachjargon (z.B. "Enjambement" bei Lyrik) schlägt Keyword oft Semantik.

2. **Query Expansion:** Bevor retrievt wird, lässt man das LLM das Thema in 3–5 Synonyme/verwandte Begriffe expandieren. Erhöht Recall deutlich.

3. **Re-Ranking:** Nach initialem Retrieval (Top-20) nochmal mit einem Cross-Encoder oder einfachem LLM-Prompt re-ranken → die tatsächlich besten 10 behalten.

4. **Chunk-Eltern-Kontext:** Kleiner Chunk für Retrieval, aber beim Summarizing den ganzen Absatz/die ganze Seite mitgeben. LangChain nennt das "Parent Document Retriever".

---

## 8. Umsetzungsplan (Jan baut alleine)

### Phase 0 — Setup (Tag 1–2)
- [ ] Supabase-Projekt anlegen, pgvector Extension aktivieren
- [ ] Mistral API-Key besorgen
- [ ] Python-Environment: `pip install fastapi pymupdf langchain supabase mistralai streamlit`
- [ ] Datenbank-Schema anlegen (SQL oben)
- [ ] Test: Ein Buch parsen, 10 Chunks embedden, in Supabase speichern

### Phase 1 — Kern-Pipeline (Tag 3–7)
- [ ] PDF-Upload + Parsing (PyMuPDF)
- [ ] Chunking (LangChain RecursiveTextSplitter)
- [ ] Embedding-Loop (Mistral Embed, batched)
- [ ] Retrieval-Funktion (Supabase `match_documents` mit pgvector)
- [ ] LLM-Summarization (Mistral Large, Prompt auf Deutsch)
- [ ] JSON-Export

### Phase 2 — Web-UI (Tag 8–12)
- [ ] Streamlit-App mit 3 Seiten:
  - "Buch hochladen" (Drag & Drop PDF → Progress)
  - "Thema abfragen" (Dropdown 103 Themen → Top-10 anzeigen → Summary → Export)
  - "Qualitäts-Check" (Binäre Bewertung 1/0, Precision anzeigen)
- [ ] Deployment auf Railway (Backend) oder als reines Streamlit-App auf Streamlit Cloud

### Phase 3 — Qualitäts-Tuning (Tag 13–17)
- [ ] Hybrid Search implementieren (BM25 + Embedding)
- [ ] Query Expansion einbauen
- [ ] An 5 Deutsch-Themen testen → Precision messen
- [ ] Chunk-Größe iterativ optimieren bis ≥ 8/10

### Phase 4 — Rachid Validation (Tag 18–21)
- [ ] Laufendes System, Dokumentation, Retrieval-Scores vorlegen
- [ ] Rachid einladen für Code-Review
- [ ] Offene Punkte addressieren

---

## 9. Risiken

| Risiko | Wahrscheinlichkeit | Mitigation |
|---|---|---|
| Schulbuch-PDFs haben Schutzkopier-Sperre | mittel | Frühzeitig ein PDF testen: `pymupdf` gibt Warning wenn DRM aktiv |
| Chunking zerschneidet Themen-Kontext | hoch | Parent-Document-Retriever + großzügiger Overlap |
| Mistral Embed hat schwache Qualität für Deutsch | mittel | A/B-Test gegen OpenAI Ada, Fallback vorbereiten |
| Precision ≥ 80% wird nicht erreicht | mittel | Hybrid Search + Re-Ranking als Eskalationsstufe |
| Jan steckt bei spezifischem Tech-Problem fest | hoch | Claude als Pair-Programmer; Rachid erst für finale Validation |

---

## 10. Offene Fragen an Philipp (nach Zahlungseingang klären)

1. Kannst du ein Muster-PDF schicken (z.B. ein Deutschbuch) zum Testen des Parsings?
2. Gibt es die 103 Themen bereits als strukturierte Liste (Excel/CSV) oder nur als PDF-Lehrplan?
3. Welches Fach/Thema soll als erstes getestet werden für die Abnahme?

---

## 11. Sofortiger Startplan (ohne Philipp, ohne PDFs)

**Situation:** Keine PDFs vorhanden, neues Supabase-Projekt, Python-Erfahrung vorhanden.
**Strategie:** System komplett mit öffentlich verfügbarem Beispiel-Material bauen und validieren. Wenn Philipp zahlt und PDFs liefert, wird nur der Content ausgetauscht — die Pipeline steht bereits.

### Schritt 1 — Supabase + Umgebung (heute, ~1h)
- Supabase-Projekt anlegen (kostenloser Plan reicht)
- pgvector Extension aktivieren: `CREATE EXTENSION IF NOT EXISTS vector;`
- Schema anlegen (SQL aus Abschnitt 7.1)
- `.env`-Datei mit `SUPABASE_URL`, `SUPABASE_KEY`, `MISTRAL_API_KEY`
- `pip install pymupdf langchain langchain-community supabase mistralai streamlit python-dotenv`

### Schritt 2 — Testdaten: öffentlicher NRW-Lehrplan als PDF
- NRW Kernlehrpläne sind öffentlich verfügbar auf schulministerium.nrw.de
- Diese PDFs **dürfen** verarbeitet werden (öffentliche Dokumente)
- Damit kann die gesamte Pipeline getestet werden: Parsing → Chunking → Embedding → Retrieval
- Vorteil: genau das richtige Vokabular (Fachbegriffe, Themen-Namen) wie später in den Schulbüchern

### Schritt 3 — Pipeline bauen in dieser Reihenfolge
1. `parse_pdf.py` — PyMuPDF, gibt Liste von `{page: int, text: str}` zurück
2. `chunk.py` — LangChain RecursiveCharacterTextSplitter, gibt Chunks mit Metadaten zurück
3. `embed_and_store.py` — Mistral Embed API, speichert Vektoren in Supabase
4. `retrieve.py` — Supabase `match_documents` RPC-Funktion, gibt Top-k Chunks zurück
5. `summarize.py` — Mistral Large Prompt auf Deutsch, gibt Zusammenfassung zurück
6. `app.py` — Streamlit-UI, verbindet alles

### Schritt 4 — Themen-Liste
- NRW Deutsch-Lehrplan Oberstufe hat ~30 Themen → als `topics.json` anlegen
- Diese Themen direkt in die Supabase `topics`-Tabelle eintragen
- Dropdown in der UI speist sich daraus

### Was am Ende steht (ohne Philipp)
Ein vollständig laufendes System auf echten NRW-Lehrplan-PDFs, das das Abnahmekriterium (Top-10, ≥ 8/10) bereits erfüllt oder sehr nah dran ist. Wenn Philipp dann Schulbuch-PDFs liefert: Upload-Funktion nutzen, fertig.

---

## 12. Wie du die nächste Projektplanung mit Claude verbesserst

*Rückblick nach Projektabschluss (März 2026). Was hätte die Zusammenarbeit noch effizienter gemacht?*

---

### 1. Entscheidungen sofort schriftlich festhalten

Wenn in einem Call eine Entscheidung fällt — z.B. "wir nutzen DOCX statt JSON" — schreib sie direkt ins Planungsdokument bevor du Claude damit beauftragst. Claude hat kein Gedächtnis über Sessions hinaus. Wenn der Kontext explizit im Dokument steht, muss er nicht aus dem Gesprächsverlauf rekonstruiert werden, und Claude kann sofort in die richtige Richtung arbeiten.

**Formulierung die funktioniert:** "Entscheidung: Export-Format ist DOCX. JSON kommt später wenn die Admin-Panel-API klar ist."

---

### 2. Das "Warum" mitliefern, nicht nur das "Was"

Claude generiert bessere Lösungen wenn es den Kontext kennt. Statt "füge einen Löschen-Button hinzu" lieber: "füge einen Löschen-Button hinzu, weil falsch indexierte Bücher entfernt werden können sollen ohne Datenbankzugriff."

Der Grund dahinter: ohne das Warum wählt Claude die technisch einfachste Lösung. Mit dem Warum wählt Claude die Lösung die zum tatsächlichen Bedarf passt.

---

### 3. Ablehnungen begründen

Wenn Claude etwas vorschlägt das du nicht willst, sag warum. "Fingerabdruck gefällt mir nicht weil ein 12-Jähriger das nicht versteht" gibt Claude eine konkrete Einschränkung die es beim nächsten Vorschlag anwendet. "Gefällt mir nicht" allein erzeugt eine Schleife ohne Fortschritt.

**Faustregel:** Jede Ablehnung = ein Satz der erklärt was fehlt oder was nicht passt.

---

### 4. Architekturentscheidungen früh und explizit treffen

Die wichtigste Architekturfrage in diesem Projekt — "alles in einer Datei (`app_Claude.py`) vs. aufgeteilt in Module" — wurde nie explizit entschieden. Es passierte einfach so. Das ist akzeptabel für einen MVP, aber es bedeutete dass spätere Diskussionen ("sollten wir jetzt splitten?") ohne Grundlage stattfanden.

Beim nächsten Projekt: am Anfang explizit entscheiden und dokumentieren. "Wir bleiben bewusst in einer Datei bis X." Dann ist die Entscheidung klar und kann re-evaluiert werden wenn X eintritt.

---

### 5. Scope-Erweiterungen als bewusste Entscheidungen behandeln

In diesem Projekt wuchs der Scope organisch: Lehrplan-Upload, Beispieldokumente, Cost Tracking, DOCX Export — alles wertvolle Ergänzungen, aber keine wurden als formale Scope-Änderungen dokumentiert. Das Ergebnis: der Akzeptanztest wurde immer wieder verschoben weil immer noch etwas "fehlte".

Für das nächste Projekt: wenn eine neue Funktion hinzukommt, kurz verschriftlichen — "Scope-Erweiterung: wir fügen X hinzu, weil Y. Aufwand: ~Z Stunden. Akzeptanztest verschiebt sich entsprechend."

---

### 6. Claude als Planungspartner nutzen, nicht nur als Code-Produzent

Claude kann in der Planungsphase mehr tun als nur Code schreiben:
- **Architektur-Review**: "Hier ist mein geplantes Datenmodell. Was fehlt? Was wird sich ändern?"
- **Risiko-Identifikation**: "Hier ist mein Plan. Was kann schiefgehen?"
- **Anforderungs-Interview**: "Ich habe ein neues Projekt. Stelle mir die Fragen die ich vergessen haben könnte."

Diese Art der Planung vor dem ersten `git commit` spart mehr Zeit als alles andere.

---

## 13. Allgemeine Konzepte (Entscheidungsgrundlagen)

---

### Warum RAG die richtige Wahl war — und wann sie es nicht wäre

RAG (Retrieval-Augmented Generation) war hier richtig weil:
- Die Bücher zu groß für direkte LLM-Verarbeitung sind (200MB, 500+ Seiten)
- Das System regelmäßig genutzt wird — einmal indexieren, viele Abfragen
- Das Abnahmekriterium messbar sein musste (Top-10, ≥ 8/10)

RAG wäre die **falsche** Wahl wenn:
- Die Datenmenge klein ist (< 50 Seiten) → direkt ins Context Window
- Es ein einmaliger Run ist (nicht wiederkehrend) → Batch-Summarization
- Exakte Volltext-Übereinstimmung wichtiger ist als semantische Ähnlichkeit → reines BM25

---

### Was Chunking ist und warum die Größe wichtig ist

Ein "Chunk" ist ein Textabschnitt der als Einheit gespeichert und abgerufen wird. Zu groß = der Chunk enthält zu viel Nicht-Relevantes, das die Ähnlichkeitsberechnung verwässert. Zu klein = wichtiger Kontext wird abgeschnitten.

Der Kompromiss in diesem Projekt: 1500 Zeichen mit 200 Zeichen Overlap. Das entspricht ~250-300 Wörtern — genug Kontext für einen zusammenhängenden Gedanken, klein genug für präzise Retrieval.

Die **200 Zeichen Overlap** stellen sicher: ein Satz der über eine Chunk-Grenze geht, erscheint in beiden Chunks. Ohne Overlap würden Schlüsselaussagen die zufällig an einer Grenze landen, in keinem Chunk vollständig sein.

---

### Was Cosinus-Ähnlichkeit ist

Wenn zwei Texte verglichen werden, hat jeder einen Vektor — eine Liste von 1024 Zahlen. Cosinus-Ähnlichkeit misst den Winkel zwischen diesen Vektoren:
- **1.0** = gleiche Bedeutung
- **0.5** = verwandt
- **0.0** = keine Verbindung

Der `<=>` Operator in Supabase (pgvector) berechnet genau diese Distanz. "Top-10 Ergebnisse" bedeutet: die 10 Chunks mit dem kleinsten Winkel zum Suchbegriff.

---

### Was der Unterschied zwischen semantischer Suche und Keyword-Suche ist

| | Semantische Suche | Keyword-Suche (BM25) |
|---|---|---|
| Findet | Bedeutungs-Ähnliches | Exakte Wortübereinstimmungen |
| Stärke | "Lyrik" findet auch "Gedicht, Strophe" | "Enjambement" findet genau "Enjambement" |
| Schwäche | Kann thematisch Ähnliches mit zu wenig Treffsicherheit liefern | Findet nichts wenn der Fachbegriff nicht im Text steht |
| Einsatz | Standard-Abfragen | Fachterminologie, seltene Begriffe |

Hybrid Search kombiniert beide: semantisch für den Grundabruf, BM25 für Re-Scoring. Das ist der geplante nächste Qualitätssprung.
