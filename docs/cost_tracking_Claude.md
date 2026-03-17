# Cost Tracking — student PRO PDF Engine

---

## Die drei Kostenarten

| | Wofür | Wann | Mistral-Modell | Wie gemessen |
|---|---|---|---|---|
| **1. OCR** | Buch lesen (Bild → Text) | einmalig beim Hochladen | `mistral-ocr-latest` | Seiten aus `ocr_response.pages` |
| **2. Steckbrief** | Text → Zahlenmuster | einmalig beim Hochladen | `mistral-embed` | Tokens aus `emb_resp.usage.prompt_tokens` |
| **3. Zusammenfassung** | KI schreibt fertigen Text | einmalig pro Thema (dann gecacht) | `mistral-large-latest` | Tokens aus `response.usage` |

Aktuell werden nur OCR und Steckbrief in `processing_log` geloggt (Tab 1). Zusammenfassungs-Kosten (Tab „Thema abfragen") werden noch nicht getrackt.

---

## Preise (Stand März 2026, Mistral Scale Plan)

| Operation | Preis | Quelle |
|---|---|---|
| OCR | $0.002 pro Seite ($2 pro 1 000 Seiten) | Mistral Pricing Page |
| Embedding (`mistral-embed`) | $0.10 pro 1 Mio. Tokens | Mistral Pricing Page |
| Chat (`mistral-large-latest`) Input | $2.00 pro 1 Mio. Tokens | Mistral Pricing Page |
| Chat (`mistral-large-latest`) Output | $6.00 pro 1 Mio. Tokens | Mistral Pricing Page |

Diese Konstanten stehen in `app_Claude.py`:

```python
PRICE_OCR_PER_PAGE    = 0.002              # $2 per 1 000 pages
PRICE_EMBED_PER_TOKEN = 0.10 / 1_000_000  # $0.10 per 1M tokens
PRICE_LARGE_IN_TOKEN  = 2.0  / 1_000_000  # $2 per 1M input tokens
PRICE_LARGE_OUT_TOKEN = 6.0  / 1_000_000  # $6 per 1M output tokens
```

Wenn Mistral die Preise ändert, reicht es, diese vier Zeilen anzupassen.

---

## Wo werden die Daten gespeichert?

Supabase-Tabelle: **`processing_log`**

```
id            — fortlaufende ID
filename      — z.B. "Klett_Deutsch kompetent EF.pdf"
operation     — "ocr" oder "embed"
pages         — Seitenanzahl (nur bei operation = "ocr")
tokens_in     — Eingabe-Tokens (nur bei operation = "embed")
tokens_out    — Ausgabe-Tokens (aktuell nicht genutzt)
cost_usd      — berechnete Kosten in US-Dollar
created_at    — Zeitstempel
```

Jede Verarbeitung schreibt **zwei Zeilen**: eine für OCR, eine für Embedding.

Beispiel nach Verarbeitung eines 109-seitigen Buchs:

| filename | operation | pages | tokens_in | cost_usd |
|---|---|---|---|---|
| Klett_Deutsch.pdf | ocr | 109 | — | 0.218000 |
| Klett_Deutsch.pdf | embed | — | 35 420 | 0.003542 |

---

## Wie wird gemessen?

### OCR-Kosten

Nach dem OCR-Aufruf enthält `ocr_response.pages` die Liste aller erkannten Seiten.

```python
ocr_cost = len(pages) * PRICE_OCR_PER_PAGE
log_processing_cost(filename, "ocr", pages=len(pages), cost_usd=ocr_cost)
```

### Embedding-Kosten

Die Mistral-Embedding-API gibt in der Antwort die Anzahl der verarbeiteten Tokens zurück.
Für jede Seite wird `emb_resp.usage.prompt_tokens` ausgelesen und aufaddiert.

```python
total_embed_tokens = 0
# pro Seite:
emb_resp = mistral.embeddings.create(model="mistral-embed", inputs=page_chunks)
total_embed_tokens += emb_resp.usage.prompt_tokens

# am Ende aller Seiten:
embed_cost = total_embed_tokens * PRICE_EMBED_PER_TOKEN
log_processing_cost(filename, "embed", tokens_in=total_embed_tokens, cost_usd=embed_cost)
```

### Fehlerresistenz

`log_processing_cost()` fängt alle Exceptions intern ab. Ein Fehler beim Logging stoppt **nie** die Buch-Verarbeitung — das ist Absicht.

---

## Wo sehe ich die Kosten?

### In der App (Tab 1)

Nach jeder Verarbeitung erscheint direkt im Erfolgs-Banner:

> ✅ Fertig! 109 Seiten → 2126 Abschnitte indexiert
> 💰 **Kosten dieser Verarbeitung: $0.2215** (OCR: $0.2180 · Embedding: $0.0035)

In der "Indexierte Bücher"-Liste steht pro Buch die Gesamtsumme:

> - **Klett_Deutsch kompetent EF.pdf** — 109 Seiten (2126 Abschnitte) · 💰 $0.2215

### Direkt in Supabase

```sql
-- Alle Einträge
SELECT * FROM processing_log ORDER BY created_at DESC;

-- Gesamtkosten pro Buch
SELECT filename, SUM(cost_usd) AS total_usd
FROM processing_log
GROUP BY filename
ORDER BY total_usd DESC;

-- Gesamtkosten aller Bücher
SELECT SUM(cost_usd) AS gesamt_usd FROM processing_log;
```

---

## Bekannte Lücken

| Was fehlt noch | Warum | Aufwand |
|---|---|---|
| Lehrplan-Extraktion (OCR + Chat) | Selten, geringe Kosten | ~30 min |
| Zusammenfassungen (Tab 2, Chat) | Pro-Abfrage schwer einem Buch zuzuordnen | ~1h |
| Kosten für bestehende Bücher (Klett, Paul D) | Wurden vor dem Tracking-System indexiert | Schätzung möglich (Seiten × Preise) |

---

## Typische Kosten zur Orientierung

| Dokument | Seiten | OCR | Embedding | Gesamt |
|---|---|---|---|---|
| Klett Deutsch kompetent EF | 109 | $0.22 | ~$0.004 | ~**$0.22** |
| Paul D Oberstufe Gesamtband | 315 | $0.63 | ~$0.011 | ~**$0.64** |
| Lehrplan (OCR + Chat-Extraktion) | ~40 | $0.08 | — + ~$0.10 | ~**$0.18** |
| Zusammenfassung (1 Thema, Tab 2) | — | — | ~$0.05 | ~**$0.05** |

Ein neues Schulbuch (~300 Seiten) kostet typisch **$0.60–0.70** zum Indexieren.
