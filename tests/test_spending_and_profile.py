from unittest.mock import patch

import pytest

from fiduciary.analysis.customer_profile import CustomerProfileEngine
from fiduciary.analysis.spending import SpendingInsightEngine
from fiduciary.storage.db import (
    get_recent_transactions,
    init_db,
    insert_transactions,
    upsert_account,
    upsert_institution,
)


@pytest.fixture(autouse=True)
def setup_database():
    init_db()
    upsert_institution("inst_revolut", "Revolut", "UK", "AUTHORIZED")
    upsert_account(
        acc_id="acc_revolut",
        institution_id="inst_revolut",
        raw_account_id="raw_revolut",
        name="Revolut Current",
        account_type="checking",
        currency="GBP",
        current_balance=7500.0,
        available_balance=7500.0
    )

    sample_txs = [
        {"id": "tx1", "booking_date": "2026-09-24", "counterparty_name": "The Carpenters Arms", "amount": -13.20, "category": "Dining, Pubs & Entertainment"},
        {"id": "tx2", "booking_date": "2026-09-24", "counterparty_name": "Sq *the Kings Arms", "amount": -14.40, "category": "Dining, Pubs & Entertainment"},
        {"id": "tx3", "booking_date": "2026-09-23", "counterparty_name": "Tap On The Line - Kew", "amount": -8.15, "category": "Dining, Pubs & Entertainment"},
        {"id": "tx4", "booking_date": "2026-09-30", "counterparty_name": "Sainsburys Brentford", "amount": -19.85, "category": "Groceries & Essentials"},
        {"id": "tx5", "booking_date": "2026-09-28", "counterparty_name": "Welcome Brentford", "amount": -6.88, "category": "Groceries & Essentials"},
        {"id": "tx6", "booking_date": "2026-09-26", "counterparty_name": "Anthropic Ireland", "amount": -18.00, "category": "Subscriptions & Software"},
        {"id": "tx7", "booking_date": "2026-09-15", "counterparty_name": "Direct Debit BRITISH GAS", "amount": -50.00, "category": "General Living Spend"},
        {"id": "tx8", "booking_date": "2026-09-10", "counterparty_name": "Direct Debit TV LICENCE", "amount": -14.95, "category": "General Living Spend"},
        {"id": "tx9", "booking_date": "2026-09-01", "counterparty_name": "Topup from Main Account", "amount": 250.00, "category": "Income & Top-ups"},
    ]
    insert_transactions("acc_revolut", sample_txs)

def test_resolve_category():
    assert SpendingInsightEngine.resolve_category("how much on pubs") == "Dining, Pubs & Entertainment"
    assert SpendingInsightEngine.resolve_category("spent on groceries") == "Groceries & Essentials"
    assert SpendingInsightEngine.resolve_category("netflix and claude subscriptions") == "Subscriptions & Software"
    assert SpendingInsightEngine.resolve_category("train and uber travel") == "Transport & Commute"

def test_parse_spending_intent():
    p1 = SpendingInsightEngine.parse_spending_intent("how much did I spend on pubs")
    assert p1["is_spending_query"] is True
    assert p1["matched_category"] == "Dining, Pubs & Entertainment"

    p2 = SpendingInsightEngine.parse_spending_intent("last 10 transactions from revolut")
    assert p2["is_last_tx_query"] is True
    assert p2["limit"] == 10
    assert p2["target_bank"] == "revolut"

    p3 = SpendingInsightEngine.parse_spending_intent("groceries in the last 14 days")
    assert p3["matched_category"] == "Groceries & Essentials"
    assert p3["days"] == 14

def test_query_spending_pubs():
    res = SpendingInsightEngine.query_spending(query_str="how much did I spend on pubs")
    assert res["category"] == "Dining, Pubs & Entertainment"
    assert res["total_spent_gbp"] > 0
    assert res["transaction_count"] > 0
    assert "Pubs & Bars" in res["narrative"]
    assert len(res["itemized_transactions"]) > 0

def test_query_spending_groceries():
    res = SpendingInsightEngine.query_spending(query_str="spent on groceries", days=30)
    assert res["category"] == "Groceries & Essentials"
    assert res["total_spent_gbp"] > 0
    assert res["timeframe_days"] == 30
    assert "Groceries & Essentials" in res["narrative"]

def test_spending_velocity():
    vel = SpendingInsightEngine.get_spending_velocity()
    assert "status" in vel
    assert vel["status"] in ["ACCELERATING", "DECELERATING", "STEADY"]
    assert "trailing_7d_spend" in vel
    assert "normalized_weekly_baseline" in vel
    assert "velocity_shift_pct" in vel

def test_micro_expense_analysis():
    micro = SpendingInsightEngine.get_micro_expense_analysis(threshold=10.0, days=30)
    assert micro["micro_threshold_gbp"] == 10.0
    assert micro["total_micro_spend_gbp"] >= 0
    assert micro["micro_transaction_count"] >= 0
    assert isinstance(micro["top_micro_merchants"], list)

def test_customer_profile_generation():
    prof = CustomerProfileEngine.generate_profile()

    # Health Score
    hs = prof["health_score"]
    assert 0 <= hs["total"] <= 100
    assert hs["grade"] in ["A (Excellent)", "B (Strong)", "C (Fair)", "D (Action Required)"]
    assert 0 <= hs["runway_score"] <= 30
    assert 0 <= hs["drag_score"] <= 25
    assert 0 <= hs["budget_score"] <= 25
    assert 0 <= hs["hygiene_score"] <= 20

    # Financial DNA
    dna = prof["financial_dna"]
    assert "archetype" in dna
    assert "description" in dna
    assert dna["cognitive_friction_level"] in ["LOW", "MODERATE", "HIGH"]

    # 50/30/20 Budget
    b50 = prof["budget_50_30_20"]
    assert b50["needs_total_gbp"] >= 0
    assert b50["wants_total_gbp"] >= 0

    # Action Cards
    actions = prof["action_cards"]
    assert len(actions) > 0
    for a in actions:
        assert a["priority"] in ["HIGH", "MEDIUM", "LOW"]
        assert "title" in a
        assert a["annual_gain_gbp"] >= 0
        assert len(a.get("action_steps", [])) > 0

def test_get_recent_transactions_category_filter():
    txs_dining = get_recent_transactions(days=None, category="Dining")
    assert len(txs_dining) > 0
    for t in txs_dining:
        assert "Dining" in t["category"]


def test_copilot_session_reset():
    from fiduciary.agent.copilot import AICopilotEngine
    from fiduciary.storage.db import get_chat_history, save_chat_message

    # Seed some old messages
    save_chat_message("user", "Old query 1")
    save_chat_message("assistant", "Old answer 1")
    save_chat_message("user", "Old query 2")
    save_chat_message("assistant", "Old answer 2")
    assert len(get_chat_history()) >= 4

    # Process query with reset_session=True
    copilot = AICopilotEngine()
    with patch.object(copilot, "is_configured", return_value=True), patch.object(copilot.llm, "generate", return_value="Fresh response"):
        res = copilot.process_query("What is my emergency fund buffer?", reset_session=True)
        assert res == "Fresh response"

    # Only current user and assistant message should exist
    history = get_chat_history()
    assert len(history) == 2
    assert history[0]["role"] == "user"
    assert history[0]["content"] == "What is my emergency fund buffer?"
    assert history[1]["role"] == "assistant"
    assert history[1]["content"] == "Fresh response"

