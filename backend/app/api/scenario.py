"""
Headless Scenario API — Service-to-Service (S2S) entry point.

A single call ingests a ScenarioSeed and returns a job handle; the caller polls
one URL for the finished report. No multipart upload, no 8 round-trips.

    POST /api/scenario
        { "seed": "<ScenarioSeed.md text>",
          "requirement": "...",        # optional — framing for the simulation
          "generic_prompt": "...",     # optional — invariant rules (additional_context)
          "max_rounds": 10,            # optional, default 10 (1..200)
          "platforms": ["twitter","reddit"] }   # optional, default twitter+reddit
        -> 202 { "success": true, "data": { "job_id": "...", "status": "running" } }

    GET /api/scenario/<job_id>
        -> { "success": true, "data": {
               "job_id", "status": running|completed|failed,
               "stage", "project_id", "simulation_id", "report", "error" } }

The orchestration replays the SAME endpoints the verified manual harness drives
(scenario-test-run/run_manual_test.sh), in-process via a caller abstraction, so
the sequence is unit-testable without a live Neo4j / LLM stack. This is the
current-path orchestrator; the output is a MiroShark report — normalization to
ScenarioBranchV1[] stays on the Bazodiac side (see architecture/).
"""

import json
import os
import threading
import time
import uuid
from datetime import datetime, timezone

from flask import current_app, jsonify, request

from . import scenario_bp
from ..utils.logger import get_logger

logger = get_logger('miroshark.api.scenario')

# Default framing used when the caller does not supply its own `requirement`.
# Domain-neutral on purpose — MiroShark never assumes the seed's subject.
_DEFAULT_REQUIREMENT = (
    "Simulate the social-media reaction dynamics implied by the attached "
    "scenario seed: who reacts, how stances form and shift, where tension and "
    "amplification arise. Do not predict concrete external events."
)

# --- job store (in-memory) --------------------------------------------------
# Single-instance store. For a horizontally-scaled deployment the report would
# have to live in Neo4j (it already does, keyed by simulation_id) and the job
# index move to shared storage — a declared limitation, not a silent one.
_JOBS: dict = {}
_LOCK = threading.Lock()

_TERMINAL_OK = "completed"
_TERMINAL_FAIL = "failed"


class PipelineError(RuntimeError):
    """Carries the stage at which the pipeline failed."""

    def __init__(self, message: str, stage: str):
        super().__init__(message)
        self.stage = stage


def _new_job() -> str:
    job_id = uuid.uuid4().hex
    with _LOCK:
        _JOBS[job_id] = {
            "job_id": job_id,
            "status": "running",
            "stage": "queued",
            "created_at": datetime.now(timezone.utc).isoformat(),
            "project_id": None,
            "simulation_id": None,
            "report": None,
            "error": None,
        }
    return job_id


def _update(job_id: str, **fields) -> None:
    with _LOCK:
        job = _JOBS.get(job_id)
        if job is not None:
            job.update(fields)


def _snapshot(job_id: str):
    with _LOCK:
        job = _JOBS.get(job_id)
        return dict(job) if job is not None else None


# --- caller abstraction -----------------------------------------------------
# The orchestrator depends only on these three methods, so tests can drive it
# with a scripted fake and production reuses the app's own endpoints in-process.

class _SelfCaller:
    """In-process client over the app's own HTTP endpoints (Flask test_client).

    Reuses the exact verified request/response contract of each step instead of
    re-deriving service-layer signatures, and runs the auth guard like any real
    caller (we pass the configured internal key)."""

    def __init__(self, app, internal_key: str):
        self._app = app
        self._key = internal_key

    def _headers(self):
        return {"x-miroshark-internal-key": self._key} if self._key else {}

    def post_json(self, path, payload):
        with self._app.test_client() as c:
            r = c.post(path, json=payload, headers=self._headers())
            return r.status_code, (r.get_json(silent=True) or {})

    def post_form(self, path, data):
        with self._app.test_client() as c:
            r = c.post(path, data=data, headers=self._headers(),
                       content_type="multipart/form-data")
            return r.status_code, (r.get_json(silent=True) or {})

    def get(self, path):
        with self._app.test_client() as c:
            r = c.get(path, headers=self._headers())
            return r.status_code, (r.get_json(silent=True) or {})


# --- status readers ---------------------------------------------------------

def _status_of(body) -> str:
    data = body.get("data") if isinstance(body, dict) else None
    if isinstance(data, dict) and data.get("status"):
        return str(data["status"])
    if isinstance(data, dict) and data.get("runner_status"):
        return str(data["runner_status"])
    return str(body.get("status", "unknown")) if isinstance(body, dict) else "unknown"


def _need(body, keys, status_code, where):
    cur = body
    for k in keys:
        cur = cur.get(k) if isinstance(cur, dict) else None
    if not cur:
        raise PipelineError(f"{where} failed (HTTP {status_code}): {json.dumps(body)[:300]}", where)
    return cur


def _poll(caller, getter, ready: set, failed: set, *, stage, poll_seconds, max_wait, sleep):
    """Poll `getter()` (returns (code, body)) until status hits ready/failed/timeout."""
    waited = 0.0
    while True:
        code, body = getter()
        st = _status_of(body)
        if st in ready:
            return body
        if st in failed:
            raise PipelineError(f"{stage} reported '{st}': {json.dumps(body)[:300]}", stage)
        if waited >= max_wait:
            raise PipelineError(f"{stage} timed out after {int(max_wait)}s (last status '{st}')", stage)
        sleep(poll_seconds)
        waited += poll_seconds


# --- orchestrator (testable: caller + sleep injected) -----------------------

def run_pipeline(job_id, params, caller, *, poll_seconds=5.0, max_wait=1800.0, sleep=time.sleep):
    try:
        seed = params["seed"]
        requirement = (params.get("requirement") or "").strip() or _DEFAULT_REQUIREMENT
        generic_prompt = (params.get("generic_prompt") or "").strip()
        max_rounds = int(params.get("max_rounds") or 10)
        platforms = params.get("platforms") or ["twitter", "reddit"]

        # 1) ontology/generate — seed travels as a url_docs text entry (no file).
        _update(job_id, stage="ontology")
        url_docs = json.dumps([{
            "title": "ScenarioSeed",
            "url": "scenario://seed",
            "text": seed,
        }])
        code, body = caller.post_form("/api/graph/ontology/generate", {
            "project_name": "S2S Scenario",
            "simulation_requirement": requirement,
            "additional_context": generic_prompt,
            "url_docs": url_docs,
        })
        project_id = _need(body, ["data", "project_id"], code, "ontology")
        _update(job_id, project_id=project_id)

        # 2) graph/build + poll
        _update(job_id, stage="graph_build")
        code, body = caller.post_json("/api/graph/build", {"project_id": project_id})
        task_id = _need(body, ["data", "task_id"], code, "graph_build")
        _poll(caller, lambda: caller.get(f"/api/graph/task/{task_id}"),
              {"completed", "success", "done", "GRAPH_COMPLETED"}, {"failed", "error"},
              stage="graph_build", poll_seconds=poll_seconds, max_wait=max_wait, sleep=sleep)

        # 3) simulation/create
        _update(job_id, stage="create")
        code, body = caller.post_json("/api/simulation/create", {
            "project_id": project_id,
            "enable_twitter": "twitter" in platforms,
            "enable_reddit": "reddit" in platforms,
            "enable_polymarket": "polymarket" in platforms,
        })
        sim_id = _need(body, ["data", "simulation_id"], code, "create")
        _update(job_id, simulation_id=sim_id)

        # 4) prepare + poll (prepare/status is POST)
        _update(job_id, stage="prepare")
        caller.post_json("/api/simulation/prepare", {"simulation_id": sim_id})
        _poll(caller, lambda: caller.post_json("/api/simulation/prepare/status", {"simulation_id": sim_id}),
              {"ready", "completed", "success"}, {"failed", "error"},
              stage="prepare", poll_seconds=poll_seconds, max_wait=max_wait, sleep=sleep)

        # 5) start
        _update(job_id, stage="simulate")
        caller.post_json("/api/simulation/start", {
            "simulation_id": sim_id, "platform": "parallel", "max_rounds": max_rounds,
        })
        # 6) poll run-status
        _poll(caller, lambda: caller.get(f"/api/simulation/{sim_id}/run-status"),
              {"completed", "finished", "stopped", "done"}, {"failed", "error"},
              stage="simulate", poll_seconds=poll_seconds, max_wait=max_wait, sleep=sleep)

        # 7) report/generate + poll
        _update(job_id, stage="report")
        caller.post_json("/api/report/generate", {"simulation_id": sim_id})
        _poll(caller, lambda: caller.get(f"/api/report/check/{sim_id}"),
              {"completed", "ready", "success"}, {"failed", "error"},
              stage="report", poll_seconds=poll_seconds, max_wait=max_wait, sleep=sleep)

        # 8) fetch the report
        code, body = caller.get(f"/api/report/by-simulation/{sim_id}")
        report = body.get("data") if isinstance(body, dict) and body.get("success") else None
        if report is None:
            raise PipelineError(f"report fetch failed (HTTP {code})", "report")

        _update(job_id, status=_TERMINAL_OK, stage="done", report=report, error=None)
        logger.info("scenario job %s completed (sim=%s)", job_id, sim_id)

    except PipelineError as exc:
        _update(job_id, status=_TERMINAL_FAIL, stage=exc.stage, error=str(exc))
        logger.warning("scenario job %s failed at %s: %s", job_id, exc.stage, exc)
    except Exception as exc:  # noqa: BLE001 — any failure must surface, never hang the job
        _update(job_id, status=_TERMINAL_FAIL, error=f"{type(exc).__name__}: {exc}")
        logger.error("scenario job %s crashed: %s", job_id, exc)


# --- endpoints --------------------------------------------------------------

@scenario_bp.route('', methods=['POST'])
def create_scenario():
    data = request.get_json(silent=True) or {}
    seed = (data.get("seed") or "").strip()
    if len(seed) < 50:
        return jsonify({"success": False, "error": "seed is required (min 50 chars)"}), 400

    try:
        max_rounds = int(data.get("max_rounds", 10))
    except (TypeError, ValueError):
        return jsonify({"success": False, "error": "max_rounds must be an integer"}), 400
    if not (1 <= max_rounds <= 200):
        return jsonify({"success": False, "error": "max_rounds must be between 1 and 200"}), 400

    platforms = data.get("platforms") or ["twitter", "reddit"]
    if not isinstance(platforms, list) or not all(isinstance(p, str) for p in platforms):
        return jsonify({"success": False, "error": "platforms must be a list of strings"}), 400

    job_id = _new_job()
    params = {
        "seed": seed,
        "requirement": data.get("requirement"),
        "generic_prompt": data.get("generic_prompt"),
        "max_rounds": max_rounds,
        "platforms": platforms,
    }
    app = current_app._get_current_object()
    # The auth guard reads the key from the environment (not Config), so the
    # self-caller must present the same value to pass its own /api/* requests.
    caller = _SelfCaller(app, os.environ.get("MIROSHARK_INTERNAL_KEY"))
    threading.Thread(
        target=run_pipeline, args=(job_id, params, caller), daemon=True,
    ).start()

    return jsonify({"success": True, "data": {"job_id": job_id, "status": "running"}}), 202


@scenario_bp.route('/<job_id>', methods=['GET'])
def get_scenario(job_id):
    job = _snapshot(job_id)
    if job is None:
        return jsonify({"success": False, "error": "job not found"}), 404
    return jsonify({"success": True, "data": job})
