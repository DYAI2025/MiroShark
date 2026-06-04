# LOCAL_SETUP — lokaler Ollama-Stack (Linux/macOS)

Reproduziert das in dieser Session erprobte **kostenlose, lokale** Setup:
Backend (Flask) + Frontend (Vite) + Neo4j + Ollama, ohne bezahlte API-Tokens.
`.env` und `frontend/.env.local` sind **gitignored** (Internal-Key) — diese
Datei ist die Vorlage, aus der du sie auf dem Zielrechner neu anlegst.

> **Wichtigste Lehre der Session:** `gemma4:e4b` ist zu schwach für NER —
> es gibt leeres JSON zurück → 0 Entities → Step 03 „No matching entities".
> Auf Linux ein **NER-fähiges** Modell ziehen (`qwen2.5:7b-instruct` oder
> `:14b`). Ontology schafft gemma4, NER nicht.

## 1. Voraussetzungen

```bash
# Ollama (https://ollama.com), Neo4j (CE), Node >=18, uv (python), jq/curl
ollama pull qwen2.5:7b-instruct     # LLM/NER/Reports — macht JSON zuverlässig
ollama pull nomic-embed-text        # Embeddings (768-dim)
# qwen2.5:14b-instruct ist besser, wenn genug RAM da ist.
```

Neo4j lokal starten (Bolt auf `:7687`), Passwort merken (unten in `.env`).
macOS: `brew services start neo4j`. Linux: `neo4j start` / systemd / Docker
(`docker run -p7687:7687 -p7474:7474 -e NEO4J_AUTH=neo4j/miroshark neo4j:community`).

## 2. Backend-Config — `MiroShark/.env` (im Projekt-Root anlegen)

```dotenv
# Neo4j
NEO4J_URI=bolt://localhost:7687
NEO4J_USER=neo4j
NEO4J_PASSWORD=miroshark            # == was du in Neo4j gesetzt hast

# LLM = lokales Ollama (OpenAI-kompatibel). "ollama" ist ein Dummy-Key.
LLM_PROVIDER=openai
LLM_API_KEY=ollama
LLM_BASE_URL=http://localhost:11434/v1
LLM_MODEL_NAME=qwen2.5:7b-instruct  # NICHT gemma4:e4b (NER scheitert)

# SMART_* leer lassen -> erbt LLM_* (Reports/Ontology nutzen dann dasselbe Modell)

# Embeddings = lokales Ollama
EMBEDDING_PROVIDER=ollama
EMBEDDING_MODEL=nomic-embed-text
EMBEDDING_BASE_URL=http://localhost:11434
EMBEDDING_DIMENSIONS=768

# Reranker aus (spart RAM; Cross-Encoder-Download entfällt)
RERANKER_ENABLED=false

# Ollama-Kontextfenster. 8192 läuft; 16384 -> OOM/Timeout auf kleinen Modellen.
OLLAMA_NUM_CTX=8192

FLASK_DEBUG=true
SECRET_KEY=miroshark-local-dev

# Internal-Key: auf dem Zielrechner NEU generieren und unten im Frontend
# IDENTISCH eintragen:  openssl rand -hex 32
MIROSHARK_INTERNAL_KEY=PASTE_OPENSSL_RAND_HEX_32_HERE
```

## 3. Frontend-Config — `frontend/.env.local` (anlegen)

```dotenv
VITE_API_BASE_URL=http://localhost:5001
VITE_INTERNAL_KEY=PASTE_SAME_VALUE_AS_MIROSHARK_INTERNAL_KEY
```

> Beide Keys **müssen exakt gleich** sein, sonst 401/„connection error" im UI.
> `VITE_API_BASE_URL` lokal = `localhost:5001` — **nicht** die Cloud-Run-URL.
> Vite backt die Werte beim Start ein → nach Änderung Frontend neu starten.

## 4. Starten

```bash
npm run setup:all        # einmalig: npm + frontend npm + uv sync
npm run dev              # Backend (:5001) + Frontend (:3000) mit Hot-Reload
# oder einzeln:
#   cd backend && uv run python run.py
#   cd frontend && npm run dev -- --host
```

Browser: `http://localhost:3000` → Settings → „LLM Connection Test" muss grün
sein. Dann ein Szenario starten (oder Template-Link `/?template=corporate_crisis`).

## 5. Headless S2S (ScenarioSeed → Report, ohne UI)

Siehe `docs/S2S-SCENARIO-API.md`. Kurz:

```bash
KEY=<MIROSHARK_INTERNAL_KEY>
curl -sS -X POST http://localhost:5001/api/scenario \
  -H "x-miroshark-internal-key: $KEY" -H "Content-Type: application/json" \
  -d "$(jq -n --rawfile s scenario-test-run/scenario_seed.md \
        '{seed:$s, max_rounds:10, platforms:["twitter","reddit"]}')"
# -> {job_id}; dann pollen:
curl -sS http://localhost:5001/api/scenario/<job_id> -H "x-miroshark-internal-key: $KEY" | jq '.data|{status,stage}'
```

## 6. Known issues (in dieser Session verifiziert — nicht neu entdecken)

| Symptom | Ursache | Fix |
|---|---|---|
| Step 03 „No matching entities" | NER-Modell zu schwach (gemma4:e4b → leeres JSON) | NER-fähiges Modell (qwen2.5:7b+) |
| Frontend „connection error" / 401 | `VITE_API_BASE_URL` zeigt auf Cloud Run **oder** Key-Mismatch | localhost:5001 + Keys identisch |
| Embedding-Fehler | `EMBEDDING_MODEL` = OpenAI-Name auf Ollama | `nomic-embed-text` |
| ask/ontology Timeout | kleines Modell langsam; `OLLAMA_NUM_CTX=16384` → OOM | NUM_CTX=8192, NER `max_tokens` ist bereits 1024 |
| Neo4j „unreachable" / 503 | Neo4j nicht gestartet oder Backend mit alter Config | Neo4j hoch, Backend neu starten (lädt `.env`) |
