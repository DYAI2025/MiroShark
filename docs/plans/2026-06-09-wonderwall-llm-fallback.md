# Wonderwall LLM Fallback (Cloud → Local) Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Let Wonderwall agent LLM calls try `openrouter/free` (cloud, 2-5s) first and fall back to `llama3.2` (local, 70-90s) on rate-limit/error — making the simulation loop ~10× faster when cloud works, while never dropping agents when it doesn't.

**Architecture:** Three new env vars (`WONDERWALL_FALLBACK_MODEL_NAME`, `_BASE_URL`, `_API_KEY`) flow through Config → simulation_runner subprocess env → agent.py. When the primary model raises an exception in `_aget_model_response()`, a lazy fallback `BaseModelBackend` is created on first failure and retried. No CAMEL subclassing, no per-agent model binding, no context-window issues (local model has larger context, so fallback always fits).

**Tech Stack:** Python, CAMEL-AI `BaseModelBackend`/`ModelFactory`, Flask Config, subprocess env forwarding

**Key constraint:** Do NOT touch CAMEL's model hierarchy. No subclassing, no wrappers. Just catch-and-retry in agent.py.

---

### Task 1: Add fallback config constants

**Files:**
- Modify: `backend/app/config.py:145-155`

**Step 1: Add three new Config constants after the existing WONDERWALL_* block**

Find the existing Wonderwall config block (around line 145):

```python
# Wonderwall model — model for Wonderwall/CAMEL agent simulation loop.
WONDERWALL_MODEL_NAME = os.environ.get('WONDERWALL_MODEL_NAME', '')
# Optional per-slot endpoint override
WONDERWALL_API_KEY = os.environ.get('WONDERWALL_API_KEY', '')
WONDERWALL_BASE_URL = os.environ.get('WONDERWALL_BASE_URL', '')
```

Add after it:

```python
# Wonderwall fallback model — used when primary (e.g. openrouter/free)
# returns rate-limit or server error. Falls back to local Ollama model
# (e.g. llama3.2) so the simulation never stalls on cloud failures.
WONDERWALL_FALLBACK_MODEL_NAME = os.environ.get('WONDERWALL_FALLBACK_MODEL_NAME', '')
WONDERWALL_FALLBACK_API_KEY = os.environ.get('WONDERWALL_FALLBACK_API_KEY', '')
WONDERWALL_FALLBACK_BASE_URL = os.environ.get('WONDERWALL_FALLBACK_BASE_URL', '')
```

**Step 2: Verify syntax**

Run: `cd backend && uv run python -c "from app.config import Config; print('FALLBACK:', Config.WONDERWALL_FALLBACK_MODEL_NAME)"`
Expected: `FALLBACK: ` (empty string by default)

**Step 3: Commit**

```bash
git add backend/app/config.py
git commit -m "feat(config): add WONDERWALL_FALLBACK_* env vars"
```

---

### Task 2: Forward fallback env vars to subprocess

**Files:**
- Modify: `backend/app/services/simulation_runner.py:505-515`

**Step 1: Extend the env-forwarding loop**

Find the loop at line ~508:

```python
from ..config import Config as _Cfg
for _attr in ('WONDERWALL_API_KEY', 'WONDERWALL_BASE_URL', 'WONDERWALL_MODEL_NAME',):
    _val = getattr(_Cfg, _attr, '') or ''
    if _val:
        env[_attr] = _val
```

Change to:

```python
from ..config import Config as _Cfg
for _attr in (
    'WONDERWALL_API_KEY', 'WONDERWALL_BASE_URL', 'WONDERWALL_MODEL_NAME',
    'WONDERWALL_FALLBACK_API_KEY', 'WONDERWALL_FALLBACK_BASE_URL', 'WONDERWALL_FALLBACK_MODEL_NAME',
):
    _val = getattr(_Cfg, _attr, '') or ''
    if _val:
        env[_attr] = _val
```

**Step 2: Verify the change**

Run: `cd backend && uv run python -c "import ast; ast.parse(open('app/services/simulation_runner.py').read()); print('Syntax OK')"`
Expected: `Syntax OK`

**Step 3: Commit**

```bash
git add backend/app/services/simulation_runner.py
git commit -m "feat(simulation-runner): forward WONDERWALL_FALLBACK_* to subprocess"
```

---

### Task 3: Implement lazy fallback model in agent.py

**Files:**
- Modify: `backend/wonderwall/social_agent/agent.py:1-30` (imports area)
- Modify: `backend/wonderwall/social_agent/agent.py:174-252` (`_aget_model_response` method)

**Step 1: Add module-level lazy fallback function before SocialAgent class**

At the top of agent.py, after the existing imports (line ~37), add a module-level variable and factory function:

```python
_fallback_model_backend = None

def _get_fallback_model():
    global _fallback_model_backend
    if _fallback_model_backend is not None:
        return _fallback_model_backend
    fb_model = os.environ.get('WONDERWALL_FALLBACK_MODEL_NAME', '')
    if not fb_model:
        return None
    fb_api_key = os.environ.get('WONDERWALL_FALLBACK_API_KEY', '') or os.environ.get('LLM_API_KEY', '')
    fb_base_url = os.environ.get('WONDERWALL_FALLBACK_BASE_URL', '') or os.environ.get('LLM_BASE_URL', '')
    try:
        from camel.models import ModelFactory
        from camel.types import ModelPlatformType
        _fallback_model_backend = ModelFactory.create(
            model_platform=ModelPlatformType.OPENAI,
            model_type=fb_model,
            api_key=fb_api_key or None,
            base_url=fb_base_url or None,
            default_headers={
                'HTTP-Referer': 'https://github.com/aaronjmars/MiroShark',
                'X-OpenRouter-Title': 'MiroShark - Universal Swarm Intelligence Engine',
                'User-Agent': f'MiroShark/1.0 (Wonderwall-Fallback; model={fb_model})',
            },
        )
        logging.getLogger(__name__).info(f'Fallback model created: {fb_model}')
    except Exception as e:
        logging.getLogger(__name__).warning(f'Failed to create fallback model: {e}')
        _fallback_model_backend = None
    return _fallback_model_backend
```

Place this after the `_emit_llm_call_event` import block (around line 37), before `class SocialAgent:`.

**Step 2: Modify `_aget_model_response` to catch, fallback, retry**

Change the exception handler in `_aget_model_response` (lines 242-247):

```python
        try:
            result = await super()._aget_model_response(filtered, num_tokens, **kwargs)
            return result
        except Exception as e:
            error_msg = str(e)
            raise
```

To:

```python
        try:
            result = await super()._aget_model_response(filtered, num_tokens, **kwargs)
            return result
        except Exception as e:
            error_msg = str(e)
            fb_model = _get_fallback_model()
            if fb_model is not None:
                logging.getLogger(__name__).warning(
                    f'SocialAgent {self.social_agent_id}: primary model failed, '
                    f'trying fallback. Error: {e}'
                )
                try:
                    result = await fb_model.run(messages=filtered, **kwargs)
                    return result
                except Exception as e2:
                    error_msg = f'Both primary and fallback failed: {e}, {e2}'
            raise
```

**Step 3: Add `logging` import at top of file if not present**

Check: the file likely already has `import logging` at line ~20-30. If not, add it.

**Step 4: Verify syntax**

Run: `cd backend && uv run python -c "import ast; ast.parse(open('wonderwall/social_agent/agent.py').read()); print('Syntax OK')"`
Expected: `Syntax OK`

**Step 5: Commit**

```bash
git add backend/wonderwall/social_agent/agent.py
git commit -m "feat(agent): lazy fallback model on LLM failure in agent loop"
```

---

### Task 4: Expose fallback config in Settings API

**Files:**
- Modify: `backend/app/api/settings.py:106-111` (GET response)
- Modify: `backend/app/api/settings.py:198-204` (POST handler)

**Step 1: Add fallback to GET /api/settings response**

Find the `'wonderwall'` block in the GET handler (around line 106-111), and add a `'wonderwall_fallback'` block after it:

```python
        'wonderwall_fallback': {
            'model_name': Config.WONDERWALL_FALLBACK_MODEL_NAME,
            'base_url': Config.WONDERWALL_FALLBACK_BASE_URL,
            'api_key_masked': _mask_key(Config.WONDERWALL_FALLBACK_API_KEY or ''),
            'has_api_key': bool(Config.WONDERWALL_FALLBACK_API_KEY),
        },
```

**Step 2: Add fallback to POST /api/settings handler**

Find the wonderwall POST block (around line 198-204):

```python
        wonderwall = body.get('wonderwall') or {}
        if wonderwall.get('model_name') is not None:
            Config.WONDERWALL_MODEL_NAME = wonderwall['model_name']
        if wonderwall.get('base_url') is not None:
            Config.WONDERWALL_BASE_URL = wonderwall['base_url']
        if wonderwall.get('api_key'):
            Config.WONDERWALL_API_KEY = wonderwall['api_key']
```

Add after it:

```python
        wonderwall_fallback = body.get('wonderwall_fallback') or {}
        if wonderwall_fallback.get('model_name') is not None:
            Config.WONDERWALL_FALLBACK_MODEL_NAME = wonderwall_fallback['model_name']
        if wonderwall_fallback.get('base_url') is not None:
            Config.WONDERWALL_FALLBACK_BASE_URL = wonderwall_fallback['base_url']
        if wonderwall_fallback.get('api_key'):
            Config.WONDERWALL_FALLBACK_API_KEY = wonderwall_fallback['api_key']
```

**Step 3: Commit**

```bash
git add backend/app/api/settings.py
git commit -m "feat(settings): expose WONDERWALL_FALLBACK_* in API"
```

---

### Task 5: Integration test — fallback triggers on simulated failure

**Files:**
- Create: `backend/tests/test_wonderwall_fallback.py`

**Step 1: Write test that verifies fallback model is created when primary fails**

```python
"""Test Wonderwall LLM fallback mechanism."""
import os
import pytest


class TestWonderwallFallback:
    """Test that the fallback model is used when primary fails."""

    def test_fallback_model_env_vars(self):
        """Fallback model config should be independent from primary."""
        os.environ['WONDERWALL_FALLBACK_MODEL_NAME'] = 'llama3.2'
        os.environ['WONDERWALL_FALLBACK_BASE_URL'] = 'http://localhost:11434/v1'
        os.environ['WONDERWALL_FALLBACK_API_KEY'] = 'ollama'

        # Re-import to pick up new env
        from importlib import reload
        from wonderwall.social_agent import agent as agent_module
        reload(agent_module)

        fb_model = agent_module._get_fallback_model()
        assert fb_model is not None, 'Fallback model should be created'
        assert hasattr(fb_model, 'run'), 'Fallback model should have run() method'
        assert hasattr(fb_model, '_get_model_response') or hasattr(fb_model, '_aget_model_response')

    def test_no_fallback_when_unconfigured(self):
        """When no fallback env var is set, _get_fallback_model returns None."""
        os.environ.pop('WONDERWALL_FALLBACK_MODEL_NAME', None)

        from importlib import reload
        from wonderwall.social_agent import agent as agent_module
        reload(agent_module)

        fb_model = agent_module._get_fallback_model()
        assert fb_model is None, 'Should return None when no fallback configured'
```

**Step 2: Run the test**

Run: `cd backend && uv run pytest tests/test_wonderwall_fallback.py -v`
Expected: PASS (2 tests)

**Step 3: Commit**

```bash
git add backend/tests/test_wonderwall_fallback.py
git commit -m "test: add wonderwall fallback model tests"
```

---

### Task 6: Verify full pipeline end-to-end

**Step 1: Check no existing env overrides pollute the test**

Run: `echo "WONDERWALL_FALLBACK_MODEL_NAME=$WONDERWALL_FALLBACK_MODEL_NAME"`
Expected: empty (no env set)

**Step 2: Run existing test suite for regressions**

Run: `cd backend && uv run pytest tests/ -v --timeout=60 2>&1 | tail -20`
Expected: All tests pass (or only pre-existing failures)

**Step 3: Apply the .env configuration**

Add to `.env`:
```
WONDERWALL_FALLBACK_MODEL_NAME=llama3.2
WONDERWALL_FALLBACK_BASE_URL=http://localhost:11434/v1
WONDERWALL_FALLBACK_API_KEY=ollama
```

**Step 4: Restart backend to pick up .env**

Run: `miroshark stop && sleep 2 && miroshark`
Check: backend starts without errors

**Step 5: Verify settings API exposes fallback config**

Run: `source .env && curl -s -H "x-miroshark-internal-key: $MIROSHARK_INTERNAL_KEY" http://localhost:5001/api/settings | python3 -c "import sys,json; d=json.load(sys.stdin); fb=d.get('data',{}).get('wonderwall_fallback',{}); print('Fallback model:', fb.get('model_name')); print('Has key:', fb.get('has_api_key'))"`
Expected: `Fallback model: llama3.2`, `Has key: True`

---

### Task 7: Commit everything and push

**Step 1: Final status check**

Run: `cd /path/to/MiroShark && git status`
Expected: Only the intended files modified

**Step 2: Commit and push**

```bash
git add -A
git commit -m "feat: Wonderwall LLM fallback (openrouter/free → llama3.2)

- Config: WONDERWALL_FALLBACK_MODEL_NAME, _API_KEY, _BASE_URL in config.py
- Runner: forward 3 fallback env vars to subprocess
- Agent: lazy fallback model in _aget_model_response(), retry on exception
- Settings API: expose wonderwall_fallback in GET/POST
- Test: verify fallback model creation from env vars"
git push origin main
```

**Step 3: Verify push**

Run: `git log --oneline -5`
Expected: Last commit is the fallback feature merge
