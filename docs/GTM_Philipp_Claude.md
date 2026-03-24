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

### Markt 3 — Nachhilfeorganisationen (B2B, hohe Zahlungsbereitschaft)

**Was:** Studienkreis, Schülerhilfe, Abacus und ähnliche Organisationen beschäftigen tausende Nachhilfelehrer — viele davon Studenten ohne tiefes Fachwissen. Das größte Problem dieser Organisationen: **Qualitätssicherung der Lernstunden.** Ein Nachhilfelehrer der ad hoc Deutsch EF unterrichtet, braucht in 10 Minuten einen strukturierten Überblick über "Kommunikationsmodelle" — genau das liefert dieses System.

**Philipps Vorteil:** Er hat bereits Kontakte im Bildungsmarkt und kennt das NRW-Curriculum. Studienkreis allein hat ~1.000 Standorte in Deutschland.

**Erlösmodell für Philipp:**
- Pro-Lehrer-Lizenz (~€5–15/Monat) × tausende Nachhilfelehrer = signifikanter Umsatz
- Oder: Pauschal-Lizenz pro Organisation (~€500–2.000/Monat)
- Einstieg: Pilotprojekt mit einem regionalen Standort, dann Rollout

**Was gebaut werden müsste:** Einfaches, mobil-optimiertes Frontend — Nachhilfelehrer schauen kurz vor der Stunde auf dem Handy nach. Kein komplexes Dashboard, nur: Fach → Thema → Zusammenfassung. Das Backend bleibt identisch.

**Warum das attraktiver als Lehrer-Direktvertrieb ist:** Organisationen haben Budgets, Entscheidungsträger und einen klaren ROI ("unsere Lehrer sind besser vorbereitet"). Einzellehrer sind schwer zu erreichen und preis-sensitiv.

---

### Markt 4 — Andere Bundesländer / andere Lehrpläne (Skalierung)

**Was:** Das System ist heute auf NRW-Lehrplan trainiert. Bayern, Baden-Württemberg, Berlin haben eigene Lehrpläne und eigene Schulbücher. Dieselbe Technologie, anderer Content.

**Philipps Vorteil:** Der Aufwand für Bundesland #2 ist 80% kleiner als für Bundesland #1 — das Backend steht, es müssen nur neue Bücher indexiert und neue Lehrpläne hochgeladen werden.

**Erlösmodell:** Pro-Bundesland-Lizenz für Schulen, Lehrer oder Nachhilfeorganisationen.

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

---

## Philipps GTM-Auftrag — Vollständiger RFP (Stand 2026-03-24)

Philipp hat Jan denselben Brief geschickt den er an andere Agenturen schickt. Das ist der genaue Auftrag.

**Produktbeschreibung laut Philipp:**
> "student PRO ist eine fast fertig entwickelte Anwendung (native App & Web-App) mit bestehender Content-Pipeline und ausgearbeitetem Design. Der Fokus liegt jetzt auf der strukturierten Vorbereitung des Markteintritts."

**Wichtig:** Philipp beschreibt student PRO als **zweiseitigen Marktplatz: Lehrkräfte & Schüler/Eltern**. Das ist breiter als im Demo-Meeting besprochen — die App hat zwei Nutzergruppen.

---

### Was Philipp konkret sucht (seine 7 Bausteine)

| # | Baustein | Was Jan dazu einbringen kann |
|---|---|---|
| 1 | Markt- und Wettbewerbsanalyse EdTech (Nachhilfe, AI-Tutoring, Microlearning) | Kennt den Markt bereits, kann schnell Competitor-Research liefern |
| 2 | Zielgruppen- und Persona-Definition (Lehrkräfte & Schüler/Eltern) | Kann Personas direkt aus query_log + Produktkenntnissen ableiten |
| 3 | Positionierung + Angebots- und Monetarisierungsstruktur | Hat bereits GTM-Dokument mit Marktanalyse — Vorsprung gegenüber jeder Agentur |
| 4 | Conversion- und Funnel-Strategie | Track Record aus letztem Job + eigene Projekte |
| 5 | Landingpage-/Website-Konzept (inkl. UX/UI-Empfehlungen) | Kann direkt bauen (Lovable/Next.js) — Agenturen liefern nur Mockups |
| 6 | KPI- und Tracking-Framework | query_log bereits implementiert — kann direkt darauf aufbauen |
| 7 | Kanalstrategie (Organic, Paid, Kooperationen) | Allgemeine GTM-Kompetenz + LinkedIn Sales Navigator bereits aktiv |

### Deliverables die Philipp erwartet

1. Competitor- und Benchmark-Analyse
2. Positionierungs- und Differenzierungsansatz
3. Definierte Personas
4. Conversion-Blueprint und Funnel-Struktur
5. Website-/Landingpage-Konzept (inkl. UX/UI-Empfehlungen)
6. KPI- und Tracking-Konzept
7. Channel-Mix und Customer-Acquisition-Ansatz

---

## Jans Angebot — Was konkret zu liefern ist

**Jans einzigartiger Vorteil gegenüber jeder Agentur:**

> Jede Agentur braucht 2–3 Wochen Briefing. Jan kann morgen anfangen — er kennt das Produkt, die Datenbank, die Nutzer und den Markt bereits.

Zusätzlich kann Jan etwas das keine Agentur kann: **er liefert nicht nur Konzepte, sondern baut auch direkt**. Ein Landingpage-Konzept von einer Agentur = PowerPoint. Von Jan = funktionierender Prototyp auf Vercel, klickbar, in einer Woche.

### Vorgeschlagenes Paket für Philipp

**GTM-Konzept + Prototyp** (~3–4 Wochen)

| Deliverable | Was Jan liefert | Format |
|---|---|---|
| Competitor-Analyse | Top 5–8 Wettbewerber, Positionierungsmatrix, Differenzierung | MD/PDF |
| Personas | 2–3 Personas (Lehrkraft, Nachhilfelehrer, Schüler/Elternteil) mit Jobs-to-be-done | MD/PDF |
| Positionierung | Unique Value Proposition, Messaging je Zielgruppe | MD/PDF |
| Monetarisierung | Preismodelle (B2C Abo, B2B Lizenz, Freemium) mit Empfehlung | MD/PDF |
| Funnel-Strategie | Acquisition → Activation → Retention je Zielgruppe | MD/PDF |
| Landingpage | Funktionierender Prototyp (Lovable/Vercel), nicht nur Mockup | Live URL |
| KPI-Framework | Metriken, Tracking-Setup (auf bestehendem query_log aufbauend) | MD + Code |
| Kanalstrategie | Organic (SEO/Content), Paid, Kooperationen mit konkreten Empfehlungen | MD/PDF |

**Zeitplan:** Ab Sonntag (Jan zurück vom Schiff) → Kick-off → Lieferung in 3–4 Wochen

---

## Email-Thread Zusammenfassung (Stand 2026-03-24)

| Datum | Von | Inhalt |
|---|---|---|
| 23.03. | Jan | Fragt nach Agentur-Projekten, bietet GTM-Hilfe an |
| 23.03. | Philipp | Schickt unterschriebenes NDA |
| 24.03. | Philipp | Schickt vollständigen RFP (wie an andere Agenturen) |
| 24.03. | Jan | Bestätigt GTM-Kompetenz + Track Record, bis Samstag auf Schiff, ab Sonntag verfügbar |

**Status:** Philipp wartet auf Jans konkretes Angebot. Jan muss nach der Rückkehr (ab Sonntag) ein strukturiertes Proposal mit Deliverables und Preis liefern — schneller als die Agenturen.

---

## Offene Fragen für nächstes Gespräch

1. **Zweiseitiger Marktplatz:** Wie weit ist die Schüler/Eltern-Seite entwickelt? Was sehen Schüler in der App?
2. **Budget:** Was ist Philipps Budget für das GTM-Projekt? (Fördergelder, ~1,5 Monate)
3. **Timing:** Wann will er mit dem Markteintritt starten — April? Wann läuft die Förderung aus?
4. **Agenturen:** Mit wie vielen spricht er noch? Was ist sein Entscheidungskriterium?
5. **Landingpage:** Existiert bereits eine Website oder muss alles neu gebaut werden?
