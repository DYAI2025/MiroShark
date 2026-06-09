#!/usr/bin/env bash
# ──────────────────────────────────────────────────────────
# MiroShark — OpenRouter interactive setup (idempotent)
#
# Interactive setup with full model selection for every slot:
#   LLM (default)   — persona gen, sim config, memory compaction
#   SMART           — reports, ontology extraction, graph reasoning
#   NER             — entity extraction (high-volume, mechanical)
#   WONDERWALL      — simulation loop (#1 cost driver, 850+ calls/run)
#   EMBEDDING       — vector embeddings
#   WEB_SEARCH      — web enrichment for persona research
#
# Usage:
#   bash scripts/local_setup_openrouter.sh
#   bash scripts/local_setup_openrouter.sh --non-interactive KEY
#
# ──────────────────────────────────────────────────────────
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

if [[ -t 1 ]]; then
  GREEN='\033[0;32m'; YELLOW='\033[0;33m'; CYAN='\033[0;36m'; RED='\033[0;31m'; BOLD='\033[1m'; RESET='\033[0m'
else GREEN='' YELLOW='' CYAN='' RED='' BOLD='' RESET=''; fi
info()    { printf "${CYAN}  [*]${RESET} %s\n" "$*"; }
success() { printf "${GREEN}  [+]${RESET} %s\n" "$*"; }
warn()    { printf "${YELLOW}  [!]${RESET} %s\n" "$*"; }
error()   { printf "${RED}  [-]${RESET} %s\n" "$*"; }
header()  { printf "\n${BOLD}  === %s ===${RESET}\n\n" "$*"; }

gen_key() {
  if command -v openssl >/dev/null 2>&1; then openssl rand -hex 32
  elif command -v python3 >/dev/null 2>&1; then python3 -c 'import secrets;print(secrets.token_hex(32))'
  else error "need openssl or python3 to generate a key"; exit 1; fi
}

# ── Default OpenRouter models ─────────────────────────────
DEFAULT_LLM="openai/gpt-4o-mini"
DEFAULT_SMART="google/gemini-2.5-flash-preview-04-17"
DEFAULT_NER="google/gemini-2.5-flash-preview-04-17"
DEFAULT_WONDERWALL="openai/gpt-4o-mini"
DEFAULT_EMBED="text-embedding-3-small"
DEFAULT_WEB_SEARCH=""

# ── Model categories with descriptions ────────────────────
declare -A MODEL_DESC
MODEL_DESC[LLM]="Default model — persona generation, sim config, memory compaction. Cheap & fast."
MODEL_DESC[SMART]="Strong model — reports, ontology extraction, graph reasoning. Optional, falls back to LLM."
MODEL_DESC[NER]="NER model — entity extraction (high-volume, mechanical JSON). Needs reliable JSON output."
MODEL_DESC[WONDERWALL]="Wonderwall — simulation loop. #1 cost driver (850+ calls/run). Keep it cheap!"
MODEL_DESC[EMBEDDING]="Embedding model — vector embeddings. Use OpenRouter or keep local Ollama."
MODEL_DESC[WEB_SEARCH]="Web search model — optional, for web enrichment (e.g. perplexity/sonar-pro)"

# ── Parse args ────────────────────────────────────────────
NON_INTERACTIVE=0
OR_KEY=""
for a in "$@"; do case "$a" in
  --non-interactive) NON_INTERACTIVE=1 ;;
  -h|--help) sed -n '3,15p' "$0"; exit 0 ;;
  *) if [[ -z "$OR_KEY" ]]; then OR_KEY="$a"; else echo "unknown arg: $a" >&2; exit 2; fi ;;
esac; done

# ── 1. Welcome & mode ─────────────────────────────────────
header "MiroShark — OpenRouter Setup"
echo "  This configures MiroShark to use OpenRouter (cloud LLMs)."
echo "  For local Ollama setup, run: bash scripts/local_setup.sh"
echo ""

# ── 2. OpenRouter API Key ─────────────────────────────────
header "OpenRouter API Key"
if [[ $NON_INTERACTIVE -eq 1 && -n "$OR_KEY" ]]; then
  API_KEY="$OR_KEY"
  success "Using provided API key"
else
  read -r -p "  Enter your OpenRouter API key (sk-or-...): " API_KEY
  API_KEY="${API_KEY:-}"
  if [[ -z "$API_KEY" ]]; then
    error "API key required. Get one at https://openrouter.ai/keys"
    exit 1
  fi
  success "API key set"
fi

# ── Validate key (optional ping) ──────────────────────────
info "Validating API key..."
VALID=$(curl -sS -o /dev/null -w "%{http_code}" \
  -H "Authorization: Bearer $API_KEY" \
  -H "Content-Type: application/json" \
  https://openrouter.ai/api/v1/models 2>/dev/null || echo "000")
if [[ "$VALID" = "200" || "$VALID" = "000" ]]; then
  if [[ "$VALID" = "200" ]]; then
    success "API key valid — OpenRouter reachable"
  else
    warn "Could not reach OpenRouter (offline?) — proceeding anyway. Fix key later in .env"
  fi
else
  warn "API key may be invalid (HTTP $VALID) — proceeding anyway"
fi

# ── 3. Model selection ────────────────────────────────────
header "Model Selection"
echo "  Choose models for each slot. Press Enter to accept defaults."
echo "  OpenRouter model IDs: https://openrouter.ai/models"
echo ""

pick_model() {
  local slot="$1"
  local desc="${MODEL_DESC[$slot]}"
  local default_var="DEFAULT_${slot}"
  local default="${!default_var}"
  local prompt="$slot [$desc]"
  local val=""

  read -r -p "  $prompt
    Model (default: $default): " val
  val="${val:-$default}"
  echo "$val"
}

LLM_MODEL=$(pick_model "LLM")
SMART_MODEL=$(pick_model "SMART")
NER_MODEL=$(pick_model "NER")
WONDERWALL_MODEL=$(pick_model "WONDERWALL")
EMBED_MODEL=$(pick_model "EMBEDDING")
WEB_SEARCH_MODEL=$(pick_model "WEB_SEARCH")

echo ""
success "Model selection complete:"
echo "    LLM:        $LLM_MODEL"
echo "    SMART:      $SMART_MODEL"
echo "    NER:        $NER_MODEL"
echo "    Wonderwall: $WONDERWALL_MODEL"
echo "    Embedding:  $EMBED_MODEL"
echo "    Web Search: ${WEB_SEARCH_MODEL:-<disabled>}"

# ── 4. Optional: Embedding provider ───────────────────────
header "Embedding Provider"
echo "  Use OpenRouter for embeddings, or keep local Ollama?"
echo "  1) OpenRouter ($EMBED_MODEL)"
echo "  2) Ollama (local — nomic-embed-text)"
read -r -p "  Choose [1/2] (default: 1): " EMB_CHOICE
EMB_CHOICE="${EMB_CHOICE:-1}"

if [[ "$EMB_CHOICE" = "2" ]]; then
  EMBEDDING_PROVIDER="ollama"
  EMBEDDING_MODEL="nomic-embed-text"
  EMBEDDING_BASE_URL="http://localhost:11434"
  EMBEDDING_API_KEY=""
  EMBEDDING_DIMENSIONS="768"
  EMBEDDING_BATCH_SIZE="128"
  success "Using local Ollama for embeddings"
else
  EMBEDDING_PROVIDER="openai"
  EMBEDDING_MODEL="$EMBED_MODEL"
  EMBEDDING_BASE_URL="https://openrouter.ai/api/v1"
  EMBEDDING_API_KEY="$API_KEY"
  EMBEDDING_DIMENSIONS="1536"
  EMBEDDING_BATCH_SIZE="128"
  success "Using OpenRouter for embeddings"
fi

# ── 5. Optional: Internal key ─────────────────────────────
header "Internal Key"
KEY="$(grep -E '^MIROSHARK_INTERNAL_KEY=' .env 2>/dev/null | head -1 | cut -d= -f2- | tr -d '[:space:]' || true)"
if [[ -z "$KEY" ]]; then
  KEY="$(gen_key)"
  info "Generated new internal key"
else
  success "Reusing existing internal key from .env"
fi

# ── 6. Write .env ─────────────────────────────────────────
header "Writing .env"
cat > .env <<EOF
# Generated by scripts/local_setup_openrouter.sh — OpenRouter stack.
NEO4J_URI=bolt://localhost:7687
NEO4J_USER=neo4j
NEO4J_PASSWORD=miroshark

# ── Default LLM (persona gen, sim config, memory compaction) ──
LLM_PROVIDER=openai
LLM_API_KEY=${API_KEY}
LLM_BASE_URL=https://openrouter.ai/api/v1
LLM_MODEL_NAME=${LLM_MODEL}

# ── Smart model — reports, ontology, graph reasoning (stronger, optional) ──
SMART_PROVIDER=openai
SMART_API_KEY=${API_KEY}
SMART_BASE_URL=https://openrouter.ai/api/v1
SMART_MODEL_NAME=${SMART_MODEL}

# ── NER model — entity extraction (high-volume, mechanical JSON) ──
NER_MODEL_NAME=${NER_MODEL}
NER_BASE_URL=https://openrouter.ai/api/v1
NER_API_KEY=${API_KEY}

# ── Wonderwall model — simulation loop (#1 cost driver, keep cheap!) ──
WONDERWALL_MODEL_NAME=${WONDERWALL_MODEL}
WONDERWALL_API_KEY=${API_KEY}
WONDERWALL_BASE_URL=https://openrouter.ai/api/v1

# ── Embeddings ──
EMBEDDING_PROVIDER=${EMBEDDING_PROVIDER}
EMBEDDING_MODEL=${EMBEDDING_MODEL}
EMBEDDING_BASE_URL=${EMBEDDING_BASE_URL}
EMBEDDING_API_KEY=${EMBEDDING_API_KEY}
EMBEDDING_DIMENSIONS=${EMBEDDING_DIMENSIONS}
EMBEDDING_BATCH_SIZE=${EMBEDDING_BATCH_SIZE}

# ── Reranker ──
RERANKER_ENABLED=true
RERANKER_MODEL=BAAI/bge-reranker-v2-m3
RERANKER_CANDIDATES=30

# ── Web enrichment — optional OpenRouter model for persona research ──
WEB_SEARCH_MODEL=${WEB_SEARCH_MODEL}

# ── Graph search ──
GRAPH_SEARCH_ENABLED=true
GRAPH_SEARCH_HOPS=1
GRAPH_SEARCH_SEEDS=5

# ── Entity resolution ──
ENTITY_RESOLUTION_ENABLED=true
ENTITY_RESOLUTION_USE_LLM=true

# ── Contradiction detection ──
CONTRADICTION_DETECTION_ENABLED=true

# ── Communities ──
COMMUNITY_MIN_SIZE=3
COMMUNITY_MAX_COUNT=30

# ── Reasoning trace ──
REASONING_TRACE_ENABLED=true

# ── Opt-out of OpenRouter chain-of-thought (huge latency win) ──
LLM_DISABLE_REASONING=true

# ── Prompt caching ──
LLM_PROMPT_CACHING_ENABLED=true

# ── Report agent ──
REPORT_AGENT_MAX_TOOL_CALLS=5
REPORT_AGENT_MAX_REFLECTION_ROUNDS=2
REPORT_AGENT_TEMPERATURE=0.5

# ── Flask ──
FLASK_DEBUG=true
SECRET_KEY=miroshark-local-dev
OLLAMA_NUM_CTX=8192

# ── Internal auth ──
MIROSHARK_INTERNAL_KEY=${KEY}
EOF
success ".env written with OpenRouter configuration"

# ── 7. Frontend .env.local ────────────────────────────────
header "Frontend config (frontend/.env.local)"
FE=frontend/.env.local
FE_KEY="$(grep -E '^VITE_INTERNAL_KEY=' "$FE" 2>/dev/null | head -1 | cut -d= -f2- | tr -d '[:space:]' || true)"
if [[ -f "$FE" && "$FE_KEY" == "$KEY" ]]; then
  success "$FE present — keeping it"
else
  cat > "$FE" <<EOF
VITE_API_BASE_URL=http://localhost:5001
VITE_INTERNAL_KEY=${KEY}
EOF
  success "wrote $FE (localhost:5001, key matched to backend)"
fi

# ── 8. Dependencies ───────────────────────────────────────
header "Dependencies"
info "Running npm run setup:all ..."
if npm run setup:all; then
  success "Dependencies installed"
else
  warn "setup:all failed — run it manually: npm run setup:all"
fi

# ── 9. Show OpenRouter model list ─────────────────────────
header "Available OpenRouter Models (Top 30)"
curl -sS -H "Authorization: Bearer $API_KEY" \
  "https://openrouter.ai/api/v1/models" \
  2>/dev/null | python3 -c "
import json, sys
try:
  data = json.load(sys.stdin)
  models = data.get('data', [])
  # Sort by some reasonable metric
  models.sort(key=lambda m: m.get('id', ''))
  for i, m in enumerate(models[:30]):
    print(f'  {i+1:2d}. {m[\"id\"]}')
  if len(models) > 30:
    print(f'  ... and {len(models)-30} more')
except:
  print('  (could not fetch model list)')
" || warn "Could not fetch model list from OpenRouter"

# ── Done ──────────────────────────────────────────────────
header "Done"
success "OpenRouter setup complete!"
echo ""
echo "  LLM:        $LLM_MODEL"
echo "  SMART:      $SMART_MODEL"
echo "  NER:        $NER_MODEL"
echo "  Wonderwall: $WONDERWALL_MODEL"
echo "  Embeddings: ${EMBEDDING_PROVIDER} (${EMBEDDING_MODEL})"
echo "  Web Search: ${WEB_SEARCH_MODEL:-disabled}"
echo ""
success "Start the stack:  npm run dev"
success "Open:             http://localhost:3000  → Settings → LLM Connection Test"
echo ""
echo "  To switch back to local Ollama:  bash scripts/local_setup.sh"
echo "  To re-run this setup:            bash scripts/local_setup_openrouter.sh"
