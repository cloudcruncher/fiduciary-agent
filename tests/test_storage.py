from fiduciary.storage.db import (
    clear_chat_history,
    delete_account,
    delete_oauth_tokens,
    get_chat_history,
    get_connection,
    get_net_worth_breakdown,
    get_oauth_tokens,
    get_rate_cache,
    get_recurring_bills,
    init_db,
    save_chat_message,
    save_oauth_tokens,
    set_rate_cache,
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

