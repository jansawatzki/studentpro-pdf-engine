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

## Offene Fragen / To Explore

- [ ] Warum zeigt die Mistral-Oberfläche keinen historischen Verbrauch aus März?
      → Mögliche Ursache: Mistral zeigt nur die letzten 30 Tage, oder der Account
        hat sich geändert (anderer Login als der, unter dem der Key erstellt wurde)
- [ ] Unter welchem Mistral-Account wurde der API-Key `MISTRAL_API_KEY` erstellt?
      → API-Keys sind accountgebunden — Usage ist nur im Account des Key-Erstellers sichtbar
- [ ] Hat Rachid einen eigenen Key verwendet, oder denselben?
