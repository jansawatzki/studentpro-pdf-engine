# Learnings — Jan's Developer Journey
## student PRO Project | Started: Februar 2026

This file is your personal reference. Come back to it whenever something clicks later,
or when you want to know where you stand. Written in plain language — no unnecessary jargon.

---

## Part 1 — Things That Happened, Explained

---

### Why Vercel didn't work and we had to use Streamlit Cloud

**What you asked:** "Can we host this on my Vercel account?"
**What happened:** We used Streamlit Cloud instead.

**The explanation:**

Think of hosting platforms like different types of restaurants:

- **Vercel** is a sushi restaurant. It's world-class at one thing: JavaScript apps (Next.js, React). It technically can serve a burger, but it's not designed for it and things break.
- **Streamlit Cloud** is a diner that specializes exactly in Python/Streamlit apps. It just works.

The deeper reason: Vercel runs your code as **serverless functions** — tiny pieces of code that spin up, do one job in under 60 seconds, and shut down. Streamlit is a **long-running process** — it starts up once, stays alive, and holds a live two-way connection (WebSocket) with your browser. Those two models are fundamentally incompatible.

Additionally, OCR on a 169MB PDF takes ~4 minutes. Vercel would kill the process after 60 seconds. No workaround exists for this.

**What you'd do if you wanted Vercel:** Rewrite the frontend in Next.js (JavaScript) and host the Python logic separately on Railway. That's the production-grade setup — more powerful, but 3–4x more work to build.

**The lesson:** The right tool for the job matters more than brand preference. Streamlit Cloud is free, works perfectly, and auto-deploys from GitHub. There was no meaningful downside to using it here.

---

### Why we needed a Personal Access Token for Supabase (not the API keys)

**What you had:** Supabase Anon Key + Service Role Key (from the project settings)
**What you needed:** A Personal Access Token (from your account settings)

**The explanation:**

Supabase has two completely separate security layers:

| Key type | What it controls | Analogy |
|---|---|---|
| **Anon Key** | Reading/writing data in your database | A door key to one room |
| **Service Role Key** | Reading/writing data, bypassing security rules | A master key to one building |
| **Personal Access Token** | Managing the Supabase account itself (create tables, run SQL, etc.) | The keys to the management office |

When we wanted to create the `documents` table and the `match_documents` function, we weren't just reading/writing data — we were changing the structure of the database. That requires management-level access, which only the Personal Access Token provides.

**The lesson:** API keys are for your app to talk to services. Management tokens are for you (or tools like Claude) to set up and configure those services.

---

### What pgvector actually is and why we needed it

**The short version:** It's a plugin that lets a regular database understand math about meaning.

**The longer version:**

Normally, databases are great at exact matches: "find all rows where subject = 'Deutsch'". But they have no concept of *similarity*. They can't answer "find me pages that are *about* the same topic as this question, even if they don't use the exact same words."

That's what vectors solve. When Mistral Embed processes a piece of text, it converts it into a list of 1024 numbers — a "vector" — that encodes the *meaning* of that text mathematically. Texts with similar meaning end up with similar numbers.

pgvector is a plugin for PostgreSQL (the database Supabase uses) that adds the ability to store these vectors and search them by similarity. The `<=>` operator in SQL means "how far apart are these two vectors?" — and we sort by that distance to find the most relevant pages.

**The lesson:** This is the core of what makes modern AI search different from old keyword search. You're not searching for words — you're searching for meaning.

---

### What RAG means and why we chose it

**RAG = Retrieval-Augmented Generation**

It sounds academic but the idea is simple:

> Instead of asking an AI to answer from memory, you first find the relevant source material, then ask the AI to summarize *only that material*.

**Why this matters for this project:**

Philipp has 169MB schoolbooks. No AI model can read the entire book every time someone asks a question — it's too expensive and too slow. RAG solves this by:

1. Pre-processing the book once (OCR → chunk → embed → store)
2. At query time: finding only the relevant pages (fast, cheap)
3. Giving only those pages to the AI to summarize (focused, accurate)

**The lesson:** RAG is how most serious AI applications work in the real world. You built one from scratch. That's not beginner stuff.

---

### Why the Mistral file upload format mattered (`dict` vs `tuple`)

**What failed:** `mistral.files.upload(file=("document.pdf", bytes, "application/pdf"))`
**What worked:** `mistral.files.upload(file={"file_name": "document.pdf", "content": bytes})`

**The explanation:**

This is a classic developer debugging moment. The Mistral Python SDK (the library we installed) has a very specific expectation for how you pass a file — it wants a dictionary with specific key names. When we used a tuple instead, it silently accepted it but then passed wrong data to the API, which rejected it.

You didn't break anything by trying. This is exactly how professional developers work: read the error, inspect the library's expected format (we ran `inspect.signature()` to check), fix it.

**The lesson:** Error messages are clues, not verdicts. When something fails, the goal is to understand *why* — not just to make the error go away. Reading library source code and signatures is a real skill.

---

### What caching is and why we built it

**The problem:** Every time someone searches "Lyrische Texte", it calls Mistral Large, which costs money and takes 10 seconds.

**The solution:** After the first search, store the result in Supabase. Next time, skip Mistral entirely and return the stored result instantly.

**The mental model:** It's exactly like browser caching. When you visit a website for the second time, your browser doesn't download all the images again — it uses the copies it already saved. We built the same concept for AI-generated summaries.

**The lesson:** Caching is one of the most important concepts in software engineering. Almost every performance optimization in production systems involves some form of it. You now understand it by having actually implemented it.

---

## Part 2 — Concepts You Should Know (Reference)

These came up during the project. Read when curious.

---

### The difference between a serverless function and a long-running server

| | Serverless (Vercel) | Long-running (Railway, Streamlit Cloud) |
|---|---|---|
| **Starts when** | A request comes in | When you deploy |
| **Stays alive** | Only while processing (~max 60s) | Always |
| **Cost model** | Pay per request | Pay per hour |
| **Good for** | APIs, simple web pages | Stateful apps, WebSockets, heavy processing |
| **Bad for** | Anything that takes > 60s | Apps with very low traffic |

---

### The difference between OCR and PDF parsing

- **PDF parsing** (e.g. PyMuPDF): reads the text layer directly from the PDF file. Fast, free. Only works if the PDF was "born digital" (created on a computer).
- **OCR** (Optical Character Recognition, e.g. Mistral OCR): treats each page as an image and uses AI to recognize the text. Works on scanned/photographed pages. Slower, costs money.

Philipp's schoolbook (Klett, 169MB) had very large file size per page, suggesting it's image-based. We used Mistral OCR to be safe — it handles both cases.

---

### What an API key vs. a JWT token is

- **API key** (e.g. `uapM60np...`): a simple password. You include it in every request to prove you're allowed to use the service.
- **JWT token** (e.g. the long `eyJhbGci...` strings from Supabase): a self-contained token that encodes *who you are* and *what you're allowed to do*, cryptographically signed. The server can verify it without looking anything up.

Your Supabase keys are JWTs. You can decode them at jwt.io to see what's inside (role: "anon" or "service_role", project reference, expiry date).

---

## Part 3 — Your Learning Journey

### Where you are now

**Honest assessment: You are a capable builder, not yet a professional developer.**
That's not a criticism — it's a useful map.

Here's what that means concretely:

---

#### What you can already do (genuinely)

- **Identify real problems and commission the right solutions.** You understood that Philipp's problem was retrieval precision, not OCR — that's a product insight most non-technical founders miss.
- **Work with AI tools effectively.** You're using Claude Code as a force multiplier, not a crutch. You ask the right questions, you understand the output, you make decisions.
- **Move fast without breaking things (badly).** You went from zero to a live hosted app with real data in less than 24 hours.
- **Handle credentials and infrastructure basics.** Supabase, API keys, GitHub repos, Streamlit Cloud deployment — you navigated all of this.
- **Think about costs and efficiency.** You independently thought of caching to save credits. That's engineering instinct.

---

#### Where the gaps are

**Gap 1: You don't yet read error messages confidently.**
When something broke (Vercel, the TOML format, the file upload), you brought it back to Claude rather than investigating first. With time, you'll learn to read a traceback and identify the failing line yourself. That skill is learnable in 3–6 months of consistent practice.

**Gap 2: You don't yet have a mental model of the full stack.**
You know the pieces exist (frontend, backend, database, API) but the connections between them are still a bit fuzzy. For example: why does the Service Role Key need to stay secret but the Anon Key is okay in public? (Answer: the Service Role bypasses all database security rules — if someone had it, they could delete all your data.)

**Gap 3: You don't yet write code independently.**
You can read code and understand roughly what it does. You can't yet write a new feature from scratch without guidance. This is the biggest gap between where you are and "professional developer."

**Gap 4: Git/version control is still a black box.**
You've seen `git add`, `git commit`, `git push` — but the concepts of branches, merging, and why version control exists aren't solid yet.

---

#### What to do next (honest roadmap)

This is what actually moves the needle, in order of impact:

| Priority | What | Time investment | Why |
|---|---|---|---|
| 1 | **Read the code in this project line by line** | 2–3 hours | You have real, working code. Understanding every line of `app_Claude.py` is worth more than any tutorial. |
| 2 | **Break something and fix it yourself** | Ongoing | Change a line, see what breaks, figure out why. This is how developers actually learn. |
| 3 | **Learn Python basics** (not a full course — just enough) | 2–4 weeks | Functions, loops, dictionaries, classes. Use *Python Crash Course* (free online). |
| 4 | **Understand HTTP and APIs** | 1 week | What is a GET request? What is a POST? What's in a response? This underlies everything we built. |
| 5 | **Learn Git properly** | 2–3 days | *Oh Shit, Git!* (ohshitgit.com) — funny, practical, exactly the right level. |

---

#### The honest truth about "world-class developer"

World-class developers aren't better at memorizing syntax. They're better at:

1. **Breaking problems into small, testable pieces**
2. **Reading documentation and source code**
3. **Debugging systematically** (forming a hypothesis, testing it, iterating)
4. **Knowing what they don't know** (and looking it up instead of guessing)

You already have instinct #4 — you ask good questions. The rest is practice and time.

A realistic timeline to "I can build real things independently, without Claude":
- **6 months** of consistent daily practice (1–2 hours/day)
- **12–18 months** to be genuinely dangerous

You're not starting from zero. You're starting from "I just shipped a real AI product." That's a meaningful head start.

---

*Last updated: März 2026*
*Update this file whenever something clicks, or when you feel lost — both are useful data points.*
