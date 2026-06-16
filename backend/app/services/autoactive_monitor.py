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
OLLAMA_HOST = os.environ.get("OLLAMA_HOST", "127.0.0.1:11435")
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
            host = OLLAMA_HOST
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
            env["OLLAMA_HOST"] = OLLAMA_HOST
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
                "http://127.0.0.1:5001/api/simulation/start",
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
