from fastapi.testclient import TestClient

from fiduciary.observability.tracer import (
    GroundingAuditor,
    clear_all_traces,
    get_observability_metrics,
    get_recent_traces,
    record_llm_trace,
)
from fiduciary.web.app import app

client = TestClient(app)

def test_grounding_auditor_verified():
    sys_prompt = "Total Liquid Capital: £27.26. Daily burn: £17.12. Top Cash ISA: Trading 212 at 4.87% AER."
    response = "You currently have £27.26 in liquid funds and your daily living burn is £17.12. You could earn 4.87% AER in a Cash ISA."

    res = GroundingAuditor.audit(response=response, system_prompt=sys_prompt)
    assert res["status"] == "VERIFIED_GROUNDED"
    assert res["grounding_score"] == 1.0
    assert "£27.26" in res["verified_figures"]
    assert "4.87%" in res["verified_figures"]
    assert len(res["unverified_figures"]) == 0

def test_grounding_auditor_unverified_figure():
    sys_prompt = "Total Liquid Capital: £27.26."
    response = "You have £27.26 in cash, but I found an unpaid bill of £8,950.00 from British Gas."

    res = GroundingAuditor.audit(response=response, system_prompt=sys_prompt)
    assert res["status"] in ("PARTIALLY_GROUNDED", "UNVERIFIED_FIGURES_DETECTED")
    assert res["grounding_score"] < 1.0
    assert "£8,950.00" in res["unverified_figures"] or "£8,950" in str(res["unverified_figures"])

def test_trace_lifecycle_and_metrics():
    clear_all_traces()
    m0 = get_observability_metrics()
    assert m0["total_invocations"] == 0

    # Record trace 1
    t1 = record_llm_trace(
        caller="test_caller",
        provider="local",
        model="local-test-model",
        latency_ms=120.5,
        user_prompt="How much runway do I have?",
        system_prompt="Runway: 1.6 days. Liquid cash: £27.26.",
        response="You have 1.6 days of liquid runway based on £27.26 in cash."
    )
    assert t1["audit"]["status"] == "VERIFIED_GROUNDED"

    traces = get_recent_traces(limit=10)
    assert len(traces) == 1
    assert traces[0]["caller"] == "test_caller"
    assert traces[0]["latency_ms"] == 120.5

    metrics = get_observability_metrics()
    assert metrics["total_invocations"] == 1
    assert metrics["local_share_pct"] == 100.0
    assert metrics["grounding_pass_rate_pct"] == 100.0

    clear_all_traces()
    assert len(get_recent_traces()) == 0

def test_api_traces_endpoints():
    # Test GET /api/traces
    res_get = client.get("/api/traces")
    assert res_get.status_code == 200
    data = res_get.json()
    assert "traces" in data
    assert "metrics" in data

    # Test POST /api/traces/clear
    res_clear = client.post("/api/traces/clear")
    assert res_clear.status_code == 200
    assert res_clear.json()["status"] == "cleared"

def test_api_judge_endpoints(monkeypatch):
    from fiduciary.observability.judge import LLMJudge

    def mock_eval_trace(self, trace_id: str):
        return {
            "trace_id": trace_id,
            "status": "SUCCESS",
            "verdict": "PASSED",
            "overall_score": 1.0,
            "reasoning": "Mocked judge passed."
        }

    def mock_eval_latest(self):
        return {
            "trace_id": "tr_latest",
            "status": "SUCCESS",
            "verdict": "PASSED",
            "overall_score": 0.95,
            "reasoning": "Latest trace evaluated."
        }

    monkeypatch.setattr(LLMJudge, "evaluate_trace", mock_eval_trace)
    monkeypatch.setattr(LLMJudge, "evaluate_latest_trace", mock_eval_latest)

    res1 = client.post("/api/traces/tr_test_123/judge")
    assert res1.status_code == 200
    assert res1.json()["verdict"] == "PASSED"
    assert res1.json()["trace_id"] == "tr_test_123"

    res2 = client.post("/api/traces/judge-latest")
    assert res2.status_code == 200
    assert res2.json()["verdict"] == "PASSED"
    assert res2.json()["trace_id"] == "tr_latest"

