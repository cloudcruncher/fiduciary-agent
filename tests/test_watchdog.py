from fiduciary.analysis.watchdog import FinancialWatchdog


def test_detect_price_hikes():
    watchdog = FinancialWatchdog()
    sample_txs = [
        {"counterparty_name": "Netflix", "amount": -10.99, "booking_date": "2026-08-01"},
        {"counterparty_name": "Netflix", "amount": -12.99, "booking_date": "2026-09-01"},
    ]
    hikes = watchdog._detect_price_hikes(sample_txs)
    assert len(hikes) == 1
    assert hikes[0]["merchant"] == "Netflix"
    assert hikes[0]["increase_amount"] == 2.00
    assert hikes[0]["percentage_increase"] == 18.2

def test_detect_duplicate_charges():
    watchdog = FinancialWatchdog()
    sample_txs = [
        {"id": "tx1", "account_id": "acc1", "counterparty_name": "Coffee House", "amount": -4.50, "booking_date": "2026-09-10"},
        {"id": "tx2", "account_id": "acc1", "counterparty_name": "Coffee House", "amount": -4.50, "booking_date": "2026-09-10"},
    ]
    dups = watchdog._detect_duplicate_charges(sample_txs)
    assert len(dups) == 1
    assert dups[0]["merchant"] == "Coffee House"
    assert dups[0]["amount"] == 4.50

def test_detect_bills():
    watchdog = FinancialWatchdog()
    sample_txs = [
        {"counterparty_name": "Spotify", "amount": -10.99, "booking_date": "2026-08-15", "category": "Subscriptions & Software"},
        {"counterparty_name": "Spotify", "amount": -10.99, "booking_date": "2026-09-15", "category": "Subscriptions & Software"},
    ]
    active, inactive = watchdog._detect_and_sync_bills(sample_txs)
    assert len(active) == 1
    assert active[0]["merchant"] == "Spotify"
    assert active[0]["frequency"] == "monthly"
    assert active[0]["expected_amount"] == 10.99
    assert len(inactive) == 0
