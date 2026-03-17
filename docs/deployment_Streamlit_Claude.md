# Deployment Guide — Streamlit Cloud

**App:** https://studentpro.streamlit.app
**Repo:** https://github.com/jansawatzki/studentpro-pdf-engine
**Branch:** `main` — auto-deploys on every push

---

## How auto-deployment works

1. Push any commit to `main`
2. Streamlit Cloud detects the push (usually within 30 seconds)
3. If `requirements.txt` changed → full pip reinstall
4. If only code changed → restarts app without reinstalling packages
5. App is live again in ~1–2 minutes

---

## Requirements file rules

**Only `requirements.txt` in the repo root is read by Streamlit Cloud.**
`requirements_Claude.txt` exists for reference only — Streamlit ignores it.

### Current `requirements.txt`
```
streamlit
mistralai==1.10.0
supabase
python-dotenv
openpyxl
python-docx
```

### What NOT to add
| Package | Reason |
|---|---|
| `pymupdf` | C extension — fails to build on Streamlit Cloud Linux, aborts entire pip install |

`pymupdf` is only needed in `ingest_Claude.py` which runs **locally**, never on Streamlit Cloud.

Note: `python-docx` **is** included — it is used for DOCX **generation** (writing Word files), not parsing. It builds cleanly on Linux.

---

## Debugging a broken deployment

### Step 1 — Check what the actual error is
Streamlit redacts the full error message in the UI to prevent data leaks.
To see the real error: open the app URL → click **"Manage app"** (bottom right corner) → **Logs**.

### Step 2 — Common errors and fixes

| Error shown | Likely cause | Fix |
|---|---|---|
| `ImportError: from mistralai import Mistral` | Old mistralai version cached, or pip install aborted mid-way | Check requirements.txt; ensure no package causes pip to abort before mistralai installs |
| `ImportError` on any line | A package in requirements.txt failed to install (often a C extension) | Remove the offending package if the app doesn't actually use it |
| `ModuleNotFoundError: No module named 'X'` | Package missing from requirements.txt entirely | Add it |
| App loads but crashes on action | Runtime error, not import error — check Logs for full traceback |  Fix the code |
| Login redirect loop | App visibility set to Private | Share → set to Public in Streamlit Cloud dashboard |

### Step 3 — Force a full rebuild
If the packages seem correct but the error persists (cached environment):
1. Change the pinned version in `requirements.txt` (e.g. bump `mistralai==1.10.0` → add a comment `# rebuilt YYYY-MM-DD`)
2. Commit and push — this changes the file hash and forces Streamlit to reinstall

OR: go to **share.streamlit.io** → app menu → **Reboot app**.

---

## Secrets (environment variables)

Secrets are stored in Streamlit Cloud's secret manager (not in the repo).
The app reads them via `st.secrets` with a local `.env` fallback:

```python
try:
    MISTRAL_API_KEY = st.secrets["MISTRAL_API_KEY"]
    ...
except Exception:
    load_dotenv("config_Claude.env")
    MISTRAL_API_KEY = os.getenv("MISTRAL_API_KEY")
```

**Required secrets in Streamlit Cloud dashboard:**
- `MISTRAL_API_KEY`
- `SUPABASE_URL`
- `SUPABASE_SERVICE_KEY`

To add/update: share.streamlit.io → app → Settings → Secrets.

---

## Known issues & history

| Date | Issue | Root cause | Fix |
|---|---|---|---|
| 2026-03-14 | `ImportError: from mistralai import Mistral` | `pymupdf` in requirements.txt caused pip install to abort before reaching `mistralai` | Removed `pymupdf`, pinned `mistralai==1.10.0` |
| 2026-03-14 | App unreachable (login redirect) | App visibility set to Private | Change to Public in Streamlit Cloud dashboard |
