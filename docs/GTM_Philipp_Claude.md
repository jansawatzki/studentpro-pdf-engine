# GTM — Wie Philipp die Technologie vermarktet

**Erstellt:** 2026-03-19 | **Owner:** Jan

---

## Die Ausgangslage

Was heute existiert: ein internes Produktions-Tool. Philipp gibt ein Lehrplan-Thema ein, bekommt die relevanten Buchseiten + eine Zusammenfassung, lädt das als Content in seine Lehrer-App hoch.

**Das ist nicht das Endprodukt — das ist die Maschine die das Endprodukt produziert.**

Die eigentliche Frage: Wie wird aus dieser Maschine ein skalierbares Geschäft für Philipp?

---

## Die zentrale These

> Das RAG-Backend ist ein **Content-Infrastruktur-Layer** der mit beliebigen Frontends verbunden werden kann. Jedes Frontend adressiert einen anderen Kundensegment und erschließt eine neue Einnahmequelle.

```
                    ┌─────────────────────────────────┐
                    │        RAG Backend               │
                    │  Supabase + Mistral + Chunking   │
                    │  (bereits gebaut, läuft)         │
                    └────────────┬────────────────────┘
                                 │
          ┌──────────────────────┼──────────────────────┐
          │                      │                      │
   ┌──────▼──────┐      ┌────────▼──────┐      ┌───────▼──────┐
   │ Frontend 1  │      │  Frontend 2   │      │  Frontend 3  │
   │ Lehrer-App  │      │  Verlag-      │      │  White-Label │
   │ (heute)     │      │  Dashboard    │      │  für andere  │
   └─────────────┘      └───────────────┘      └──────────────┘
```

---

## Die drei Märkte

---

### Markt 1 — Lehrer direkt (heute, bereits adressiert)

**Was:** Lehrer nutzen student PRO um Unterrichtsmaterial zu finden. Philipp produziert die Inhalte mit dem Backend und stellt sie bereit.

**Philipps Erlösmodell:** Abo-Gebühr pro Lehrer oder Schule.

**Wo das Backend reinspielt:** Jedes neue Lehrplan-Thema das Philipp mit dem Tool verarbeitet, ist ein neues Content-Paket das in der App erscheint. Das Backend ist der Inhalts-Produzent.

**Ausbaustufe:** Statt Philipp produziert das Tool die Inhalte — könnten Lehrer in Zukunft selbst Bücher hochladen und das System liefert ihnen direkt die Zusammenfassung? Das wäre ein Sprung von "Philipp als Operator" zu "Lehrer als Operator". Großes Potenzial, andere Produktfrage.

---

### Markt 2 — Schulbuch-Verlage (unerschlossen)

**Was:** Klett, Cornelsen, Westermann haben dieselben PDFs die Philipp lizenziert — aber keine intelligente Suchschicht darüber. Ein Verlag der seinen Lehrern sagen kann "Such in unserem Buch nach Lyrische Texte und bekomme eine strukturierte Zusammenfassung" hat einen klaren Differenzierungsvorteil gegenüber dem Wettbewerb.

**Philipps Position:** Er hat bereits Verlagslizenzen und kennt die Bücher. Er ist der natürliche Vermittler.

**Erlösmodell für Philipp:** Lizenzgebühr vom Verlag (einmalig oder jährlich) für die Integration. Oder: Philipp betreibt es als White-Label und der Verlag branded es als eigenes Produkt.

**Was gebaut werden müsste:** Frontend in Verlagsdesign, ggf. SSO-Integration. Das Backend bleibt identisch.

---

### Markt 3 — Andere Bundesländer / andere Lehrpläne (Skalierung)

**Was:** Das System ist heute auf NRW-Lehrplan trainiert. Bayern, Baden-Württemberg, Berlin haben eigene Lehrpläne und eigene Schulbücher. Dieselbe Technologie, anderer Content.

**Philipps Vorteil:** Der Aufwand für Bundesland #2 ist 80% kleiner als für Bundesland #1 — das Backend steht, es müssen nur neue Bücher indexiert und neue Lehrpläne hochgeladen werden.

**Erlösmodell:** Pro-Bundesland-Lizenz für Schulen oder Lehrer.

---

## Was Jan dabei baut (Folgeprojekte)

Das Backend ist fertig. Was jetzt fehlt sind die Frontends — und das ist Jan's nächste Angebotsebene.

| Projekt | Was es ist | Für wen | Aufwand |
|---|---|---|---|
| **Teacher Frontend** | Next.js UI für Lehrer — Thema suchen, Ergebnis lesen, Favoriten speichern | Philipps Endkunden | ~4 Wochen |
| **Verlag Dashboard** | Branded UI für einen Verlag — Buchauswahl, Themensuche, Export | Klett / Cornelsen | ~3 Wochen |
| **Multi-Tenant Backend** | Mehrere Schulen / Verlage auf einer Instanz, getrennte Daten via Row-Level Security | Skalierung | ~2 Wochen |
| **Admin Panel** | Philipp verwaltet Bücher, Themen, Nutzer ohne Entwickler | Philipps Operations | ~2 Wochen |
| **API Layer** | REST API die das Backend für externe Apps öffnet | Drittanbieter-Integration | ~1 Woche |

---

## Der Pitch an Philipp

**Die Kernbotschaft:**

> "Das Backend läuft. Der schwierige Teil ist fertig. Jetzt entscheidest du in welche Richtung das Produkt wächst — und ich kann jeden dieser Schritte bauen, weil ich das System von innen kenne."

**Warum Jan der richtige Partner für Folgeprojekte ist:**

- Kein Onboarding nötig — Architektur, Datenbank, API, alles bekannt
- Jedes neue Frontend baut auf demselben Backend auf — keine Doppelarbeit
- Risiko für Philipp ist minimal: Jan hat bereits bewiesen dass er liefert

**Konkrete nächste Schritte die Jan vorschlagen könnte:**

1. **Jetzt:** Akzeptanztest abschließen (5 Themen, ≥ 8/10) → offizieller Abschluss Phase 1
2. **Kurzfristig:** Teacher Frontend (Next.js) als Phase 2 anbieten — das was Lehrer tatsächlich sehen
3. **Mittelfristig:** Ein Verlag als Pilot-Kunde ansprechen — gemeinsam mit Philipp

---

## Offene Fragen für das Gespräch mit Philipp

1. **Welche Kundengruppe hat für Philipp gerade die höchste Priorität?** Lehrer direkt, oder eher B2B (Verlage, Schulen)?
2. **Hat Philipp bereits Gespräche mit Verlagen?** Die Lizenz-Frage ist zentral — hat er Exklusivrechte für digitale Nutzung der Bücher?
3. **Was ist Philipps Wachstumshypothese?** Tiefe (mehr Themen in NRW) oder Breite (andere Bundesländer, andere Fächer)?
4. **Wie sieht das Preismodell für Lehrer aktuell aus?** Das bestimmt wie viele Lehrer nötig sind um die Infrastruktur-Kosten zu tragen.
5. **Will Philipp Jan als langfristigen Tech-Partner oder plant er irgendwann einen eigenen Entwickler einzustellen?**

---

## Jans Positionierung

Jan sollte sich nicht als "der der die App gebaut hat" positionieren, sondern als **"Architect of Philipps content infrastructure"**.

Der Unterschied: Eine App baut jeder. Eine skalierbare Content-Pipeline die Verlagslizenzen, Lehrpläne und LLMs verbindet — das ist eine strategische Investition die Jan gebaut hat und die nur er schnell erweitern kann.

Das ist die Grundlage für eine langfristige Zusammenarbeit statt für ein einmaliges Projekt.
