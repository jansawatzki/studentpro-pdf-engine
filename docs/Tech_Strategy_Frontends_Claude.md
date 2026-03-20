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
