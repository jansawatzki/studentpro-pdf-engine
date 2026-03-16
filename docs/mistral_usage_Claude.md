# Mistral Usage — Wo finde ich meine Verbrauchsdaten?

---

## 🔗 Direkter Link zur Usage-Seite

**https://console.mistral.ai/usage**

Login mit dem Mistral-Account, unter dem der API-Key erstellt wurde.

---

## Warum zeigt Mistral kaum Verbrauch?

Das ist das Caching-System, das wir eingebaut haben. Fast alle Abfragen werden aus
der `summary_cache`-Tabelle in Supabase beantwortet — Mistral wird dabei gar nicht
aufgerufen.

### Wann wird Mistral WIRKLICH aufgerufen?

| Aktion | Mistral-Modell | Kosten |
|---|---|---|
| Buch zum ersten Mal verarbeiten (OCR) | `mistral-ocr-latest` | ~3–5 € pro Buch |
| Buch zum ersten Mal einbetten (Fingerabdrücke) | `mistral-embed` | ~0,01 € pro Buch |
| Lehrplan verarbeiten (OCR + Themen-Extraktion) | `mistral-ocr-latest` + `mistral-large-latest` | ~0,10 € |
| Beispieldokument hochladen (Fingerabdruck) | `mistral-embed` | ~0,001 € |
| Thema zum ersten Mal abfragen | `mistral-embed` + `mistral-large-latest` | ~0,05 € |
| Thema erneut abfragen (gecacht) | — | **€0** |

### Was der Cache-Stand bedeutet

Sobald ein Thema einmal abgefragt wurde, speichert das System das Ergebnis in
Supabase. Jede weitere Abfrage desselben Themas geht direkt aus der Datenbank —
Mistral sieht davon nichts.

**Beispiel:** Die 3 Testthemen (Sprachvarietäten, Lyrische Texte, Kommunikationsmodelle)
wurden am 05.03.2026 und 09.03.2026 abgefragt. Seitdem sind alle Folge-Abfragen gecacht.
Mistral zeigt deswegen keinen laufenden Verbrauch.

---

## Wie sehe ich, was bisher verbraucht wurde?

In der Mistral Console unter `/usage`:

- **Usage** — API-Calls pro Modell, aufgeschlüsselt nach Tag
- **Billing** — Rechnungen und Gesamtkosten

Alternativ direkt in Supabase nachschauen:

```sql
-- Wie viele gecachte Zusammenfassungen gibt es?
SELECT COUNT(*), SUM(hits) FROM summary_cache;

-- Welche Themen wurden wie oft abgerufen?
SELECT topic, hits FROM summary_cache ORDER BY hits DESC;
```

---

## ✅ Analyse (Stand 16.03.2026)

**Account und Key stimmen überein.**

Der Key in `config_Claude.env` endet auf `GTug` — das ist der Key namens **"Claude"**
im Mistral-Account von Jan Sawatzki (sawatzki.jan@gmail.com).
Letzter Einsatz laut Mistral-Console: **March 16th, 2026** → passt, aktiv.

**Warum zeigt die aktuelle Billing-Ansicht €0,00?**

Die echten Kosten (OCR + Embeddings für Klett + Paul D, ~424 Seiten) sind am **05.03.2026**
angefallen — also in einem früheren Abrechnungszeitraum. Die aktuelle Ansicht zeigt
nur den laufenden Zeitraum, der danach begann.

**Wo die historischen Kosten zu finden sind:**
→ Mistral Console → **Billing → Invoices** (vergangene Rechnungen / Abrechnungsperioden)

**Warum ist der laufende Verbrauch wirklich €0?**
Der Cache funktioniert. Alle 3 Testthemen sind gecacht seit März — Mistral wird bei
Folgeabfragen nicht aufgerufen. Neuer Verbrauch entsteht erst wenn:
- ein neues Buch indexiert wird
- ein neues Thema zum ersten Mal abgefragt wird
- jemand auf "🔄 Neu generieren" klickt
