from fiduciary.storage.db import (
    clear_chat_history,
    delete_account,
    delete_oauth_tokens,
    get_all_oauth_tokens,
    get_chat_history,
    get_connection,
    get_net_worth_breakdown,
    get_oauth_tokens,
    get_rate_cache,
    get_recurring_bills,
    init_db,
    insert_transactions,
    purge_stale_pending_transactions,
    save_chat_message,
    save_oauth_tokens,
    set_rate_cache,
    upsert_account,
    upsert_custom_asset,
    upsert_recurring_bill,
)


def test_init_db_and_tables():
    init_db()
    conn = get_connection()
    c = conn.cursor()
    c.execute("SELECT name FROM sqlite_master WHERE type='table'")
    tables = [r[0] for r in c.fetchall()]
    conn.close()

    assert "accounts" in tables
    assert "transactions" in tables
    assert "institutions" in tables
    assert "net_worth_snapshots" in tables
    assert "recurring_bills" in tables
    assert "copilot_chat" in tables
    assert "market_rate_cache" in tables

def test_custom_asset_and_net_worth():
    init_db()
    test_asset_id = "test_custom_property"
    upsert_custom_asset(
        asset_id=test_asset_id,
        name="Test Seaside Cottage",
        asset_class="property",
        account_type="property",
        balance=250000.0,
        notes="Valuation estimate"
    )

    nw = get_net_worth_breakdown()
    assert nw["total_assets"] >= 250000.0
    assert nw["breakdown"]["property"] >= 250000.0

    # Cleanup
    deleted = delete_account(test_asset_id)
    assert deleted is True

def test_recurring_bill_storage():
    init_db()
    upsert_recurring_bill(
        bill_id="test_sub_spotify",
        merchant="Spotify UK",
        category="Subscriptions & Software",
        expected_amount=10.99,
        frequency="monthly",
        last_date="2026-09-15",
        next_due_date="2026-10-15"
    )

    bills = get_recurring_bills()
    found = any(b["id"] == "test_sub_spotify" for b in bills)
    assert found is True

def test_chat_history_storage():
    init_db()
    clear_chat_history()
    save_chat_message("user", "Hello fiduciary copilot")
    save_chat_message("assistant", "Hello! How can I help?")

    history = get_chat_history()
    assert len(history) == 2
    assert history[0]["role"] == "user"
    assert history[1]["role"] == "assistant"
    clear_chat_history()

def test_rate_cache():
    init_db()
    test_data = {"boe_base_rate": 5.0, "top_isa": 4.87}
    set_rate_cache("test_cache_key", test_data)
    cached = get_rate_cache("test_cache_key")
    assert cached == test_data

def test_oauth_tokens_storage():
    init_db()
    save_oauth_tokens("test_provider", "access_123", "refresh_456", expires_in_seconds=3600)
    tokens = get_oauth_tokens("test_provider")
    assert tokens is not None
    assert tokens["provider"] == "test_provider"
    assert tokens["access_token"] == "access_123"
    assert tokens["refresh_token"] == "refresh_456"

    # Update without changing refresh token
    save_oauth_tokens("test_provider", "access_789", None, expires_in_seconds=1800)
    updated = get_oauth_tokens("test_provider")
    assert updated["access_token"] == "access_789"
    assert updated["refresh_token"] == "refresh_456"

    # Delete
    delete_oauth_tokens("test_provider")
    assert get_oauth_tokens("test_provider") is None

    # Test multi-bank token isolation and retrieval
    save_oauth_tokens("truelayer:revolut", "rev_access", "rev_ref", expires_in_seconds=3600)
    save_oauth_tokens("truelayer:lloyds", "lloyds_access", "lloyds_ref", expires_in_seconds=3600)
    all_tl = get_all_oauth_tokens("truelayer")
    providers = [t["provider"] for t in all_tl]
    assert "truelayer:revolut" in providers
    assert "truelayer:lloyds" in providers
    delete_oauth_tokens("truelayer:revolut")
    delete_oauth_tokens("truelayer:lloyds")


def test_seed_demo_data():
    from fiduciary.storage.db import get_all_accounts, get_recent_transactions
    from fiduciary.storage.seed import seed_demo_data

    res = seed_demo_data(reset=True)
    assert res["status"] == "success"
    assert res["institutions_seeded"] == 3
    assert res["accounts_seeded"] == 4
    assert res["transactions_seeded"] > 30

    accs = get_all_accounts()
    assert len(accs) == 4

    txs = get_recent_transactions(limit=100)
    assert len(txs) > 30


def test_insert_transactions_reconciles_pending_when_settled_arrives():
    init_db()
    acc_id = "test_reconcile_acc"
    upsert_account(
        acc_id=acc_id,
        institution_id="revolut",
        raw_account_id="raw_rec_1",
        name="Revolut Current",
        account_type="current",
        currency="GBP",
        current_balance=500.0,
        available_balance=500.0,
    )

    # 1. Insert pending transaction
    pending_tx = [{
        "transaction_id": "auth_999",
        "booking_date": "2026-10-03",
        "amount": -13.87,
        "currency": "GBP",
        "counterparty_name": "Welcome Brentford",
        "description": "Card payment Welcome Brentford",
        "category": "Groceries",
        "status": "pending",
    }]
    insert_transactions(acc_id, pending_tx)

    conn = get_connection()
    c = conn.cursor()
    c.execute("SELECT id, status FROM transactions WHERE account_id = ?", (acc_id,))
    rows = c.fetchall()
    assert len(rows) == 1
    assert rows[0]["status"] == "pending"

    # 2. Settled transaction arrives (different transaction ID from provider, same amount and merchant)
    settled_tx = [{
        "transaction_id": "settled_888",
        "booking_date": "2026-10-04",
        "amount": -13.87,
        "currency": "GBP",
        "counterparty_name": "Welcome Brentford",
        "description": "Welcome Brentford London",
        "category": "Groceries",
        "status": "settled",
    }]
    insert_transactions(acc_id, settled_tx)

    c.execute("SELECT id, status FROM transactions WHERE account_id = ?", (acc_id,))
    rows = c.fetchall()
    conn.close()

    # The pending row should have been purged/reconciled, leaving only the settled row
    assert len(rows) == 1
    assert rows[0]["id"] == f"{acc_id}_settled_888"
    assert rows[0]["status"] == "settled"

    delete_account(acc_id)


def test_insert_transactions_skips_pending_if_settled_already_exists():
    init_db()
    acc_id = "test_skip_pending_acc"
    upsert_account(
        acc_id=acc_id,
        institution_id="revolut",
        raw_account_id="raw_skip_1",
        name="Revolut Current",
        account_type="current",
        currency="GBP",
        current_balance=500.0,
        available_balance=500.0,
    )

    settled_tx = [{
        "transaction_id": "settled_111",
        "booking_date": "2026-10-02",
        "amount": -25.50,
        "currency": "GBP",
        "counterparty_name": "Tesco Superstore",
        "description": "Tesco Store 1234",
        "status": "settled",
    }]
    insert_transactions(acc_id, settled_tx)

    # Incoming pending transaction for the same charge
    pending_tx = [{
        "transaction_id": "auth_000",
        "booking_date": "2026-10-02",
        "amount": -25.50,
        "currency": "GBP",
        "counterparty_name": "Tesco Superstore",
        "description": "Tesco Pending Auth",
        "status": "pending",
    }]
    insert_transactions(acc_id, pending_tx)

    conn = get_connection()
    c = conn.cursor()
    c.execute("SELECT id, status FROM transactions WHERE account_id = ?", (acc_id,))
    rows = c.fetchall()
    conn.close()

    # Only settled exists, pending was skipped
    assert len(rows) == 1
    assert rows[0]["id"] == f"{acc_id}_settled_111"
    assert rows[0]["status"] == "settled"

    delete_account(acc_id)


def test_purge_stale_pending_transactions():
    init_db()
    acc_id = "test_stale_acc"
    upsert_account(
        acc_id=acc_id,
        institution_id="revolut",
        raw_account_id="raw_stale_1",
        name="Revolut Current",
        account_type="current",
        currency="GBP",
        current_balance=500.0,
        available_balance=500.0,
    )

    txs = [
        {"transaction_id": "p1", "booking_date": "2026-10-04", "amount": -10.0, "status": "pending"},
        {"transaction_id": "p2", "booking_date": "2026-10-04", "amount": -20.0, "status": "pending"},
    ]
    insert_transactions(acc_id, txs)

    # Only p2 is currently reported by provider
    active_ids = {f"{acc_id}_p2"}
    purge_stale_pending_transactions(acc_id, active_ids)

    conn = get_connection()
    c = conn.cursor()
    c.execute("SELECT id FROM transactions WHERE account_id = ?", (acc_id,))
    rows = c.fetchall()
    conn.close()

    assert len(rows) == 1
    assert rows[0]["id"] == f"{acc_id}_p2"

    delete_account(acc_id)


