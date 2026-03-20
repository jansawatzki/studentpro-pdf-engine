# GitHub Repo privat + Streamlit Deploy Key

**Erstellt:** 2026-03-20 | **Owner:** Jan

---

## Problem

Streamlit Cloud braucht Lesezugriff auf das GitHub Repo um auto-deploy zu funktionieren.
Bei einem public Repo geht das automatisch. Bei einem private Repo muss ein **Deploy Key** eingerichtet werden — sonst erscheint "Updating the app files has failed" und die App crasht.

**Aktueller Status:** Repo ist PUBLIC (nach gescheitertem Versuch am 2026-03-20).

---

## Schritt-für-Schritt: Repo privat stellen + Deploy Key einrichten

### Schritt 1 — Deploy Key in Streamlit generieren

1. Geh auf **share.streamlit.io**
2. Klick auf die App (`jansawatzki/studentpro-pdf-engine`)
3. Klick **"⋮"** (drei Punkte, unten rechts) → **"Settings"**
4. Tab **"Sharing"** oder **"General"** → Abschnitt **"Deploy key"**
5. Klick **"Generate deploy key"** → Streamlit zeigt dir einen SSH Public Key (fängt mit `ssh-rsa` an)
6. Diesen Key kopieren

### Schritt 2 — Deploy Key in GitHub hinterlegen

1. Geh auf **github.com/jansawatzki/studentpro-pdf-engine**
2. **Settings** → **Deploy keys** → **"Add deploy key"**
3. Title: `Streamlit Cloud`
4. Key: den kopierten SSH Public Key einfügen
5. **"Allow write access"**: NEIN (nur Read nötig)
6. **"Add key"** klicken

### Schritt 3 — Repo auf privat stellen

Entweder über GitHub UI:
- github.com/jansawatzki/studentpro-pdf-engine → Settings → Danger Zone → "Change visibility" → Private

Oder via CLI (Claude kann das ausführen):
```bash
gh repo edit jansawatzki/studentpro-pdf-engine --visibility private --accept-visibility-change-consequences
```

### Schritt 4 — Streamlit neu starten

1. share.streamlit.io → App → **"⋮"** → **"Reboot app"**
2. Logs beobachten: muss "Pulling code changes from GitHub" + "Updated app!" zeigen
3. App aufrufen und prüfen ob sie läuft

---

## Verifizieren dass es funktioniert

```
✅ Repo: github.com/jansawatzki/studentpro-pdf-engine zeigt "Private"
✅ Streamlit Logs: kein "Updating the app files has failed"
✅ App: studentpro.streamlit.app lädt korrekt
✅ Auto-deploy: nach git push erscheint "Updated app!" in den Logs
```

---

## Reihenfolge ist wichtig

**ERST** Deploy Key einrichten → **DANN** Repo privat stellen.
Andersherum verliert Streamlit sofort den Zugriff (wie am 2026-03-20 passiert).

---

## App-Sichtbarkeit vs. Repo-Sichtbarkeit

Diese zwei Dinge sind unabhängig voneinander:

| | Public | Private |
|---|---|---|
| **GitHub Repo** | Code für alle sichtbar | Code nur für Jan |
| **Streamlit App** | URL für jeden aufrufbar | URL nur für eingeladene User |

Das Repo privat zu stellen ändert **nicht** wer die App aufrufen kann.
Um die App selbst zu schützen: share.streamlit.io → Settings → Sharing → "Only specific people".
