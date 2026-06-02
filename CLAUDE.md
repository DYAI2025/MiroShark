# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What it is

MiroShark is a "swarm intelligence engine" — drop in a scenario (news headline, policy draft, historical what-if) and it spawns hundreds of AI agents that simulate social media reactions hour by hour across Twitter, Reddit, and a prediction market. The result is a structured report citing simulated posts and trades.

## Dev commands

### Start everything (recommended)
```bash
./miroshark          # bash launcher — starts Neo4j, backend, frontend
```

### Dev with hot-reload
```bash
npm run dev          # concurrently starts backend (uv) + frontend (vite)
```

### Backend only
```bash
cd backend && uv run python run.py     # Flask on :5001
```

### Frontend only
```bash
cd frontend && npm run dev             # Vite on :3000
```

### Setup
```bash
npm run setup:all    # npm install + cd frontend && npm install + uv sync
```

### Tests
```bash
cd backend && uv run pytest            # unit tests (default)
cd backend && uv run pytest -m integration   # needs live backend at $MIROSHARK_API_URL
cd backend && uv run pytest tests/test_unit_foo.py   # single file (path relative to backend/)
```

## Architecture

### Request flow
```
Browser → Vue 3 SPA (Vite, :3000) → /api/* → Flask backend (:5001) → Neo4j (:7687)
```

All `/api/*` routes require `x-miroshark-internal-key` header when `MIROSHARK_INTERNAL_KEY` env var is set. In `DEBUG=true`, key enforcement is relaxed.

### Backend (Flask, `backend/`)

- **Entry**: `run.py` → `app/__init__.py` (Flask factory)
- **Config**: `app/config.py` — reads from `MiroShark/.env` (project root)
- **Blueprints** live in `app/api/` (registered in `__init__.py`):
  - `/api/simulation` — create/start/stop/status, per-round frame scrubbing
  - `/api/graph` — Neo4j graph operations
  - `/api/report` — report generation
  - `/api/templates` — preset simulation templates
  - `/api/settings` — user settings
  - `/api/observability` — trace/debug data
  - `/api/mcp` — MCP server bridge
  - `/api/feed` — Atom/RSS syndication
  - `/api/countries` — country registry for demographic grounding
  - `/api/docs` — API docs
  - `/api/notifications` — webhook/push/email/Slack/Telegram/Discord notify
  - `/share/<id>` — OG-tag landing page
  - `/watch/<id>` — live spectator view
  - `/sitemap.xml`, `/robots.txt`
- **Services** (`app/services/`): heavy logic — `simulation_manager.py` orchestrates state, `simulation_runner.py` spawns subprocess per run, `report_agent.py` calls LLM for final reports, `demographic_sampler.py` for Nemotron-anchored personas
- **Storage** (`app/storage/`): Neo4j-backed graph store with `Neo4jStorage` (singleton), `EmbeddingService` (Ollama or OpenAI-compat), `SearchService` (hybrid: vector + BM25 + graph traversal), `RerankerService` (cross-encoder), `NERExtractor`, `EntityResolver`, `CommunityBuilder`, `ContradictionDetector`, `ReasoningTraceRecorder`
- **Wonderwall** (`backend/wonderwall/`): bundled fork of `camel-oasis` — the multi-agent social simulation framework. Agents are graph-connected `SocialAgent` instances run inside `environment/`

### Simulation pipeline

Graph build → Agent setup → Simulation (all 3 platforms in parallel via `asyncio.gather`) → Report (ReACT agent) → Interaction (chat/counterfactual branching). Each stage is a discrete step; the subprocess running the sim communicates back to Flask via `simulation_ipc.py` using **filesystem polling** (writes to `commands/`, reads from `responses/` dirs — not sockets).

### Frontend (Vue 3, `frontend/`)

- **Router** (`src/router/`): `/` Home → `/process/:projectId` → `/simulation/:id` → `/simulation/:id/start` (live feed) → `/report/:id` → `/interaction/:reportId` → `/replay/:id` → `/compare/:id1?/:id2?` → `/embed/:id` → `/explore` → `/verified`
- **Store** (`src/store/`): Pinia
- **Key views**: `SimulationRunView` (live feed during run), `ReportView`, `ExploreView` (public gallery, also powers `/verified` with pre-applied filter)

### Data persistence

Everything persists to Neo4j. Simulation state is stored as graph nodes; agent memory is stored as episodic graph edges. No relational DB.

### LLM config

Two tiers:
- `LLM_*` — default (persona generation, sim config, memory compaction). Cheap/fast model. Defaults: `xiaomi/mimo-v2-flash`.
- `SMART_*` — optional stronger model for reports and ontology extraction. Defaults: `google/gemini-3-flash-preview`. Falls back to `LLM_*` when unset.
- `LLM_PROVIDER` / `SMART_PROVIDER`: `"openai"` (default, any OpenAI-compat endpoint) or `"claude-code"` (local CLI — no API key needed).

## Key env vars (`.env` in project root)

```
# LLM (required)
LLM_PROVIDER, LLM_API_KEY, LLM_BASE_URL, LLM_MODEL_NAME
SMART_PROVIDER, SMART_API_KEY, SMART_BASE_URL, SMART_MODEL_NAME   # optional stronger tier

# Neo4j (required)
NEO4J_URI, NEO4J_USER, NEO4J_PASSWORD

# Embeddings
EMBEDDING_PROVIDER          # "ollama" (default) or "openai"
EMBEDDING_MODEL, EMBEDDING_BASE_URL, EMBEDDING_API_KEY, EMBEDDING_DIMENSIONS, EMBEDDING_BATCH_SIZE

# Reranker (cross-encoder, auto-downloads via sentence-transformers)
RERANKER_ENABLED, RERANKER_MODEL, RERANKER_CANDIDATES

# Graph retrieval
GRAPH_SEARCH_ENABLED, GRAPH_SEARCH_HOPS, GRAPH_SEARCH_SEEDS

# Optional features
MIROSHARK_INTERNAL_KEY   # enforces x-miroshark-internal-key header on /api/*
DEMOGRAPHICS_COUNTRY     # e.g. "us", "sg" — Nemotron-anchored persona grounding
WEB_SEARCH_MODEL         # e.g. "perplexity/sonar-pro" — web-enriched persona research
ENABLE_SITEMAP           # default true; set false for private deployments
FLASK_DEBUG              # default true
OLLAMA_NUM_CTX=8192      # 8192 works with Gemma4 7.5B; 16384 causes OOM/timeout
```

## Cloud Run (staging)

Live: `https://miroshark-api-zul335dpla-ew.a.run.app`

```bash
./scripts/deploy_cloudrun.sh        # build + push + deploy (europe-west1, project: bazodiac)
./scripts/deploy_cloudrun.sh v1.2   # tag a specific version
```

- `cloudbuild.yaml` — Cloud Build config, uses `Dockerfile.railway`, `E2_HIGHCPU_8`
- `cloudrun.env.yaml` — secrets/env for Cloud Run (**gitignored**, never commit)
- IAM: `allUsers` invoker — `/api/*` protected by `x-miroshark-internal-key`

**Test frontend against Cloud Run locally:**
```
# frontend/.env.local
VITE_API_BASE_URL=https://miroshark-api-zul335dpla-ew.a.run.app
VITE_INTERNAL_KEY=<key from cloudrun.env.yaml>
```
The `VITE_INTERNAL_KEY` is injected as `x-miroshark-internal-key` by the axios interceptor in `src/api/index.js`.

## Railway / staging

`Dockerfile.railway` + `railway.json` define the Railway staging deployment. Backend binds to `$PORT` (Railway-injected), falling back to `$FLASK_PORT` then `5001`. CMD uses `/app/backend/.venv/bin/python` (not system Python) because `uv sync --frozen` creates a virtualenv.

## Important patterns

- Simulation runs as a **subprocess** (`simulation_runner.py`), not in-process. IPC via `simulation_ipc.py` uses **filesystem polling** (commands/ + responses/ dirs), not sockets.
- `SimulationRunner.register_cleanup()` is called on app startup to ensure subprocess cleanup on exit.
- `Neo4jStorage` is a singleton stored in `app.extensions['neo4j_storage']` — endpoints check for `None` and return 503 gracefully when Neo4j is down.
- The `wonderwall` package is **bundled** at `backend/wonderwall/`, not installed from PyPI — modifying it directly affects simulation behavior.
- Demographic grounding (Nemotron-anchored personas) lives in `app/services/demographic_sampler.py` and is optional — degrades gracefully if `duckdb`/`huggingface_hub` aren't available.
