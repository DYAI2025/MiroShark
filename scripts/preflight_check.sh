#!/usr/bin/env bash
# Preflight check for MiroShark — validates environment before simulation runs.
# Usage: ./scripts/preflight_check.sh
# Exit code: 0 = all good, 1 = warnings, 2 = fatal errors

set -o pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
ENV_FILE="$ROOT/.env"
PASS=0 WARN=0 FAIL=0

pass() { PASS=$((PASS+1)); echo "  ✓ $1"; }
warn() { WARN=$((WARN+1)); echo "  ⚠ $1"; }
fail() { FAIL=$((FAIL+1)); echo "  ✗ $1"; }

# --- helpers ---
source_env() {
  if [ -f "$ENV_FILE" ]; then
    set -a; source "$ENV_FILE"; set +a
  fi
}
source_env

ollama_running_on() {
  local port="$1"
  curl -sf --max-time 3 "http://localhost:${port}/api/version" >/dev/null 2>&1
}

echo "══════════════════════════════════════"
echo "  MiroShark Preflight Check"
echo "══════════════════════════════════════"
echo ""

# ── 1. Essential env vars ──────────────────────────────────────────
echo "── Env vars ───────────────────────────────────"
[ -n "${LLM_API_KEY:-}" ]   && pass "LLM_API_KEY set"         || fail "LLM_API_KEY missing"
[ -n "${LLM_BASE_URL:-}" ]  && pass "LLM_BASE_URL=$LLM_BASE_URL" || fail "LLM_BASE_URL missing"
[ -n "${LLM_MODEL_NAME:-}" ]&& pass "LLM_MODEL_NAME=$LLM_MODEL_NAME" || fail "LLM_MODEL_NAME missing"
[ -n "${NEO4J_URI:-}" ]     && pass "NEO4J_URI=$NEO4J_URI"   || fail "NEO4J_URI missing"
[ -n "${NEO4J_PASSWORD:-}" ]&& pass "NEO4J_PASSWORD set"      || fail "NEO4J_PASSWORD missing"

# ── 2. Ollama ──────────────────────────────────────────────────────
echo ""
echo "── Ollama ────────────────────────────────────"
LLM_PORT="${LLM_BASE_URL##*:}"
LLM_PORT="${LLM_PORT%/v1}"
if ollama_running_on "$LLM_PORT"; then
  VER=$(curl -sf --max-time 3 "http://localhost:${LLM_PORT}/api/version" | python3 -c "import sys,json; print(json.load(sys.stdin).get('version','?'))" 2>/dev/null)
  pass "Ollama on :$LLM_PORT (v$VER)"
else
  fail "Ollama not found on :$LLM_PORT"
fi

# GPU check via Ollama
if command -v nvidia-smi &>/dev/null; then
  GPU_INFO=$(nvidia-smi --query-gpu=name,memory.total,memory.free --format=csv,noheader 2>/dev/null | head -1)
  if [ -n "$GPU_INFO" ]; then
    pass "GPU: $GPU_INFO"
  else
    warn "nvidia-smi available but no GPU info"
  fi
else
  warn "nvidia-smi not found — GPU check skipped"
fi

# Model loaded?
if [ -n "${LLM_MODEL_NAME:-}" ]; then
  MODEL_OK=$(curl -sf --max-time 5 "http://localhost:${LLM_PORT}/api/show" \
    -d "{\"model\":\"$LLM_MODEL_NAME\"}" 2>/dev/null | python3 -c "import sys,json; d=json.load(sys.stdin); print('ok' if d.get('modelfile') else 'no')" 2>/dev/null)
  if [ "$MODEL_OK" = "ok" ]; then
    pass "Model $LLM_MODEL_NAME available"
  else
    fail "Model $LLM_MODEL_NAME not found — run: ollama pull $LLM_MODEL_NAME"
  fi
fi

# ── 3. Timeout sanity ──────────────────────────────────────────────
echo ""
echo "── Timeouts ──────────────────────────────────"
MODEL_TO="${MODEL_TIMEOUT:-180}"
ROUND_TO="${MIROSHARK_ROUND_TIMEOUT:-900}"
[ "$MODEL_TO" -ge 60 ]      && pass "MODEL_TIMEOUT=$MODEL_TO (≥60s)" || fail "MODEL_TIMEOUT too low: $MODEL_TO"
[ "$ROUND_TO" -ge 300 ]     && pass "MIROSHARK_ROUND_TIMEOUT=$ROUND_TO (≥300s)" || fail "MIROSHARK_ROUND_TIMEOUT too low: $ROUND_TO"
if [ "$ROUND_TO" -le "$MODEL_TO" ]; then
  warn "Round timeout ($ROUND_TO) ≤ Model timeout ($MODEL_TO) — agents will time out together"
else
  pass "Round timeout > Model timeout (margin: $((ROUND_TO - MODEL_TO))s)"
fi

# ── 4. Neo4j ───────────────────────────────────────────────────────
echo ""
echo "── Neo4j ────────────────────────────────────"
if command -v cypher-shell &>/dev/null; then
  cypher-shell -a "${NEO4J_URI:-bolt://localhost:7687}" \
    -u "${NEO4J_USER:-neo4j}" -p "${NEO4J_PASSWORD}" \
    "RETURN 1 AS ok" --format plain 2>/dev/null | grep -q "ok" && \
    pass "Neo4j reachable" || fail "Neo4j connection failed"
else
  # fallback: check via HTTP
  NEO_PORT="${NEO4J_URI##*:}"
  curl -sf --max-time 3 "http://localhost:${NEO_PORT}/" >/dev/null 2>&1 && \
    pass "Neo4j port :$NEO_PORT open" || warn "Neo4j port unverified (install cypher-shell for full check)"
fi

# ── 5. Backend API ─────────────────────────────────────────────────
echo ""
echo "── Backend ───────────────────────────────────"
BACKEND_PORT=5001
HTTP_CODE=$(curl -s -o /dev/null -w "%{http_code}" --max-time 5 "http://localhost:${BACKEND_PORT}/" 2>&1)
if [ "$HTTP_CODE" != "000" ]; then
  pass "Backend on :$BACKEND_PORT (HTTP $HTTP_CODE)"
else
  fail "Backend not responding on :$BACKEND_PORT — start with: npm run dev"
fi

# ── 6. Ollama parallelism ──────────────────────────────────────────
echo ""
echo "── Parallelism ───────────────────────────────"
NP="${OLLAMA_NUM_PARALLEL:-1}"
[ "$NP" -ge 2 ] && pass "OLLAMA_NUM_PARALLEL=$NP (≥2)" || warn "OLLAMA_NUM_PARALLEL=$NP — agents may bottleneck"

# ── 7. WONDERWALL fallback env ─────────────────────────────────────
echo ""
echo "── Wonderwall ────────────────────────────────"
[ -n "${WONDERWALL_MODEL_NAME:-}" ] && pass "WONDERWALL_MODEL_NAME set"  || warn "WONDERWALL_MODEL_NAME unset (uses LLM fallback)"
[ -n "${WONDERWALL_BASE_URL:-}" ]   && pass "WONDERWALL_BASE_URL set"    || warn "WONDERWALL_BASE_URL unset (uses LLM fallback)"

echo ""
echo "══════════════════════════════════════"
echo "  $PASS passed, $WARN warnings, $FAIL failures"
echo "══════════════════════════════════════"

# Non-zero exit for failures
[ "$FAIL" -eq 0 ] && exit 0 || exit 2