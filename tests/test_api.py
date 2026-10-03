from fastapi.testclient import TestClient

from fiduciary.web.app import app

client = TestClient(app)

def test_api_routes():
    # 1. Root dashboard HTML
    res_root = client.get("/")
    assert res_root.status_code == 200
    assert "Personal Fiduciary Harness" in res_root.text

    # 2. State endpoint
    res_state = client.get("/api/state")
    assert res_state.status_code == 200
    assert "state" in res_state.json()
    assert "profile" in res_state.json()

    # 3. Net worth endpoint
    res_nw = client.get("/api/networth")
    assert res_nw.status_code == 200
    assert "net_worth" in res_nw.json()
    assert "breakdown" in res_nw.json()

    # 4. Watchdog endpoint
    res_wd = client.get("/api/watchdog")
    assert res_wd.status_code == 200
    assert "upcoming_bills_14d" in res_wd.json()

    # 5. Tax audit endpoint
    res_tax = client.get("/api/tax/audit?income=85000")
    assert res_tax.status_code == 200
    assert res_tax.json()["tax_band"] == "Higher Rate (40%)"

    # 6. Sweeper endpoint
    res_sweep = client.get("/api/sweep")
    assert res_sweep.status_code == 200
    assert "sweeper" in res_sweep.json()
    assert "standing_order" in res_sweep.json()

    # 7. Cancellation template
    res_cancel = client.post(
        "/api/cancel-template",
        json={"service_name": "Test Service", "monthly_cost": 9.99, "account_reference": "test@test.com"}
    )
    assert res_cancel.status_code == 200
    assert "email_body" in res_cancel.json()

    # 8. Copilot history
    res_chat = client.get("/api/copilot/history")
    assert res_chat.status_code == 200
    assert "messages" in res_chat.json()

    # 9. LLM Status
    res_llm = client.get("/api/llm/status")
    assert res_llm.status_code == 200
    assert "mode" in res_llm.json()
    assert "privacy_badge" in res_llm.json()

    # 10. Standalone Guide page
    res_guide = client.get("/guide")
    assert res_guide.status_code == 200
    assert "The Complete System Walkthrough" in res_guide.text

    # 11. Standalone Architecture page
    res_arch = client.get("/architecture")
    assert res_arch.status_code == 200
    assert "Solution Architecture & System Design" in res_arch.text
    assert "mermaid" in res_arch.text

    # 12. Traces endpoint
    res_traces = client.get("/api/traces")
    assert res_traces.status_code == 200
    assert "traces" in res_traces.json()

    # 13. LLM Provider switcher endpoint
    res_prov = client.post("/api/llm/provider", json={"provider": "local"})
    assert res_prov.status_code == 200
    assert res_prov.json()["configured_provider"] == "local"

    # Reset back to auto
    client.post("/api/llm/provider", json={"provider": "auto"})

    # 14. TrueLayer status endpoint
    res_tl = client.get("/api/truelayer/status")
    assert res_tl.status_code == 200
    assert "connected" in res_tl.json()

    # 15. Tools catalog endpoint
    res_tools = client.get("/api/tools")
    assert res_tools.status_code == 200
    assert "tools" in res_tools.json()
    assert len(res_tools.json()["tools"]) >= 3

    # 16. Spending insights endpoint
    res_spend = client.get("/api/spending")
    assert res_spend.status_code == 200
    assert "velocity" in res_spend.json()

    res_spend_query = client.get("/api/spending?query=pubs")
    assert res_spend_query.status_code == 200
    assert "narrative" in res_spend_query.json()

    # 17. Customer Intelligence Profile endpoint
    res_prof = client.get("/api/profile/intelligence")
    assert res_prof.status_code == 200
    assert "health_score" in res_prof.json()
    assert "financial_dna" in res_prof.json()
    assert "action_cards" in res_prof.json()

    # 18. Credit & Affordability audit endpoint
    res_credit = client.get("/api/credit/audit")
    assert res_credit.status_code == 200
    credit_data = res_credit.json()
    assert "borrowing_readiness_score" in credit_data
    assert "underwriter_tier" in credit_data
    assert "cash_flow_affordability" in credit_data
    assert "mortgage_borrowing_capacity" in credit_data
    assert "underwriter_risk_flags" in credit_data

    # 19. Credit bureau scores update endpoint
    res_scores = client.post(
        "/api/credit/scores",
        json={"experian": 880, "equifax": 750, "transunion": 650, "electoral_roll": True}
    )
    assert res_scores.status_code == 200
    assert res_scores.json()["experian"] == 880
    assert res_scores.json()["electoral_roll"] is True
