"""
Unit tests for the headless /api/scenario S2S orchestrator.

The orchestration sequence is driven through a scripted fake caller, so the
full ontology -> graph -> simulate -> report chain is exercised deterministically
without a live Neo4j / LLM stack.
"""
import os
import pytest

from app import create_app
from app.api import scenario as sc


# --------------------------------------------------------------------------
# A scripted in-memory stand-in for the app's own endpoints. Each entry maps a
# (method, path-prefix) to a list of responses consumed in order, so polling
# loops can return "running" first and a terminal status next.
# --------------------------------------------------------------------------
class FakeCaller:
    def __init__(self, script):
        self.script = script          # list of (matcher_fn, (code, body))
        self.calls = []

    def _resolve(self, method, path, payload=None):
        self.calls.append((method, path))
        for i, (match, resp) in enumerate(self.script):
            if match(method, path):
                # one-shot: remove so the next matching entry (poll step 2) wins
                self.script.pop(i)
                return resp
        raise AssertionError(f"no scripted response for {method} {path}")

    def post_json(self, path, payload):
        return self._resolve("POST", path, payload)

    def post_form(self, path, data):
        return self._resolve("POST", path, data)

    def get(self, path):
        return self._resolve("GET", path)


def _ok(data):
    return (200, {"success": True, "data": data})


def _happy_script():
    """All 8 steps succeed; graph build and run-status each poll twice."""
    def p(prefix):
        return lambda m, path: path.startswith(prefix)

    return [
        (lambda m, path: path == "/api/graph/ontology/generate", _ok({"project_id": "proj1", "ontology": {"entity_types": [1, 2]}})),
        (lambda m, path: path == "/api/graph/build", _ok({"task_id": "task1"})),
        (p("/api/graph/task/"), _ok({"status": "running"})),
        (p("/api/graph/task/"), _ok({"status": "completed"})),
        (lambda m, path: path == "/api/simulation/create", _ok({"simulation_id": "sim1"})),
        (lambda m, path: path == "/api/simulation/prepare", _ok({"status": "starting"})),
        (lambda m, path: path == "/api/simulation/prepare/status", _ok({"status": "ready"})),
        (lambda m, path: path == "/api/simulation/start", _ok({"runner_status": "running"})),
        (p("/api/simulation/sim1/run-status"), _ok({"status": "running", "current_round": 1})),
        (p("/api/simulation/sim1/run-status"), _ok({"status": "completed", "current_round": 1})),
        (lambda m, path: path == "/api/report/generate", _ok({"status": "generating", "report_id": "rep1"})),
        (p("/api/report/check/"), _ok({"status": "completed"})),
        (p("/api/report/by-simulation/"), _ok({"report_id": "rep1", "sections": [{"title": "Overview"}]})),
    ]


def test_pipeline_happy_path_reaches_completed_with_report():
    job_id = sc._new_job()
    sc.run_pipeline(job_id, {"seed": "x" * 80}, FakeCaller(_happy_script()),
                    poll_seconds=0, max_wait=10, sleep=lambda *_: None)
    job = sc._snapshot(job_id)
    assert job["status"] == "completed"
    assert job["stage"] == "done"
    assert job["project_id"] == "proj1"
    assert job["simulation_id"] == "sim1"
    assert job["report"]["report_id"] == "rep1"
    assert job["error"] is None


def test_pipeline_failure_records_stage_and_error():
    script = _happy_script()
    # Force graph build to report a hard failure on its first poll.
    script[2] = (lambda m, path: path.startswith("/api/graph/task/"), (200, {"success": True, "data": {"status": "failed"}}))
    job_id = sc._new_job()
    sc.run_pipeline(job_id, {"seed": "x" * 80}, FakeCaller(script),
                    poll_seconds=0, max_wait=10, sleep=lambda *_: None)
    job = sc._snapshot(job_id)
    assert job["status"] == "failed"
    assert job["stage"] == "graph_build"
    assert "failed" in job["error"].lower()
    assert job["report"] is None


def test_pipeline_prepare_refused_fails_fast_not_timeout():
    """Regression: prepare on a 0-entity graph refuses synchronously
    (success=false, no task). The orchestrator must fail immediately, not poll
    prepare/status='not_started' to a timeout."""
    script = _happy_script()
    # Replace the prepare trigger with a synchronous refusal (what an empty graph yields).
    for i, (match, _resp) in enumerate(script):
        if match("POST", "/api/simulation/prepare") and not match("POST", "/api/simulation/prepare/status"):
            script[i] = (lambda m, path: path == "/api/simulation/prepare",
                         (400, {"success": False, "error": "No matching entities found"}))
            break
    job_id = sc._new_job()
    sc.run_pipeline(job_id, {"seed": "x" * 80}, FakeCaller(script),
                    poll_seconds=0, max_wait=10, sleep=lambda *_: None)
    job = sc._snapshot(job_id)
    assert job["status"] == "failed"
    assert job["stage"] == "prepare"
    assert "no matching entities" in job["error"].lower()


def test_pipeline_not_started_status_is_failure_not_poll():
    """A status of 'not_started' means the task was never created — fail, not hang."""
    script = _happy_script()
    # prepare trigger succeeds but prepare/status always says not_started.
    for i, (match, _resp) in enumerate(script):
        if match("POST", "/api/simulation/prepare/status"):
            script[i] = (lambda m, path: path == "/api/simulation/prepare/status",
                         (200, {"success": True, "data": {"status": "not_started"}}))
            break
    job_id = sc._new_job()
    sc.run_pipeline(job_id, {"seed": "x" * 80}, FakeCaller(script),
                    poll_seconds=0, max_wait=10, sleep=lambda *_: None)
    job = sc._snapshot(job_id)
    assert job["status"] == "failed"
    assert job["stage"] == "prepare"
    assert "not_started" in job["error"]


def test_pipeline_missing_project_id_fails_at_ontology():
    script = [(lambda m, path: path == "/api/graph/ontology/generate", (200, {"success": False, "error": "no entities"}))]
    job_id = sc._new_job()
    sc.run_pipeline(job_id, {"seed": "x" * 80}, FakeCaller(script),
                    poll_seconds=0, max_wait=10, sleep=lambda *_: None)
    job = sc._snapshot(job_id)
    assert job["status"] == "failed"
    assert job["stage"] == "ontology"


# --------------------------------------------------------------------------
# Endpoint contract — the POST path spawns a real thread; monkeypatch the
# orchestrator to a no-op so the contract tests stay fast and stack-free.
# --------------------------------------------------------------------------
@pytest.fixture
def client(monkeypatch):
    monkeypatch.setenv("MIROSHARK_INTERNAL_KEY", "")  # relax auth for the contract tests
    monkeypatch.setattr(sc.threading, "Thread", _NoopThread)
    app = create_app()
    app.config["TESTING"] = True
    with app.test_client() as c:
        yield c


class _NoopThread:
    def __init__(self, *a, **k):
        pass

    def start(self):
        pass


def test_post_requires_seed(client):
    r = client.post("/api/scenario", json={})
    assert r.status_code == 400
    assert "seed" in r.get_json()["error"].lower()


def test_post_rejects_short_seed(client):
    r = client.post("/api/scenario", json={"seed": "too short"})
    assert r.status_code == 400


def test_post_rejects_bad_max_rounds(client):
    r = client.post("/api/scenario", json={"seed": "x" * 80, "max_rounds": 9999})
    assert r.status_code == 400


def test_post_accepts_valid_seed_returns_job(client):
    r = client.post("/api/scenario", json={"seed": "x" * 80, "max_rounds": 3})
    assert r.status_code == 202
    body = r.get_json()
    assert body["success"] is True
    assert body["data"]["status"] == "running"
    job_id = body["data"]["job_id"]
    # GET reflects the created job
    g = client.get(f"/api/scenario/{job_id}")
    assert g.status_code == 200
    assert g.get_json()["data"]["job_id"] == job_id


def test_get_unknown_job_404(client):
    r = client.get("/api/scenario/does-not-exist")
    assert r.status_code == 404
