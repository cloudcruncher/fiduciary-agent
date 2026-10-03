from datetime import datetime, timedelta

import pytest

from fiduciary.analysis.credit_affordability import CreditAffordabilityEngine as Engine
from fiduciary.storage.db import (
    get_connection,
    get_credit_bureau_scores,
    init_db,
    insert_transactions,
    save_credit_bureau_scores,
    upsert_account,
    upsert_institution,
)


def _d(days_ago: int) -> str:
    return (datetime.now() - timedelta(days=days_ago)).strftime("%Y-%m-%d")


@pytest.fixture(autouse=True)
def clean_db():
    init_db()
    conn = get_connection()
    for table in ("transactions", "accounts", "institutions", "credit_profile"):
        conn.execute(f"DELETE FROM {table}")
    conn.commit()
    conn.close()
    upsert_institution("inst_t", "TestBank", "GB", "connected")
    upsert_account(
        acc_id="acc_t", institution_id="inst_t", raw_account_id="raw_t", name="Current",
        account_type="checking", currency="GBP", current_balance=6000.0, available_balance=6000.0,
    )


def _txs(extra=()):
    base = []
    for i, ago in enumerate((5, 35, 65)):
        base.append({"id": f"pay{i}", "booking_date": _d(ago), "counterparty_name": "ACME PAYROLL", "description": "Salary", "amount": 3500.0, "category": "Income & Top-ups"})
        base.append({"id": f"rent{i}", "booking_date": _d(ago), "counterparty_name": "Standing Order FOXTONS LETTINGS", "description": "RENT", "amount": -1300.0, "category": "General Living Spend"})
    base.extend(extra)
    insert_transactions("acc_t", base)


def test_income_and_housing_detected():
    _txs()
    txs = __import__("fiduciary.storage.db", fromlist=["x"]).get_all_transactions()
    assert Engine._detect_monthly_income(txs, {}) == 3500.0
    assert Engine._detect_recurring_commitments(txs)["housing"] == 1300.0


def test_bnpl_caps_score_below_prime_and_adds_action():
    extra = [
        {"id": f"k{i}", "booking_date": _d(ago), "counterparty_name": "Klarna", "description": "KLARNA* INSTALMENT", "amount": -40.0, "category": "General Living Spend"}
        for i, ago in enumerate((10, 40))
    ]
    _txs(extra)
    audit = Engine.run_full_audit()
    assert audit["underwriter_risk_flags"]["bnpl_detected"] is True
    assert audit["borrowing_readiness_score"] <= 84
    assert audit["cash_flow_affordability"]["monthly_committed_debt"] == 40.0
    assert any("BNPL" in c["title"] for c in audit["action_playbook"])


def test_bounced_direct_debit_is_flagged():
    _txs([{"id": "b1", "booking_date": _d(20), "counterparty_name": "Returned Direct Debit", "description": "UNPAID DD INSUFFICIENT FUNDS", "amount": -25.0, "category": "Fees & Charges"}])
    audit = Engine.run_full_audit()
    assert audit["underwriter_risk_flags"]["bounced_direct_debits_detected"] is True
    assert any(c["priority"] == "CRITICAL" for c in audit["action_playbook"])


def test_mortgage_math_and_gross_estimate():
    gross = Engine._estimate_gross_from_net(3650.0)
    assert 50000 < gross < 65000
    low = Engine._calculate_monthly_mortgage(200000, 0.044)
    high = Engine._calculate_monthly_mortgage(200000, 0.075)
    assert high > low > 0
    assert Engine._calculate_monthly_mortgage(0, 0.05) == 0.0


def test_bureau_scores_roundtrip_and_partial_update():
    save_credit_bureau_scores(experian=850, equifax=700, transunion=600, electoral_roll=True)
    save_credit_bureau_scores(experian=860)
    s = get_credit_bureau_scores()
    assert (s["experian"], s["equifax"], s["transunion"], s["electoral_roll"]) == (860, 700, 600, True)
    save_credit_bureau_scores(electoral_roll=False)
    assert get_credit_bureau_scores()["electoral_roll"] is False


def test_copilot_credit_query_triggers_audit(monkeypatch):
    from unittest.mock import MagicMock

    from fiduciary.agent.copilot import AICopilotEngine

    copilot = AICopilotEngine()
    mock_llm = MagicMock()
    mock_llm.generate.return_value = "Your borrowing readiness score is 84/100 (Tier 2 Mainstream)."
    monkeypatch.setattr(copilot, "llm", mock_llm)
    monkeypatch.setattr(copilot, "is_configured", lambda: True)

    _txs()
    ans = copilot.process_query("What is my borrowing readiness score and mortgage capacity?")
    assert "84/100" in ans
    assert mock_llm.generate.called
    call_kwargs = mock_llm.generate.call_args.kwargs
    sys_prompt = call_kwargs.get("system_prompt", "")
    assert "BORROWING READINESS SCORE" in sys_prompt
    assert "OPEN BANKING CASH-FLOW AFFORDABILITY" in sys_prompt
    assert "INDICATIVE MORTGAGE BORROWING CAPACITY" in sys_prompt
    tools_used = call_kwargs.get("tools_used", [])
    assert any(t.get("tool_name") == "credit_affordability_audit" for t in tools_used)

