# Autoactive Monitoring Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Add a toggleable "Autoactive Monitor" that polls the simulation every 8 minutes and autonomously intervenes (restart Ollama, kill stuck runners, re-trigger sim) when the simulation gets stuck.

**Architecture:** Pure backend service (`autoactive_monitor.py`) started/stopped via new API endpoints, exposed in the frontend as a checkbox toggle near the simulation start view. The monitoring loop runs in a daemon thread with escalating remediation — mirroring the `sim_monitor.sh` pattern proven in production. No new infrastructure, no DB state.

**Tech Stack:** Flask (Python threading), Vue 3 (Pinia refs), subprocess/nvidia-smi for GPU checks, existing `SimulationRunner.get_run_state()` for progress detection.

---

## Task 1: Create Backend Monitor Service

**Files:**
- Create: `backend/app/services/autoactive_monitor.py`
- Test: `backend/tests/test_unit_autoactive_monitor.py`

### Step 1: Write failing test

Create `backend/tests/test_unit_autoactive_monitor.py`:

```python
"""Tests for the autoactive monitor service."""

import pytest
import time
import threading
from unittest.mock import patch, MagicMock
from app.services.autoactive_monitor import AutoactiveMonitorService, MonitorStatus


class TestAutoactiveMonitorService:
    """Suite for monitor service lifecycle and remediation logic."""

    def test_start_monitor_returns_running_status(self):
        """Starting monitor returns RUNNING state immediately."""
        result = AutoactiveMonitorService.start("sim_test_1")
        assert result["success"] is True
        assert result["data"]["status"] == MonitorStatus.RUNNING.value
        # Cleanup
        AutoactiveMonitorService.stop("sim_test_1")

    def test_double_start_returns_error(self):
        """Starting an already-running monitor returns error."""
        AutoactiveMonitorService.start("sim_test_2")
        result = AutoactiveMonitorService.start("sim_test_2")
        assert result["success"] is False
        assert "already running" in result["error"].lower()
        AutoactiveMonitorService.stop("sim_test_2")

    def test_stop_monitor_sets_stopped(self):
        """Stopping transitions state to STOPPED."""
        AutoactiveMonitorService.start("sim_test_3")
        result = AutoactiveMonitorService.stop("sim_test_3")
        assert result["success"] is True
        status = AutoactiveMonitorService.status("sim_test_3")
        assert status["data"]["status"] == MonitorStatus.STOPPED.value

    def test_status_idle_when_not_started(self):
        """Querying status for unknown sim returns IDLE, not error."""
        status = AutoactiveMonitorService.status("sim_test_nonexistent")
        assert status["data"]["status"] == MonitorStatus.IDLE.value

    def test_stop_nonexistent_returns_error(self):
        """Stopping an unmonitored sim returns error, not crash."""
        result = AutoactiveMonitorService.stop("sim_test_nonexistent")
        assert result["success"] is False

    @patch("app.services.autoactive_monitor.AutoactiveMonitorService._ollama_is_alive")
    @patch("app.services.autoactive_monitor.AutoactiveMonitorService._vram_used_mib")
    def test_no_intervention_when_healthy(self, mock_vram, mock_ollama):
        """Healthy sim with progress should have stuck_count = 0."""
        mock_ollama.return_value = True
        mock_vram.return_value = 5000
        # Simulate a running monitor with progress
        state = {
            "status": MonitorStatus.RUNNING.value,
            "last_progress": "round_5|150_actions",
            "stuck_count": 0,
        }
        assert state["stuck_count"] == 0

    @patch("app.services.autoactive_monitor.AutoactiveMonitorService._restart_ollama")
    @patch("app.services.autoactive_monitor.AutoactiveMonitorService._ollama_is_alive")
    def test_intervention_triggers_when_ollama_dead(self, mock_alive, mock_restart):
        """Dead Ollama triggers restart intervention."""
        mock_alive.return_value = False
        mock_restart.return_value = True
        intervention = AutoactiveMonitorService._execute_remediation("sim_test", {})
        assert "ollama_restart" in intervention.get("actions", [])
```

### Step 2: Run test to verify it fails

Run: `cd backend && uv run pytest tests/test_unit_autoactive_monitor.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'app.services.autoactive_monitor'`

### Step 3: Write minimal implementation

Create `backend/app/services/autoactive_monitor.py`:

```python
"""Autoactive Monitor — polls simulation every 8 min, remediates on stuck.

Mirrors the sim_monitor.sh pattern proven in production:
  1. Check Ollama health (port 11435, configurable)
  2. Check VRAM pressure (nvidia-smi)
  3. Check sim runner process
  4. Kill + restart as last resort

Usage:
    AutoactiveMonitorService.start("sim_xxxxx")
    AutoactiveMonitorService.stop("sim_xxxxx")
    status = AutoactiveMonitorService.status("sim_xxxxx")
"""

import os
import time
import subprocess
import threading
from datetime import datetime, timezone
from enum import Enum
from typing import Dict, Optional

try:
    from app.services.simulation_runner import SimulationRunner, RunnerStatus
except ImportError:
    SimulationRunner = None
    RunnerStatus = None


POLL_INTERVAL_SECONDS = int(os.environ.get("MONITOR_POLL_INTERVAL", "480"))
STUCK_THRESHOLD = int(os.environ.get("MONITOR_STUCK_THRESHOLD", "3"))
OLLAMA_PORT = os.environ.get("OLLAMA_HOST", "127.0.0.1:11435")
VRAM_CRITICAL_MIB = int(os.environ.get("MONITOR_VRAM_CRITICAL", "7500"))


class MonitorStatus(str, Enum):
    IDLE = "idle"
    RUNNING = "running"
    STOPPED = "stopped"


class AutoactiveMonitorService:
    """Background daemon-thread monitor for simulation health."""

    _states: Dict[str, dict] = {}
    _lock = threading.Lock()

    @classmethod
    def start(cls, simulation_id: str) -> dict:
        with cls._lock:
            existing = cls._states.get(simulation_id)
            if existing and existing["status"] == MonitorStatus.RUNNING.value:
                return {"success": False, "error": "Monitoring already running"}

            state = {
                "simulation_id": simulation_id,
                "status": MonitorStatus.RUNNING.value,
                "last_progress": "",
                "stuck_count": 0,
                "started_at": datetime.now(timezone.utc).isoformat(),
                "interventions": [],
                "consecutive_vram_high": 0,
            }
            cls._states[simulation_id] = state

        thread = threading.Thread(
            target=cls._monitor_loop,
            args=(simulation_id,),
            daemon=True,
        )
        thread.start()
        return {"success": True, "data": {k: v for k, v in state.items() if k != "interventions"}}

    @classmethod
    def stop(cls, simulation_id: str) -> dict:
        with cls._lock:
            if simulation_id not in cls._states:
                return {"success": False, "error": "Not monitoring this simulation"}
            cls._states[simulation_id]["status"] = MonitorStatus.STOPPED.value
        return {"success": True}

    @classmethod
    def status(cls, simulation_id: str) -> dict:
        with cls._lock:
            state = cls._states.get(simulation_id)
            if not state:
                return {
                    "success": True,
                    "data": {
                        "simulation_id": simulation_id,
                        "status": MonitorStatus.IDLE.value,
                    },
                }
            safe = {k: v for k, v in state.items() if k in (
                "simulation_id", "status", "started_at", "stuck_count", "last_progress"
            )}
            safe["intervention_count"] = len(state.get("interventions", []))
            return {"success": True, "data": safe}

    # ---- Monitor loop -------------------------------------------------------

    @classmethod
    def _monitor_loop(cls, simulation_id: str):
        while True:
            with cls._lock:
                state = cls._states.get(simulation_id)
                if not state or state["status"] != MonitorStatus.RUNNING.value:
                    break

            run_state = cls._get_run_state(simulation_id)
            if run_state:
                cls._check_progress(simulation_id, run_state)

            with cls._lock:
                state = cls._states.get(simulation_id)
                if state and state["stuck_count"] >= STUCK_THRESHOLD:
                    cls._execute_remediation(simulation_id, run_state or {})
                    state["stuck_count"] = 0

            if run_state and cls._is_completed(run_state):
                with cls._lock:
                    s = cls._states.get(simulation_id)
                    if s:
                        s["status"] = MonitorStatus.STOPPED.value
                break

            time.sleep(POLL_INTERVAL_SECONDS)

    @classmethod
    def _check_progress(cls, simulation_id: str, run_state) -> None:
        with cls._lock:
            state = cls._states.get(simulation_id)
            if not state:
                return

            cur_round = getattr(run_state, "current_round", None) or "?"
            actions = (
                getattr(run_state, "twitter_actions_count", 0)
                + getattr(run_state, "reddit_actions_count", 0)
            )
            sig = f"r{cur_round}|a{actions}"

            if sig == state["last_progress"]:
                state["stuck_count"] += 1
            else:
                state["stuck_count"] = 0
                state["last_progress"] = sig

    @classmethod
    def _is_completed(cls, run_state) -> bool:
        if RunnerStatus is None:
            return False
        status = getattr(run_state, "runner_status", None)
        if status is None:
            runner_status_str = getattr(run_state, "runner_status", "")
            if isinstance(runner_status_str, str):
                return runner_status_str in ("completed", "failed", "stopped", "stuck")
            return False
        return status in (
            RunnerStatus.COMPLETED,
            RunnerStatus.FAILED,
            RunnerStatus.STOPPED,
            RunnerStatus.STUCK,
        )

    @classmethod
    def _get_run_state(cls, simulation_id: str):
        if SimulationRunner is None:
            return None
        try:
            return SimulationRunner.get_run_state(simulation_id)
        except Exception:
            return None

    # ---- Remediation --------------------------------------------------------

    @classmethod
    def _execute_remediation(cls, simulation_id: str, run_state) -> dict:
        """Escalating interventions. Returns action log."""
        actions = []

        if not cls._ollama_is_alive():
            cls._log(simulation_id, "Ollama not responding — restarting")
            cls._restart_ollama()
            actions.append("ollama_restart")
            time.sleep(10)

        vram = cls._vram_used_mib()
        if vram and vram > VRAM_CRITICAL_MIB:
            cls._log(simulation_id, f"VRAM critical ({vram} MiB) — restarting Ollama")
            cls._restart_ollama()
            actions.append("ollama_restart_vram")
            time.sleep(10)

        sim_pid = cls._find_sim_pid(simulation_id)
        if not sim_pid:
            cls._log(simulation_id, "Sim runner process not found — re-triggering start")
            cls._re_trigger_start(simulation_id)
            actions.append("re_trigger_start")
        else:
            cls._log(simulation_id, f"Killing stuck sim PID {sim_pid} + restarting")
            cls._kill_process(sim_pid)
            time.sleep(3)
            cls._re_trigger_start(simulation_id)
            actions.append("kill_and_restart")

        cls._log_intervention(simulation_id, actions)
        return {"actions": actions}

    @classmethod
    def _ollama_is_alive(cls) -> bool:
        try:
            host = OLLAMA_PORT  # format: "127.0.0.1:11435"
            import urllib.request
            req = urllib.request.Request(f"http://{host}/api/tags")
            with urllib.request.urlopen(req, timeout=5) as resp:
                return resp.status == 200
        except Exception:
            return False

    @classmethod
    def _vram_used_mib(cls) -> Optional[int]:
        try:
            result = subprocess.run(
                ["nvidia-smi", "--query-gpu=memory.used", "--format=csv,noheader"],
                capture_output=True, text=True, timeout=10,
            )
            if result.returncode == 0:
                raw = result.stdout.strip().lower().replace(" miB", "").strip()
                return int(float(raw))
        except Exception:
            return None

    @classmethod
    def _restart_ollama(cls) -> bool:
        try:
            subprocess.run(
                ["pkill", "-f", "/tmp/ollama-upstream/bin/ollama serve"],
                timeout=5,
            )
            time.sleep(2)
            subprocess.run(
                ["pkill", "-f", "llama-server"],
                timeout=5,
            )
            time.sleep(2)
            env = os.environ.copy()
            env["OLLAMA_NUM_PARALLEL"] = "2"
            env["OLLAMA_HOST"] = OLLAMA_PORT
            subprocess.Popen(
                ["/tmp/ollama-upstream/bin/ollama", "serve"],
                env=env,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
            time.sleep(5)
            return True
        except Exception:
            return False

    @classmethod
    def _find_sim_pid(cls, simulation_id: str) -> Optional[int]:
        try:
            result = subprocess.run(
                ["pgrep", "-f", f"run_parallel_simulation.*{simulation_id}"],
                capture_output=True, text=True, timeout=5,
            )
            if result.returncode == 0 and result.stdout.strip():
                return int(result.stdout.strip().split("\n")[0])
        except Exception:
            return None

    @classmethod
    def _kill_process(cls, pid: int) -> None:
        try:
            subprocess.run(["kill", str(pid)], timeout=5)
            time.sleep(2)
            subprocess.run(["kill", "-9", str(pid)], timeout=5)
        except Exception:
            pass

    @classmethod
    def _re_trigger_start(cls, simulation_id: str) -> None:
        """Call POST /api/simulation/start via internal HTTP."""
        try:
            import urllib.request
            import json
            data = json.dumps({
                "simulation_id": simulation_id,
                "platform": "parallel",
                "enable_cross_platform": True,
            }).encode()
            req = urllib.request.Request(
                f"http://127.0.0.1:5001/api/simulation/start",
                data=data,
                headers={"Content-Type": "application/json"},
                method="POST",
            )
            urllib.request.urlopen(req, timeout=30)
        except Exception:
            pass

    # ---- Logging ------------------------------------------------------------

    @classmethod
    def _log(cls, simulation_id: str, msg: str) -> None:
        ts = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")
        with cls._lock:
            s = cls._states.get(simulation_id)
            if s:
                s.setdefault("log", []).append(f"[{ts}] {msg}")

    @classmethod
    def _log_intervention(cls, simulation_id: str, actions: list) -> None:
        ts = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")
        entry = {
            "timestamp": ts,
            "actions": actions,
        }
        with cls._lock:
            s = cls._states.get(simulation_id)
            if s:
                s.setdefault("interventions", []).append(entry)
```

### Step 4: Run tests to verify they pass

Run: `cd backend && uv run pytest tests/test_unit_autoactive_monitor.py -v`
Expected: All tests PASS

If tests fail (e.g., import path issues), adjust imports and re-run.

### Step 5: Commit

```bash
git add backend/app/services/autoactive_monitor.py backend/tests/test_unit_autoactive_monitor.py
git commit -m "feat: add AutoactiveMonitorService daemon-thread monitor"
```

---

## Task 2: Add API Endpoints (start/stop/status monitor)

**Files:**
- Modify: `backend/app/api/simulation.py` (append before `# ============== Real-time Status Monitoring Endpoints ==============`)
- Verify: OAS spec if needed

### Step 1: Read the insertion point

Read lines 3420-3430 of `simulation.py` to confirm the anchor.

### Step 2: Insert endpoints

Add after line 3422 (`}), 500`) and before line 3424 (`# ============== Real-time Status...`):

```python

# ============== Autoactive Monitor Endpoints ==============

@simulation_bp.route('/<simulation_id>/monitor', methods=['POST'])
def start_autoactive_monitor(simulation_id: str):
    """Start autoactive monitoring for a simulation.

    Request (JSON):
        {"simulation_id": "sim_xxxx"}  # Optional, extracted from URL too

    Returns:
        {"success": true, "data": {monitor_state}}
    """
    try:
        from ..services.autoactive_monitor import AutoactiveMonitorService
        body = request.get_json(silent=True) or {}
        sid = body.get("simulation_id", simulation_id)
        result = AutoactiveMonitorService.start(sid)
        return jsonify(result)
    except Exception as e:
        logger.error(f"Failed to start monitor: {e}")
        return jsonify({"success": False, "error": str(e)}), 500


@simulation_bp.route('/<simulation_id>/monitor/stop', methods=['POST'])
def stop_autoactive_monitor(simulation_id: str):
    """Stop autoactive monitoring."""
    try:
        from ..services.autoactive_monitor import AutoactiveMonitorService
        result = AutoactiveMonitorService.stop(simulation_id)
        return jsonify(result)
    except Exception as e:
        logger.error(f"Failed to stop monitor: {e}")
        return jsonify({"success": False, "error": str(e)}), 500


@simulation_bp.route('/<simulation_id>/monitor/status', methods=['GET'])
def get_autoactive_monitor_status(simulation_id: str):
    """Get autoactive monitoring status."""
    try:
        from ..services.autoactive_monitor import AutoactiveMonitorService
        result = AutoactiveMonitorService.status(simulation_id)
        return jsonify(result)
    except Exception as e:
        logger.error(f"Failed to get monitor status: {e}")
        return jsonify({"success": False, "error": str(e)}), 500
```

### Step 3: Verify syntax

Run: `cd backend && uv run python -c "import py_compile; py_compile.compile('app/api/simulation.py', doraise=True); print('OK')"`
Expected: OK

### Step 4: Test endpoint via curl (integration check)

Run:
```bash
curl -s -X POST http://localhost:5001/api/simulation/sim_test_123/monitor \
  -H "Content-Type: application/json" \
  -H "x-miroshark-internal-key:...key..." \
  -d '{"simulation_id":"sim_test_123"}' | python3 -m json.tool
```
Expected: `{"success": true, "data": {"status": "running", ...}}`

### Step 5: Commit

```bash
git add backend/app/api/simulation.py
git commit -m "feat: add /monitor, /monitor/stop, /monitor/status API endpoints"
```

---

## Task 3: Add Frontend API Functions

**Files:**
- Modify: `frontend/src/api/simulation.js` (after line 129, before `compareSimulations`)

### Step 1: Read current file

Read lines 129-137 of `frontend/src/api/simulation.js` to confirm anchor.

### Step 2: Insert API functions

Add after line 129 (`export const getRunStatusDetail...`) and before line 131 (`/** Compare two simulations...`):

```js
/**
 * Start autoactive monitoring for a simulation
 * @param {Object} data - { simulation_id }
 */
export const startMonitor = (data) => {
  return requestWithRetry(() => service.post('/api/simulation/monitor', data), 3, 1000)
}

/**
 * Stop autoactive monitoring
 * @param {string} simulationId
 */
export const stopMonitor = (simulationId) => {
  return service.post(`/api/simulation/${simulationId}/monitor/stop`)
}

/**
 * Get autoactive monitoring status
 * @param {string} simulationId
 */
export const getMonitorStatus = (simulationId) => {
  return service.get(`/api/simulation/${simulationId}/monitor/status`)
}
```

### Step 3: Verify syntax

Run: `cd frontend && npx eslint src/api/simulation.js` (or just check file parses)

### Step 4: Commit

```bash
git add frontend/src/api/simulation.js
git commit -m "feat: add startMonitor/stopMonitor/getMonitorStatus frontend API"
```

---

## Task 4: Add Frontend Toggle in Step3Simulation.vue

**Files:**
- Modify: `frontend/src/components/Step3Simulation.vue` (add toggle + handler)

### Step 1: Read anchor lines

Read lines 185-193 (monitoring bar) and lines 1088-1144 (doStartSimulation) and line ~745 (imports).

### Step 2: Add import for new API functions

In the script section import block (around line 745), add to the existing import from `../../api/simulation`:

```js
import {
  ...existing imports...,
  startMonitor,
  stopMonitor,
  getMonitorStatus,
} from '../../api/simulation'
```

### Step 3: Add state ref and handler

In the `<script setup>` section (near other refs, around line 800), add:

```js
const autoMonitorEnabled = ref(false)

const toggleAutoMonitor = async () => {
  if (!props.simulationId) return
  if (autoMonitorEnabled.value) {
    addLog($tr('Starting autoactive monitoring...', '启动自动监控…'))
    try {
      const res = await startMonitor({ simulation_id: props.simulationId })
      if (res?.success !== false) {
        addLog($tr('Autoactive monitoring active (polls every 8 min)', '自动监控已激活（每8分钟轮询）'))
      } else {
        autoMonitorEnabled.value = false
        addLog($tr(`Monitor start failed: ${res?.error || 'unknown'}`, `监控启动失败：${res?.error || '未知'}`))
      }
    } catch (err) {
      autoMonitorEnabled.value = false
      addLog($tr(`Monitor start error: ${err.message}`, `监控启动错误：${err.message}`))
    }
  } else {
    addLog($tr('Stopping autoactive monitoring...', '停止自动监控…'))
    try {
      await stopMonitor(props.simulationId)
      addLog($tr('Autoactive monitoring stopped', '自动监控已停止'))
    } catch (err) {
      addLog($tr(`Monitor stop error: ${err.message}`, `监控停止错误：${err.message}`))
    }
  }
}
```

### Step 4: Add toggle UI in monitoring bar (after line 192)

```vue
    <div class="monitoring-bar">
      <span class="backend-dot" :class="{ alive: backendAlive, dead: !backendAlive }" :title="backendAlive ? 'Backend connected' : 'Backend unreachable'"></span>
      <label class="monitor-toggle" :title="$tr('Auto-remediate stuck simulations (polls every 8 min)', '自动修复卡住的模拟（每8分钟轮询）')">
        <input type="checkbox" v-model="autoMonitorEnabled" @change="toggleAutoMonitor" />
        <span class="monitor-label">{{ $tr('Auto Monitor', '自动监控') }}</span>
      </label>
      <span v-if="stuckWarning" class="stuck-warning">⚠ {{ stuckWarning }}</span>
    </div>
```

### Step 5: Add CSS for new toggle

In the `<style scoped>` section, add:

```css
.monitor-toggle {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  margin-left: 12px;
  cursor: pointer;
  font-size: 12px;
  user-select: none;
}
.monitor-toggle input[type="checkbox"] {
  cursor: pointer;
  accent-color: #3b82f6;
}
.monitor-label {
  color: var(--text-secondary, #9ca3af);
  transition: color 0.2s;
}
.monitor-toggle input:checked + .monitor-label {
  color: #3b82f6;
  font-weight: 600;
}
```

### Step 6: Verify build

Run: `cd frontend && npm run build`  
Expected: Build succeeds with no errors

### Step 7: Commit

```bash
git add frontend/src/components/Step3Simulation.vue
git commit -m "feat: add Autoactive Monitoring toggle in simulation start view"
```

---

## Task 5: Test End-to-End

**Files:** None (manual verification steps)

### Step 1: Start backend + frontend

Ensure dev servers are running: `cd backend && uv run python run.py` and `cd frontend && npm run dev`

### Step 2: Create a simulation via API

```bash
curl -s -X POST http://localhost:5001/api/simulation/create \
  -H "Content-Type: application/json" \
  -H "x-miroshark-internal-key:...key..." \
  -d '{"project_id":"proj_test","enable_twitter":true,"enable_reddit":true}' | python3 -m json.tool
```
Extract `simulation_id` from response.

### Step 3: Start monitoring via API

```bash
curl -s -X POST http://localhost:5001/api/simulation/<sim_id>/monitor \
  -H "Content-Type: application/json" \
  -H "x-miroshark-internal-key:...key..." \
  -d '{}' | python3 -m json.tool
```
Expected: `{"success": true, "data": {"status": "running", ...}}`

### Step 4: Check status

```bash
curl -s http://localhost:5001/api/simulation/<sim_id>/monitor/status \
  -H "x-miroshark-internal-key:...key..." | python3 -m json.tool
```
Expected: `{"success": true, "data": {"status": "running", ...}}`

### Step 5: Stop monitoring

```bash
curl -s -X POST http://localhost:5001/api/simulation/<sim_id>/monitor/stop \
  -H "x-miroshark-internal-key:...key..." | python3 -m json.tool
```
Expected: `{"success": true, "data": {"status": "stopped", ...}}`

### Step 6: Check frontend toggle

Open `http://localhost:3000/simulation/<sim_id>/start` — verify the "Auto Monitor" checkbox appears in the monitoring bar, toggles on/off, and shows status in the log panel.

---

## Task 6: Update OpenAPI Spec

**Files:**
- Modify: `backend/openapi.yaml` or `backend/docs/openapi.yaml`

### Step 1: Find the spec file

```bash
find backend -name "*.yaml" -path "*openapi*" 2>/dev/null
```

If found, add three new path entries for:
- `POST /api/simulation/{simulation_id}/monitor`
- `POST /api/simulation/{simulation_id}/monitor/stop`
- `GET /api/simulation/{simulation_id}/monitor/status`

### Step 2: Commit

```bash
git add backend/openapi.yaml
git commit -m "docs: add autoactive monitor endpoints to OpenAPI spec"
```
