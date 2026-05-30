#!/usr/bin/env bash
# ---------------------------------------------------------------------------
# Manual end-to-end test run against a LIVE MiroShark backend.
# Drives the REAL current-path pipeline (verified against backend/app/api/*.py):
#   ontology/generate -> graph/build -> simulation/create -> prepare -> start
#   -> run-status -> report/generate -> report/by-simulation
#
# This exercises the S2S PLUMBING: can MiroShark ingest a ScenarioSeed and
# produce a structured report end-to-end? It does NOT yet emit ScenarioBranchV1[]
# (that is the planned normalizer on the Bazodiac side — see architecture/).
#
# Requirements:
#   - MiroShark backend running (default :5001) with Neo4j up + LLM_* configured.
#   - jq + curl installed.
#   - Run from this folder:  bash run_manual_test.sh
#
# Config via env (no secrets in this file):
#   export MIROSHARK_API_URL=http://localhost:5001        # or your Cloud Run URL
#   export MIROSHARK_INTERNAL_KEY=...                      # only if backend enforces it
# ---------------------------------------------------------------------------
set -euo pipefail

API="${MIROSHARK_API_URL:-http://localhost:5001}"
KEY="${MIROSHARK_INTERNAL_KEY:-}"
HERE="$(cd "$(dirname "$0")" && pwd)"
MAX_ROUNDS="${MAX_ROUNDS:-20}"        # keep the test short; raise for a fuller run
POLL_SECONDS="${POLL_SECONDS:-5}"

# header args (only send the key header if set)
hdr=(-H "Content-Type: application/json")
[ -n "$KEY" ] && hdr+=(-H "x-miroshark-internal-key: $KEY")
khdr=()
[ -n "$KEY" ] && khdr+=(-H "x-miroshark-internal-key: $KEY")

say(){ printf '\n\033[1;36m== %s\033[0m\n' "$*"; }
post(){ curl -sS -X POST "${hdr[@]}" -d "$2" "$API$1"; }
get(){ curl -sS "${khdr[@]}" "$API$1"; }

# ---------------------------------------------------------------------------
say "0) Health check"
get /api/mcp/status >/dev/null && echo "backend reachable at $API"

# ---------------------------------------------------------------------------
say "1) Create project + ontology (multipart: seed file + requirement + prompt)"
SIM_REQ="$(cat <<'EOF'
Simulate user-relative pattern dynamics from the attached Scenario Seed.
Do NOT predict external events, do NOT diagnose, do NOT treat astrology as causal.
Model the seven working hypotheses as interacting tendencies under the current
temporal field and return 3 to 7 scenario branches (amplification, interruption,
coherence shift, tension shift, integration, risk, stabilization). Each branch must
carry confidence, relatedHypothesisIds, sourceWeights, coherence/tension delta,
notToInfer and a reflective question.
EOF
)"
GENERIC_PROMPT="$(cat "$HERE/generic_scenario_prompt.md")"

ONTO=$(curl -sS -X POST "${khdr[@]}" \
  -F "files=@$HERE/scenario_seed.md;type=text/markdown" \
  -F "project_name=PatternAmp Manual Test" \
  -F "simulation_requirement=$SIM_REQ" \
  -F "additional_context=$GENERIC_PROMPT" \
  "$API/api/graph/ontology/generate")
echo "$ONTO" | jq '.success, .data.project_id, (.data.ontology.entity_types|length)'
PROJECT_ID=$(echo "$ONTO" | jq -r '.data.project_id')
[ "$PROJECT_ID" = "null" ] && { echo "ontology/generate failed:"; echo "$ONTO"; exit 1; }

# ---------------------------------------------------------------------------
say "2) Build graph (async) + poll task"
BUILD=$(post /api/graph/build "{\"project_id\":\"$PROJECT_ID\"}")
TASK_ID=$(echo "$BUILD" | jq -r '.data.task_id')
echo "graph build task: $TASK_ID"
while :; do
  T=$(get "/api/graph/task/$TASK_ID")
  ST=$(echo "$T" | jq -r '.data.status // .status // "unknown"')
  echo "  graph task status: $ST"
  case "$ST" in completed|success|done|GRAPH_COMPLETED) break;; failed|error) echo "$T"; exit 1;; esac
  sleep "$POLL_SECONDS"
done

# ---------------------------------------------------------------------------
say "3) Create simulation"
CREATE=$(post /api/simulation/create "{\"project_id\":\"$PROJECT_ID\",\"enable_twitter\":true,\"enable_reddit\":true,\"enable_polymarket\":false}")
SIM_ID=$(echo "$CREATE" | jq -r '.data.simulation_id')
echo "simulation_id: $SIM_ID"
[ "$SIM_ID" = "null" ] && { echo "$CREATE"; exit 1; }

# ---------------------------------------------------------------------------
say "4) Prepare (config + agent profiles, async) + poll"
post /api/simulation/prepare "{\"simulation_id\":\"$SIM_ID\"}" | jq '.data.status, .data.message'
while :; do
  P=$(post /api/simulation/prepare/status "{\"simulation_id\":\"$SIM_ID\"}")
  ST=$(echo "$P" | jq -r '.data.status // "unknown"')
  echo "  prepare status: $ST"
  case "$ST" in ready|completed|success) break;; failed|error) echo "$P"; exit 1;; esac
  sleep "$POLL_SECONDS"
done

# ---------------------------------------------------------------------------
say "5) Start simulation (max_rounds=$MAX_ROUNDS)"
post /api/simulation/start "{\"simulation_id\":\"$SIM_ID\",\"platform\":\"parallel\",\"max_rounds\":$MAX_ROUNDS}" | jq '.data.runner_status, .data.process_pid'

say "6) Poll run-status until finished"
while :; do
  R=$(get "/api/simulation/$SIM_ID/run-status")
  ST=$(echo "$R" | jq -r '.data.status // .data.runner_status // "unknown"')
  RND=$(echo "$R" | jq -r '.data.current_round // "?"')
  echo "  run status: $ST (round $RND)"
  case "$ST" in completed|finished|stopped|done) break;; failed|error) echo "$R"; exit 1;; esac
  sleep "$POLL_SECONDS"
done

# ---------------------------------------------------------------------------
say "7) Generate report (async) + poll"
post /api/report/generate "{\"simulation_id\":\"$SIM_ID\"}" | jq '.data.status, .data.report_id'
while :; do
  C=$(get "/api/report/check/$SIM_ID")
  ST=$(echo "$C" | jq -r '.data.status // .status // "unknown"')
  echo "  report status: $ST"
  case "$ST" in completed|ready|success) break;; failed|error) echo "$C"; exit 1;; esac
  sleep "$POLL_SECONDS"
done

# ---------------------------------------------------------------------------
say "8) Fetch final report -> report_output.json"
get "/api/report/by-simulation/$SIM_ID" | tee "$HERE/report_output.json" | jq '.success, .data.report_id, (.data.sections|length?)'
echo
echo "DONE. project=$PROJECT_ID simulation=$SIM_ID  ->  $HERE/report_output.json"
echo "Next: normalize report_output.json to ScenarioBranchV1[] (Bazodiac-side normalizer)."
