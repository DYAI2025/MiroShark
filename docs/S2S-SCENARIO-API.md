# S2S Scenario API — headless `POST /api/scenario`

Service-to-Service entry point for Bazodiac → MiroShark. One call ingests a
`ScenarioSeed` and returns a job handle; the caller polls one URL for the
finished report. Replaces the 8-call manual chain
(`scenario-test-run/run_manual_test.sh`) with a single server-side orchestration.

## Endpoints

### `POST /api/scenario`

Request (JSON):

| Field | Type | Required | Default | Notes |
|-------|------|----------|---------|-------|
| `seed` | string | **yes** | — | ScenarioSeed.md content (min 50 chars). Travels into the pipeline as a `url_docs` text entry — no file upload. |
| `requirement` | string | no | neutral default | Framing for the simulation (the `simulation_requirement`). |
| `generic_prompt` | string | no | `""` | Invariant rules → `additional_context`. |
| `max_rounds` | int | no | `10` | 1..200. |
| `platforms` | string[] | no | `["twitter","reddit"]` | Subset of `twitter`, `reddit`, `polymarket`. |

Headers: `x-miroshark-internal-key: <key>` when the deployment enforces it.

Response `202`:

```json
{ "success": true, "data": { "job_id": "78463195f56c434e852e76c1ef1e6f74", "status": "running" } }
```

Validation errors return `400` (`seed` too short, bad `max_rounds`, bad `platforms`).

### `GET /api/scenario/<job_id>`

```json
{ "success": true, "data": {
    "job_id": "...",
    "status": "running | completed | failed",
    "stage":  "queued | ontology | graph_build | create | prepare | simulate | report | done",
    "project_id": "miroshark_xxxx | null",
    "simulation_id": "sim_xxxx | null",
    "report": { ... } ,          // present only when status == completed
    "error":  "string | null"     // present only when status == failed; names the failing stage
} }
```

Unknown `job_id` → `404`.

## What it orchestrates

The same verified current-path chain, server-side:

```
ontology/generate → graph/build (poll) → simulation/create → prepare (poll)
  → start → run-status (poll) → report/generate (poll) → report/by-simulation
```

`stage` mirrors that sequence so a caller can show progress.

## Limits and honest boundaries

- **Output is a MiroShark report**, not `ScenarioBranchV1[]`. Normalization to
  branches stays on the Bazodiac side (see `architecture/`).
- **In-memory job index**: single-instance. The report itself persists in Neo4j
  (keyed by `simulation_id`), but the `job_id → state` map is per-process. A
  horizontally-scaled deployment must move the index to shared storage.
- **Runtime tracks the model.** On the local Ollama preset (Gemma4) a full run
  is minutes-to-tens-of-minutes (ontology design + per-chunk NER + per-entity
  persona generation + rounds + report, all sequential). Use a fast cloud
  `LLM_*`/`SMART_*` tier for production S2S latency.
- No payload-supplied `verifyCommand`-style hooks; `seed`/`requirement`/
  `generic_prompt` are treated as content only.

## Example

```bash
curl -sS -X POST "$MIROSHARK_API_URL/api/scenario" \
  -H "x-miroshark-internal-key: $KEY" -H "Content-Type: application/json" \
  -d "$(jq -n --rawfile s ScenarioSeed.md '{seed:$s, max_rounds:10, platforms:["twitter","reddit"]}')"
# -> { "data": { "job_id": "JOB", "status": "running" } }

# poll
curl -sS "$MIROSHARK_API_URL/api/scenario/JOB" -H "x-miroshark-internal-key: $KEY" | jq '.data | {status, stage}'
```
