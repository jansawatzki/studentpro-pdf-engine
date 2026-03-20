# Technische Strategie — Frontends & Hosting

**Erstellt:** 2026-03-19 | **Owner:** Jan

---

## Was heute existiert

```
Streamlit App (studentpro.streamlit.app)
    └── app_Claude.py (Python — OCR, Embed, Suche, Zusammenfassung)
            └── Supabase (PostgreSQL + pgvector)
                    └── Mistral API (OCR, Embed, Large)
```

Das ist ein internes Werkzeug. Philipp bedient es allein. Kein Login, kein Multi-User, kein mobiles Design.

**Das Problem:** Jedes neue Frontend (Lehrer-App, Nachhilfe-App, Verlag-Dashboard) braucht dieselbe Logik — aber Streamlit ist dafür nicht geeignet. Es ist langsam, nicht mobilfähig und nicht white-label-fähig.

---

## Die zentrale Architekturfrage

> Wo lebt die Intelligenz (Mistral-Aufrufe, Chunking, Suche)?

Drei Optionen:

| Option | Wie | Pro | Contra |
|---|---|---|---|
| **A — FastAPI** | Python-Backend als REST API, Frontends rufen es auf | Bestehender Python-Code wiederverwendbar | Extra Server nötig |
| **B — Supabase Edge Functions** | Logik als TypeScript-Funktionen direkt in Supabase | Kein separater Server, alles in Supabase | Muss in TypeScript umgeschrieben werden |
| **C — Direkt aus Frontend** | Next.js ruft Supabase + Mistral direkt auf | Einfachste Architektur | API Keys im Frontend-Code riskant |

**Empfehlung: Option A (FastAPI)** — Jan kennt Python, der bestehende Code kann direkt wiederverwendet werden, und FastAPI ist in wenigen Stunden aufgesetzt.

---

## Empfohlene Ziel-Architektur

```
┌─────────────────────────────────────────────────────────┐
│                    SUPABASE                              │
│  PostgreSQL + pgvector + Auth + Row-Level Security       │
│  (Single source of truth für alle Frontends)            │
└──────────────────────┬──────────────────────────────────┘
                       │
          ┌────────────▼────────────┐
          │    FastAPI (Python)      │
          │    Railway (~€5/Monat)   │
          │                          │
          │  /search   → Suche       │
          │  /summary  → Mistral     │
          │  /ingest   → OCR+Embed   │
          └────┬──────────┬──────────┘
               │          │
    ┌──────────▼──┐   ┌───▼──────────────┐
    │  Streamlit  │   │   Next.js         │
    │  (intern,   │   │   (Vercel, free)  │
    │  bleibt)    │   │   Lehrer / Nachhilfe / Verlag │
    └─────────────┘   └───────────────────┘
```

**Streamlit bleibt** als internes Operator-Tool für Philipp. Die neuen Frontends sind Next.js und laufen auf Vercel.

---

## Konkrete Frontend-Tools — Was passt wann?

Es gibt heute mehrere Wege ein Frontend zu bauen. Keiner ist universell richtig — es kommt auf den Use Case an.

---

### Option 1 — Lovable (empfohlen für schnellen Start)

**Was es ist:** KI-gestützter Full-Stack App-Builder. Du beschreibst was du willst, Lovable generiert React-Code und verbindet sich direkt mit Supabase.

**Wie es mit dem bestehenden System zusammenspielt:**

```
Lovable → Supabase (direkt, native Integration) ✅
Lovable → FastAPI (via HTTP-Calls)              ✅
Lovable → Mistral (direkt, nicht empfohlen)     ⚠️ API Key wäre sichtbar
```

**Was Lovable gut kann:**
- Themenliste anzeigen (liest direkt aus `topics` Tabelle)
- Gecachte Zusammenfassungen anzeigen (liest aus `summary_cache`)
- Login/Auth via Supabase Auth — fertig in Minuten
- Mobil-optimiertes Design ohne CSS-Kenntnisse

**Was Lovable nicht kann (ohne FastAPI):**
- Neue Zusammenfassungen triggern (Mistral Large Aufruf)
- OCR oder Embedding neuer Bücher

**Praktischer Ansatz: Lovable für die Nutzer-Seite, FastAPI für die Intelligenz**

```
Lovable Frontend
  → Thema wählen → gecachte Zusammenfassung aus Supabase lesen  ← 90% der Nutzung
  → "Neu generieren" → FastAPI aufrufen → Mistral → Supabase → zurück ans Frontend
```

**Kosten:** Free Tier (5 Projekte), dann ~$20/Monat.
**Zeitaufwand:** MVP in 1–2 Tagen. Lovable generiert den Code, Jan verbindet FastAPI.
**Exportierbar:** Ja — Lovable gibt dir den React-Code, den du auf Vercel deployen kannst. Keine Abhängigkeit von Lovable nach dem Export.

---

### Option 2 — v0 by Vercel (für UI-Komponenten)

**Was es ist:** KI-Tool das einzelne React-Komponenten generiert — kein Full-Stack, nur UI.

**Wann sinnvoll:** Jan hat bereits eine Next.js App und will einzelne Screens schnell generieren. v0 erstellt den Code, Jan fügt ihn in sein Projekt ein.

**Kosten:** Kostenlos für Basis-Nutzung.

---

### Option 3 — FlutterFlow (wenn Philipp eine mobile App will)

**Was es ist:** No-Code Builder für Flutter-Apps — Philipps bestehende Lehrer-App ist bereits in Flutter.

**Vorteil:** Kann direkt an Supabase angebunden werden. Wenn Philipp seine Lehrer-App erweitern will (statt ein separates Web-Frontend), ist FlutterFlow der schnellste Weg.

**Kosten:** ~$30/Monat.
**Wann sinnvoll:** Wenn Philipp sagt "ich will das in meiner bestehenden App haben, nicht auf einer neuen Website."

---

### Option 4 — Retool (für interne Dashboards)

**Was es ist:** Low-Code Tool für interne Operator-Dashboards. Philipp könnte damit Bücher verwalten, Kosten einsehen, Themen bearbeiten — ohne dass Jan ständig die Streamlit-App anpassen muss.

**Kosten:** Kostenlos für interne Tools (bis 5 User).
**Wann sinnvoll:** Als Ersatz für die aktuelle Streamlit-App wenn Philipp mehr Kontrolle ohne Entwickler braucht.

---

### Entscheidungsbaum

```
Will Philipp eine mobile App (iOS/Android)?
  → JA  → FlutterFlow (baut auf seiner Flutter-App auf)
  → NEIN ↓

Braucht er es in 1-2 Wochen als Demo?
  → JA  → Lovable (schnellste Prototyping-Option mit Supabase-Integration)
  → NEIN ↓

Hat Jan Zeit für saubere Architektur?
  → JA  → Next.js (v0 für UI) + FastAPI (für Logik)
  → NEIN → Lovable exportieren + Vercel deployen
```

---

## Schritt-für-Schritt: Erstes Frontend aufbauen

### Schritt 1 — FastAPI Layer aus app_Claude.py extrahieren (~1 Tag)

Die Kernfunktionen aus `app_Claude.py` in eine FastAPI-App auslagern:

```python
# api_Claude.py
from fastapi import FastAPI
app = FastAPI()

@app.post("/search")
async def search(topic: str, subject: str, books: list[str]):
    # bestehende Suchlogik aus app_Claude.py
    ...

@app.post("/summary")
async def summary(topic: str, chunks: list):
    # bestehende Zusammenfassungslogik
    ...
```

Kein Neuschreiben — Copy-Paste der bestehenden Funktionen, FastAPI-Wrapper drumrum.

### Schritt 2 — FastAPI auf Railway deployen (~2 Stunden)

Railway (railway.app) ist das einfachste Python-Hosting:
1. GitHub Repo verbinden
2. `Procfile` anlegen: `web: uvicorn api_Claude:app --host 0.0.0.0 --port $PORT`
3. Environment Variables setzen (Mistral Key, Supabase Keys)
4. Deploy → fertig, URL: `https://studentpro-api.railway.app`

Kosten: **$5/Monat** (Hobby Plan) oder kostenlos bis zum Usage-Limit.

### Schritt 3 — Next.js Frontend aufsetzen (~2 Tage für MVP)

```bash
npx create-next-app@latest studentpro-lehrer --typescript
```

Das Frontend ruft die FastAPI auf:

```typescript
// Thema suchen
const results = await fetch('https://studentpro-api.railway.app/search', {
  method: 'POST',
  body: JSON.stringify({ topic: 'Lyrische Texte', subject: 'Deutsch', books: [...] })
})
```

Supabase direkt aus Next.js für reine Lesezugriffe (Themenliste, gecachte Zusammenfassungen):

```typescript
import { createClient } from '@supabase/supabase-js'
const supabase = createClient(SUPABASE_URL, SUPABASE_ANON_KEY)
const { data } = await supabase.from('topics').select('*')
```

### Schritt 4 — Auf Vercel deployen (~30 Minuten)

```bash
npx vercel
```

GitHub Repo verbinden → auto-deploy bei jedem Push. **Kostenlos** auf dem Free Tier.
URL: `https://studentpro-lehrer.vercel.app` (oder eigene Domain)

---

## Multi-Tenancy: Mehrere Kunden auf einer Instanz

Wenn Philipp verschiedene Organisationen (Studienkreis, Schülerhilfe, eigene Lehrer) auf derselben Infrastruktur betreiben will:

### Supabase Auth + Row-Level Security

```sql
-- Jeder User gehört zu einer Organisation
CREATE TABLE organisations (id uuid, name text, slug text);
ALTER TABLE documents ADD COLUMN org_id uuid REFERENCES organisations(id);

-- RLS Policy: User sieht nur Daten seiner Organisation
CREATE POLICY "org isolation"
ON documents FOR ALL
USING (org_id = (SELECT org_id FROM users WHERE id = auth.uid()));
```

Resultat: Studienkreis-Lehrer sehen nur Studienkreis-Bücher. Schülerhilfe-Lehrer sehen nur Schülerhilfe-Bücher. Eine Datenbank, vollständig isoliert.

### Pro Organisation: eigenes Frontend oder Subdomain

```
studienkreis.studentpro.de  →  Studienkreis-Branding
schuelerhilfe.studentpro.de →  Schülerhilfe-Branding
lehrer.studentpro.de        →  Direktlehrer
```

Alle zeigen auf dasselbe Next.js-Deployment auf Vercel, aber mit unterschiedlicher Konfiguration (Logo, Farben, welche Bücher sichtbar sind).

---

## Hosting-Übersicht

| Komponente | Service | Kosten | Warum |
|---|---|---|---|
| Streamlit (intern) | Streamlit Cloud | Kostenlos | Bleibt wie heute |
| FastAPI (Backend) | Railway | ~€5/Monat | Einfachstes Python-Hosting |
| Next.js (Frontend) | Vercel | Kostenlos | Optimal für Next.js, CDN inklusive |
| Datenbank | Supabase | Kostenlos bis ~€25 | Bleibt wie heute |
| Domain | Namecheap/Cloudflare | ~€10/Jahr | Optional, für Kundenpräsentation |
| **Gesamt** | | **~€5–30/Monat** | |

---

## Reihenfolge für Jan

| Schritt | Was | Aufwand | Wann |
|---|---|---|---|
| 1 | FastAPI Layer aus app_Claude.py extrahieren | ~1 Tag | Erstes Folgeprojekt |
| 2 | Railway Deployment + Testen | ~2h | Gleicher Tag |
| 3 | Next.js MVP für Lehrer/Nachhilfe | ~3 Tage | Zweite Woche |
| 4 | Supabase Auth einbauen | ~1 Tag | Dritte Woche |
| 5 | Vercel Deployment + Subdomain | ~2h | Gleicher Tag |
| 6 | Multi-Tenancy (RLS) | ~2 Tage | Bei erstem B2B-Kunden |

**Wichtig:** Schritt 1 und 2 sind die Voraussetzung für alles andere. Ohne FastAPI-Layer kann kein Frontend die Mistral-Logik nutzen.

---

## Was das Gespräch mit Philipp ergeben muss

Bevor Jan anfängt zu bauen, muss klar sein:

1. **Welches Frontend zuerst?** Nachhilfe-App (schnellster Weg zu B2B-Umsatz) oder Lehrer-Frontend (größerer Markt, mehr Konkurrenz)?
2. **Eigene Domain?** `studentpro.de` oder Subdomains unter seiner bestehenden Domain?
3. **Wer betreibt Railway?** Philipps Account oder Jans Account? (Kostenverantwortung)
4. **Branding:** Hat Philipp ein Design-System, Farben, Logos für verschiedene Kundengruppen?

---

## Metriken & Performance-Tracking

Philipp möchte keine Zusammenfassung die 3 Minuten braucht. Das ist verständlich — und messbar. Diese Sektion erklärt was gemessen werden soll, wie reale Zeiten aussehen, und wie man das ohne großen Aufwand trackt.

---

### Was sollte gemessen werden?

| Metrik | Warum wichtig | Zielwert |
|---|---|---|
| **End-to-End-Zeit** | Nutzererfahrung: wie lange wartet Philipp? | < 30 Sekunden (frisch), < 1s (Cache) |
| **Cache-Trefferquote** | Wie oft muss Mistral gar nicht aufgerufen werden? | > 60% nach 2 Wochen Betrieb |
| **Kosten pro Anfrage** | Wie viel kostet eine frische Zusammenfassung? | ~€0.05 (Zielwert) |
| **Fehlerrate** | Wie oft schlägt ein API-Aufruf fehl (Mistral, Supabase)? | < 1% |
| **Suchergebnisse** | Wie viele Chunks werden gefunden? (zu wenig = schlechte Summary) | ≥ 5 relevante Chunks |

---

### Wie lange dauert was? (Realwerte)

```
Nutzer klickt "Zusammenfassung" → frische Generierung:

Schritt 1 — Steckbrief berechnen (Embed)     ~1–2 Sekunden
Schritt 2 — Vektordatenbank durchsuchen       ~1 Sekunde
Schritt 3 — Mistral Large generiert           ~15–25 Sekunden
────────────────────────────────────────────
Gesamt                                        ~18–28 Sekunden

Cache-Treffer (Topic wurde schon generiert):  < 1 Sekunde
```

Das ist die Baseline. Alles über 35 Sekunden ist ein Problem das untersucht werden sollte.

---

### Option A — Einfach: Supabase `query_log` Tabelle (empfohlen für Start)

Kein externes Tool, keine Kosten, alles in der bestehenden Supabase-DB.

```sql
CREATE TABLE query_log (
  id          uuid DEFAULT gen_random_uuid() PRIMARY KEY,
  topic       text,
  subject     text,
  from_cache  boolean,
  duration_ms integer,
  chunks_found integer,
  cost_usd    numeric(10,6),
  error       text,
  created_at  timestamptz DEFAULT now()
);
```

In `app_Claude.py` / FastAPI: vor und nach der Generierung messen:

```python
import time

start = time.time()

# ... Steckbrief + Suche + Mistral ...

duration_ms = int((time.time() - start) * 1000)

supabase.table("query_log").insert({
    "topic": topic,
    "subject": subject,
    "from_cache": False,
    "duration_ms": duration_ms,
    "chunks_found": len(chunks),
    "cost_usd": estimated_cost,
}).execute()
```

In der Streamlit-App (Tab „Projektübersicht") dann einfach auswerten:

```sql
-- Durchschnittszeiten
SELECT
  from_cache,
  ROUND(AVG(duration_ms) / 1000.0, 1) AS avg_sekunden,
  COUNT(*) AS anfragen
FROM query_log
GROUP BY from_cache;

-- Cache-Trefferquote
SELECT
  ROUND(100.0 * SUM(CASE WHEN from_cache THEN 1 END) / COUNT(*), 1) AS cache_quote_pct
FROM query_log;
```

**Aufwand:** ~2 Stunden. Reicht für interne Nutzung und Philipp-Demos.

---

### Option B — Professionell: PostHog (wenn es ein richtiges Frontend wird)

PostHog ist ein Open-Source-Analytics-Tool — kostenloses Free Tier (1M Events/Monat), DSGVO-konform wenn EU-Cloud gewählt wird, kein Cookie-Banner nötig für rein interne Nutzung.

**Warum PostHog statt Google Analytics:** Ereignis-basiert (kein Pageview-Denken), gut für Custom Events ("Zusammenfassung generiert", "Buch hochgeladen"), und funktioniert sowohl in Python als auch in Next.js/React.

**Python (FastAPI / Streamlit):**

```python
from posthog import Posthog
posthog = Posthog(project_api_key='...', host='https://eu.posthog.com')

posthog.capture(
    distinct_id='philipp',  # oder user_id aus Supabase Auth
    event='summary_generated',
    properties={
        'topic': topic,
        'subject': subject,
        'duration_ms': duration_ms,
        'from_cache': False,
        'chunks_found': len(chunks),
        'cost_usd': cost,
    }
)
```

**Next.js:**

```typescript
import posthog from 'posthog-js'

posthog.capture('summary_generated', {
  topic: selectedTopic,
  subject: selectedSubject,
  duration_ms: endTime - startTime,
  from_cache: result.from_cache,
})
```

PostHog erstellt dann automatisch Dashboards: durchschnittliche Wartezeit, Cache-Trefferquote, meistgesuchte Themen — ohne SQL.

**Aufwand:** ~4 Stunden (Setup + Events in FastAPI + Events in Next.js).

---

### Option C — Fehler-Monitoring: Sentry (optional, wenn Philipp klagt)

Wenn Nutzer Fehler bekommen (Mistral-Timeout, Supabase-Verbindung bricht weg), sieht Jan das in Sentry sofort — mit Stack Trace und dem genauen Thema das den Fehler ausgelöst hat.

```python
import sentry_sdk
sentry_sdk.init(dsn="https://...@sentry.io/...")

# Dann automatisch: alle unbehandelten Exceptions werden geloggt
```

**Kosten:** Kostenlos bis 5.000 Fehler/Monat.
**Wann sinnvoll:** Wenn Philipp erste externe Nutzer hat und Jan nicht mehr jeden Fehler selbst sieht.

---

### Empfehlung: Stufenplan

```
Jetzt (intern, Philipp allein):
  → Option A: query_log Tabelle
  → Auswertung im Projektübersicht-Tab
  → Aufwand: 2h

Wenn Frontend für externe Nutzer:
  → Option B: PostHog EU-Cloud dazu
  → Cache-Trefferquote + Nutzungsverhalten sichtbar
  → Aufwand: 4h zusätzlich

Wenn erster Kundenvertrag:
  → Option C: Sentry für Fehler-Alerting
  → Damit Jan nachts nicht aufwacht wenn etwas kaputt geht
```

---

### Was Philipp konkret sehen sollte (in der App oder einem Dashboard)

```
📊 Performance (letzte 30 Tage)
────────────────────────────────
Anfragen gesamt:        127
davon aus Cache:         81 (64%)
Durchschnitt frisch:    23s
Durchschnitt Cache:      0.3s
Gesamtkosten:          ~€2.30
Häufigste Themen:       Lyrische Texte (12×), Kommunikationsmodelle (8×)
```

Das ist genug um zu sehen ob das System läuft, ob der Cache greift, und ob die Kosten im Rahmen bleiben.
