# Tracking — Was wird gemessen und warum

**Erstellt:** 2026-03-20 | **Owner:** Jan

---

## Ziel

Jan will wissen wie Philipp die App benutzt — **ohne ihn fragen zu müssen**.
Vor jedem Folge-Meeting soll Jan die Query-Log-Daten ansehen und Verbesserungen
vorbereiten bevor Philipp überhaupt Feedback gibt.

---

## Was getrackt wird

### Tabelle: `query_log` (live seit 2026-03-20)

| Spalte | Was es bedeutet |
|---|---|
| `topic` | Welches Thema Philipp abgefragt hat |
| `subject` | Fach (Deutsch, Mathe, …) |
| `from_cache` | `true` = sofort aus Cache · `false` = frisch generiert (~20s) |
| `duration_ms` | Wie lange die Generierung gedauert hat (nur bei `from_cache=false`) |
| `chunks_found` | Wie viele Buchseiten gefunden wurden (Qualitätsindikator) |
| `cost_usd` | Was die Abfrage gekostet hat |
| `created_at` | Wann die Abfrage war |

### Tabelle: `summary_cache` (existiert schon länger)

| Spalte | Was es bedeutet |
|---|---|
| `hits` | Wie oft ein Thema insgesamt abgerufen wurde (inkl. Cache) |

---

## Nützliche SQL-Abfragen (in Supabase SQL Editor ausführen)

```sql
-- Was hat Philipp wann abgefragt?
SELECT topic, subject, from_cache, duration_ms, created_at
FROM query_log ORDER BY created_at DESC;

-- Welche Themen am häufigsten?
SELECT topic, COUNT(*) AS abfragen
FROM query_log GROUP BY topic ORDER BY abfragen DESC;

-- Durchschnittliche Wartezeit bei frischen Generierungen
SELECT ROUND(AVG(duration_ms) / 1000.0, 1) AS avg_sekunden
FROM query_log WHERE from_cache = false;

-- Cache-Trefferquote
SELECT
  ROUND(100.0 * SUM(CASE WHEN from_cache THEN 1 END) / COUNT(*), 1) AS cache_quote_pct,
  COUNT(*) AS anfragen_gesamt
FROM query_log;

-- Gesamtkosten
SELECT ROUND(SUM(cost_usd)::numeric, 4) AS gesamtkosten_usd
FROM query_log WHERE from_cache = false;
```

---

## Was noch NICHT getrackt wird (mögliche Erweiterungen)

| Was | Warum interessant | Aufwand |
|---|---|---|
| DOCX-Download | Hat Philipp die Zusammenfassung tatsächlich verwendet? | Mittel — Streamlit download_button hat kein zuverlässiges Callback |
| „Neu generieren" geklickt | War er unzufrieden mit der Zusammenfassung? | Gering — eine Zeile in `log_query()` |
| Welche Bücher ausgewählt | Nutzt er beide Bücher oder immer nur eines? | Gering — `selected_books` ist bereits verfügbar |
| Lehrplan-PDF hochgeladen | Wie aktiv pflegt er die Themenquelle? | Gering |

---

## Wie man die Daten vor einem Meeting nutzt

1. Supabase → SQL Editor → Abfragen oben ausführen
2. Schauen: Welche Themen hat er oft abgefragt? → Sind die Ergebnisse gut?
3. Schauen: Wie lange hat er gewartet? → Über 30s = Problem
4. Schauen: Hat er Themen mehrfach neu generiert? → Hinweis auf schlechte Qualität
5. Daraus: 1–2 konkrete Verbesserungen vorbereiten und im Meeting proaktiv ansprechen

---

## Implementierung

- **Tabelle erstellt:** via Supabase MCP `apply_migration` am 2026-03-20
- **Code:** `log_query()` Funktion in `app_Claude.py` (~Zeile 325)
- **Logging-Punkte:**
  - Cache-Treffer: nach `get_cached_summary()`, nur wenn `fresh_topic != keyword` (vermeidet Doppel-Log nach frischer Generierung)
  - Frische Generierung: nach `save_cached_summary()`, mit `duration_ms` und `cost_usd`
