# Manual Test Run — Pattern-Amp Seed durch MiroShark

Dieses Kit fährt einen **echten End-to-End-Lauf** gegen ein laufendes MiroShark-Backend
über den **aktuellen Pfad** (es gibt noch keinen `/api/scenario`-Endpunkt — siehe `architecture/`).

## Dateien

| Datei | Rolle | Geht an |
|---|---|---|
| `scenario_seed.md` | das **WAS** (User-Muster, Hypothesen, Kontext) | Upload-Datei für `ontology/generate` |
| `generic_scenario_prompt.md` | das **WIE** (invariante Regeln) | `additional_context` |
| `simulation_config.json` | mode/horizon/branch-counts | Referenz (V1 nicht nativ von der API gelesen) |
| `trigger_source.json` | Trigger + `trigger_key` (Dedupe) | Referenz |
| `data_completeness.json` | Vollständigkeitsreport | Referenz |
| `run_manual_test.sh` | curl-Pipeline gegen die echten Endpunkte | — |
| `report_output.json` | wird vom Script erzeugt (Ergebnis) | — |

## Voraussetzungen

1. Backend läuft: `./miroshark` **oder** `cd backend && uv run python run.py` (Flask :5001).
2. Neo4j (:7687) erreichbar, `LLM_*` (und idealerweise `SMART_*`) in `.env` gesetzt —
   ontology/build/prepare/report rufen alle das LLM.
3. `jq` und `curl` installiert.

## Ausführen

```bash
cd scenario-test-run
export MIROSHARK_API_URL=http://localhost:5001      # oder Cloud-Run-URL
export MIROSHARK_INTERNAL_KEY=...                   # NUR falls Backend den Key erzwingt
# optional: export MAX_ROUNDS=20   POLL_SECONDS=5
bash run_manual_test.sh
```

Das Script druckt jeden Schritt und schreibt am Ende `report_output.json`.

## Pipeline (aus dem Code verifiziert)

1. `POST /api/graph/ontology/generate` (multipart) → `project_id` + Ontologie
2. `POST /api/graph/build` → `task_id`; pollt `GET /api/graph/task/:task_id`
3. `POST /api/simulation/create` → `simulation_id`
4. `POST /api/simulation/prepare` → pollt `POST /api/simulation/prepare/status`
5. `POST /api/simulation/start` (`max_rounds`)
6. pollt `GET /api/simulation/:id/run-status`
7. `POST /api/report/generate` → pollt `GET /api/report/check/:id`
8. `GET /api/report/by-simulation/:id` → `report_output.json`

## Was der Test beweist — und was NICHT

**Beweist:** MiroShark kann einen Pattern-Amp-Seed ingestieren und einen strukturierten
Report end-to-end erzeugen (das S2S-**Plumbing** trägt).

**Beweist NICHT:**
- MiroShark gibt **kein** `ScenarioBranchV1[]` zurück. Der Output ist ein MiroShark-Report
  (Social-Reaction-Simulation über Twitter/Reddit-Agenten). Die Umwandlung in Branches ist
  der **geplante Normalizer auf Bazodiac-Seite** (offener Punkt aus dem Architektur-Snapshot).
- `simulation_config.json` (mode/horizon) wird vom heutigen `/api/simulation` **nicht nativ**
  gelesen — es ist Teil des künftigen `/api/scenario`-Vertrags. Hier dient es als Referenz.
- Die MiroShark-Agenten simulieren *soziale Reaktionen* auf den Seed-Inhalt; das ist ein
  Proxy für Musterdynamik, nicht die native Pattern-Amp-Logik.

Kurz: Dieser Lauf validiert die **Schnittstellen-Mechanik und die Datenübergabe**, nicht das
finale Branch-Format. Genau diese Lücke (Output → ScenarioBranchV1) ist der nächste Designschritt.

## Fehlerbilder

- `503` bei graph/prepare → Neo4j nicht initialisiert.
- Hänger bei ontology/build/prepare → `LLM_*` fehlt/falsch in `.env`.
- `401/403` → Backend erzwingt `MIROSHARK_INTERNAL_KEY`; Env setzen.
- Status-Strings können je nach Version abweichen — Script bricht bei `failed|error` ab und
  druckt die Roh-Antwort; Polling-`case`-Zweige ggf. an reale Werte anpassen.
