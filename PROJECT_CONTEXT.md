# PROJECT_CONTEXT — MiroShark (S2S für Bazodiac)

> **Zweck dieser Datei:** Persistente Projektmanager-Ebene — Ziel, Stand, offene
> Stränge, Entscheidungen. Bewusst getrennt von `CLAUDE.md` (Dev-/Code-Ebene) und
> liegt im Git-Repo, damit sie keinen App-Absturz teilt. Hier wird laufend
> fortgeschrieben. Rekonstruiert am 2026-06-02 aus README, CLAUDE.md und
> `architecture/architecture-snapshot.md` (2026-05-29).

## Was es ist

MiroShark ist eine Swarm-Intelligence-Engine: Ein Szenario (Headline, Policy-Draft,
What-if) wird eingegeben, hunderte AI-Agenten simulieren Stunde für Stunde
Social-Media-Reaktionen über Twitter, Reddit und einen Prediction-Market, Ergebnis
ist ein strukturierter Report mit Zitaten simulierter Posts und Trades.

## Rolle im Bazodiac-Ökosystem (das eigentliche Ziel)

MiroShark wird als **Scenario-Simulation-Service für Pattern-Amp / Bazodiac**
betrieben (S2S = Service-to-Service). Aufgabenteilung:

- **Bazodiac** besitzt Supabase-Zugriff, kondensiert pro User die Daten zu einer
  `ScenarioSeed.md` (User Base Context, Pattern Context = sieben Eve-Hypothesen,
  Temporal Context), normalisiert MiroSharks Output zu `ScenarioBranchV1[]`.
- **MiroShark** bleibt domänen-neutral: bekommt **nur** `ScenarioSeed.md` +
  invarianten Generic Scenario Prompt + Simulation Config — nie rohe Supabase-Tabellen
  oder Service-Keys — und liefert Simulation + Report zurück.

Ziel ist **kein** objektives Forecasting, sondern Simulation von Pattern-Dynamik:
was verstärkt sich, was kann kippen, wo entsteht Spannung, wo sind beeinflussbare
Entscheidungspunkte ("Enabling Your Destiny").

## Aktueller Stand (Stand 2026-05-29 laut Snapshot)

- **Live (Staging):** Cloud Run, `https://miroshark-api-zul335dpla-ew.a.run.app`
  (europe-west1, GCP-Projekt `bazodiac`). Zusätzlich Railway-Staging via
  `Dockerfile.railway` + `railway.json`.
- **Aktiver Integrationsweg Bazodiac→MiroShark:** läuft heute über die generischen
  Endpunkte `/api/simulation/prepare → start → run-status` + `/api/report/...`,
  Normalisierung zu Branches passiert auf Bazodiac-Seite.
- **Geplant (noch nicht gebaut):** schlanke `/api/scenario`-Fassade auf MiroShark
  (1× submit + 2× poll) statt des manuellen prepare→start→status→report-Tanzes;
  sowie `scenario_*`-Tabellen auf Supabase für Run-Lifecycle, Dedupe (`trigger_key`)
  und Wiederholbarkeit.

## Architektur in Kürze

`Vue 3 SPA (:3000) → Flask Backend (:5001) → Neo4j (:7687)`. Simulation läuft als
**Subprozess** (`simulation_runner.py`), IPC zum Subprozess über Dateisystem-Polling
(`commands/` + `responses/`). `wonderwall/` (camel-oasis-Fork) ist **in-tree
gebündelt**, kein PyPI-Paket. Persistenz nur Neo4j (Singleton `Neo4jStorage`, 503 bei
Ausfall). LLM zweistufig: `LLM_*` (günstig, Default Mimo V2 Flash) + optional
`SMART_*` (stark, Reports/Ontologie, Default Gemini 3 Flash).

## Offene Punkte / nächste Schritte (rekonstruiert)

- [ ] `/api/scenario`-Fassade implementieren (siehe Contract in
      `architecture/architecture-snapshot.md` §7.2).
- [ ] `scenario_*`-Persistenztabellen auf Supabase-Seite anlegen.
- [ ] Doku-Diskrepanz klären: `CLAUDE.md` sagt IPC = Dateisystem-Polling,
      der Snapshot sagt an einer Stelle "socket IPC". Eine Quelle korrigieren.
- [ ] Offene Markdown-Notizen im Repo-Root sichten (z. B.
      `1_tabellen_...md`, `2_fehlende_tabellen_fuer_scenario_runs...md`,
      `miroshark_scenario_seed_pattern_amp_base_scenario.md`) — enthalten
      vermutlich Teile des verlorenen Planungskontexts.

## Entscheidungs-Log

> Format: `JJJJ-MM-TT — Entscheidung — kurze Begründung`. Bitte fortschreiben.

- _(noch keine Einträge — ab hier mitschreiben)_

## Nicht rekonstruierbar (bitte ergänzen)

Die folgenden Dinge lagen nur in den verlorenen Cowork-Chats und sind **nicht** aus
dem Code ableitbar — bitte aus dem Gedächtnis nachtragen, wenn möglich:

- Woran zuletzt konkret gearbeitet wurde / nächster geplanter Schritt.
- Offene Design-Entscheidungen, die noch nicht im Code stehen.
- Bekannte Bugs / Workarounds, die wir besprochen hatten.
