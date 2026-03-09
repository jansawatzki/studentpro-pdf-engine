# Template Strategy — PDF Retrieval Engine as a Productized Service

**Created:** 2026-03-09 | **Owner:** Jan

---

## The core idea

What you built for Philipp is not a one-off project. It is a **reusable engine** that solves the same problem for many different clients:

> "I have a large collection of PDFs. I need to find the most relevant content for a list of topics and get a clean summary — without reading everything manually."

This problem exists in dozens of industries. The tech stack stays identical. Only the content (PDFs), the topics (their version of Philipps Excel), and the language of the prompts change.

---

## Who else has this problem?

| Industry | Their PDFs | Their "topics" |
|---|---|---|
| **Education** (like Philipp) | Schoolbooks, curriculum guides | NRW Lehrplan topics per subject |
| **Law firms** | Case law, contracts, legal commentaries | Legal questions, case types |
| **Pharma / Medical** | Clinical guidelines, drug documentation | Diagnoses, treatments, drug names |
| **Corporate HR** | Policy manuals, compliance handbooks | HR questions, compliance topics |
| **Insurance** | Policy documents, claims guidelines | Coverage types, claim scenarios |
| **Real estate** | Building regulations, property law | Regulation topics, property types |
| **Consulting** | Research reports, market studies | Client questions, industry topics |
| **Publishers** | Book catalogues, reference works | Reader questions, subject areas |

The pattern is always the same: **big PDFs + structured topic list + need for fast, accurate summaries.**

---

## What is reusable (everything technical)

The entire tech stack requires zero changes between clients:

| Component | Reusable? | Notes |
|---|---|---|
| Supabase DB schema | ✅ 100% | Same tables, same RPC |
| Mistral OCR | ✅ 100% | Works on any PDF language |
| Mistral Embed | ✅ 100% | Language-agnostic |
| Chunking logic | ✅ 100% | Same splitting algorithm |
| Vector search | ✅ 100% | Same pgvector setup |
| Caching layers | ✅ 100% | Ingestion + summary + lehrplan cache |
| Topic extraction pipeline | ✅ 100% | Just change the prompt |
| Streamlit UI structure | ✅ 95% | Labels and branding change |

---

## What changes per client (30–60 min of customization)

| What | Example (Philipp) | Example (Law firm) |
|---|---|---|
| App title | "student PRO — PDF Engine" | "LexSearch — Dokumenten-Engine" |
| Subject names | Deutsch, Mathematik | Vertragsrecht, Arbeitsrecht |
| "Topic" label | Lehrplan-Thema | Rechtsfrage |
| "Book" label | Schulbuch | Gesetzeskommentar |
| Summary system prompt | NRW teacher context | Legal analysis context |
| Extraction system prompt | NRW Lehrplan format | Legal taxonomy format |
| Export format | JSON for Philipps admin | CSV for case management tool |
| Branding / colors | student PRO blue | Client brand colors |

---

## What to build INTO this project now (so the next client is easy)

These are small decisions that cost almost nothing to do now but save hours later.

### 1. Config file per deployment
Instead of hardcoding "Deutsch", "Mathematik", "Lehrplan" in the app, move all client-specific strings into a `client_config_Claude.json`:

```json
{
  "app_title": "student PRO — PDF Engine",
  "subject_label": "Fach",
  "topic_label": "Thema",
  "document_label": "Schulbuch",
  "taxonomy_label": "Lehrplan",
  "default_subjects": ["Deutsch", "Mathematik"],
  "export_format": "json"
}
```

The app reads from this file. Deploying for a new client = swap the JSON. No code changes.

### 2. Keep prompts generic, not NRW-specific
The summary prompt currently mentions "NRW Lehrplan" and "Sekundarstufe II". That's correct for Philipp. But it lives in the `settings` DB table (editable), so this is already mostly solved — just make sure no NRW wording is hardcoded in the app code itself.

### 3. Rename "Lehrplan" to "Taxonomie" internally
The Lehrplan tab is really a "topic taxonomy upload" tab. Naming it "Lehrplan" in the code makes it feel specific to education. Renaming variables to `taxonomy`, `taxonomy_pdf`, `taxonomy_source` costs nothing and makes the code reusable by reading.

### 4. Supabase project per client
Each client gets their own Supabase project (their data, their DB, their credentials). The schema is identical — just a fresh deploy. Philipp even has his own Supabase already. Keep this pattern.

### 5. GitHub repo template
Once the Philipp project is done and stable, create a GitHub template repository stripped of all client-specific data. New client = fork the template, fill in the config JSON, done.

---

## How to price this

### Option A — Project fee (recommended to start)

| Component | Price |
|---|---|
| Setup + customization | €1,500 – €3,000 |
| PDF indexing (first corpus) | included |
| Training session (1h) | included |
| Monthly hosting + credits | €50 – €150/month |

**Why this works:** The setup is now fast (2–4h of real work). You are charging for the value (hours saved), not the hours worked.

### Option B — SaaS (later)

Once you have 3+ clients, consider a white-label SaaS:
- €99/month per client (self-serve, they upload their own PDFs)
- You run one shared Streamlit app with client login
- Supabase row-level security separates client data

This requires authentication and multi-tenancy — probably Phase 2 of the productization.

---

## The repeatable sales process

1. **Discovery call (30 min):** Ask: how many PDFs? How many topics? How do you use the results? What format do they need for export?
2. **Demo:** Show the Philipp app live. It sells itself — they see their exact use case.
3. **Proposal:** Fixed setup fee + monthly. Keep it simple.
4. **Kickoff:** Client sends PDFs + topic list (their version of the Excel). You index, tune prompts, deploy.
5. **Handover:** 1h training. They run it themselves.

The whole thing from kickoff to handover is now **1–2 days of work** (mostly indexing time, not dev time).

---

## Risks to manage

| Risk | How to handle |
|---|---|
| Client has DRM-locked PDFs | Check upfront — Mistral OCR cannot process encrypted PDFs |
| Client has non-German PDFs | Mistral OCR + Embed work in any language; prompts need translation |
| Client wants real-time (not batch) | That's a different product — scope it separately |
| Client wants their data on-premise | Supabase can be self-hosted; Mistral is EU-hosted (DSGVO ok) |
| Client changes topic list often | The topic extraction pipeline already handles this — they upload new taxonomy PDFs themselves |

---

## Immediate actions for this project (keep productization in mind)

These cost nothing to do now and make reuse much easier:

- [ ] Add `client_config_Claude.json` — pull app title + labels from config instead of hardcoding
- [ ] Rename "Lehrplan" to "Taxonomie" in internal variable names (UI labels stay German/client-specific)
- [ ] Confirm no NRW-specific wording is hardcoded in `app_Claude.py` (prompts are already in DB — good)
- [ ] After Philipp project is stable: strip to template repo on GitHub

---

## Summary

You have already built the hard part. The engine works. The next client is configuration, not construction. The goal now is to treat every architectural decision in the Philipp project as if it will be reused 10 times — because it will be.
