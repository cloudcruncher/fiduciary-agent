"""
Synthetic Demo Data Seeder for Personal Fiduciary Agent.
Allows any user to clone and test the entire engine locally without
connecting real banks or exposing private credentials.
"""
import random
from datetime import datetime, timedelta
from typing import Any, Dict

from fiduciary.storage.db import (
    get_connection,
    init_db,
    insert_transactions,
    save_credit_bureau_scores,
    save_net_worth_snapshot,
    upsert_account,
    upsert_institution,
)


def seed_demo_data(reset: bool = True) -> Dict[str, Any]:
    """
    Seeds a clean, realistic UK financial profile with multiple accounts,
    recurring bills, pubs, groceries, subscriptions, and salary inflows.
    """
    init_db()

    if reset:
        conn = get_connection()
        c = conn.cursor()
        c.execute("DELETE FROM transactions")
        c.execute("DELETE FROM accounts")
        c.execute("DELETE FROM institutions")
        c.execute("DELETE FROM net_worth_snapshots")
        c.execute("DELETE FROM recurring_bills")
        conn.commit()
        conn.close()

    # 1. Institutions
    upsert_institution(
        inst_id="inst_natwest",
        name="NatWest Bank",
        country="GB",
        status="connected",
        expires_at=datetime.now() + timedelta(days=90),
    )
    upsert_institution(
        inst_id="inst_revolut",
        name="Revolut",
        country="GB",
        status="connected",
        expires_at=datetime.now() + timedelta(days=90),
    )
    upsert_institution(
        inst_id="inst_wise",
        name="Wise",
        country="GB",
        status="connected",
        expires_at=datetime.now() + timedelta(days=90),
    )

    # 2. Accounts
    upsert_account(
        acc_id="acc_natwest_main",
        institution_id="inst_natwest",
        raw_account_id="nw_001",
        name="NatWest Select Current",
        account_type="checking",
        currency="GBP",
        current_balance=3850.40,
        available_balance=3850.40,
        estimated_interest_rate=0.0,
        sort_code="60-12-34",
        account_number="87654321",
        asset_class="cash",
        notes="Primary salary & direct debit operating account",
    )
    upsert_account(
        acc_id="acc_rev_main",
        institution_id="inst_revolut",
        raw_account_id="rev_001",
        name="Revolut Everyday Card",
        account_type="checking",
        currency="GBP",
        current_balance=745.20,
        available_balance=745.20,
        estimated_interest_rate=0.0,
        sort_code="04-00-75",
        account_number="12345678",
        asset_class="cash",
        notes="Daily discretionary card spend (0% cashback drag)",
    )
    upsert_account(
        acc_id="acc_rev_vault",
        institution_id="inst_revolut",
        raw_account_id="rev_002",
        name="Revolut Instant Vault",
        account_type="savings",
        currency="GBP",
        current_balance=2500.00,
        available_balance=2500.00,
        estimated_interest_rate=4.00,
        sort_code="04-00-75",
        account_number="12345679",
        asset_class="cash",
        notes="Emergency reserve yielding 4.00% gross AER",
    )
    upsert_account(
        acc_id="acc_wise_gbp",
        institution_id="inst_wise",
        raw_account_id="wise_001",
        name="Wise Multi-Currency GBP",
        account_type="checking",
        currency="GBP",
        current_balance=360.13,
        available_balance=360.13,
        estimated_interest_rate=0.0,
        sort_code="23-14-70",
        account_number="34567890",
        asset_class="cash",
        notes="Travel & international remittance float",
    )

    # 3. Generate Realistic Transactions over last 60 days
    now = datetime.now()
    tx_pool = []

    # Monthly Inflows (Salary on 28th)
    for months_ago in [0, 1]:
        d = (now - timedelta(days=30 * months_ago)).replace(day=28 if now.day >= 28 or months_ago > 0 else 1)
        tx_pool.append({
            "account_id": "acc_natwest_main",
            "transaction_id": f"sal_{months_ago}",
            "booking_date": d.strftime("%Y-%m-%d"),
            "amount": 3650.00,
            "currency": "GBP",
            "counterparty_name": "ACME TECH LTD PAYROLL",
            "description": "Monthly Net Salary ACME-9942",
            "category": "Income & Top-ups",
        })

    # Direct Debits (Monthly on 1st/2nd)
    for months_ago in [0, 1]:
        base_d = now - timedelta(days=30 * months_ago)
        tx_pool.extend([
            {
                "account_id": "acc_natwest_main",
                "transaction_id": f"so_rent_{months_ago}",
                "booking_date": (base_d.replace(day=1)).strftime("%Y-%m-%d"),
                "amount": -1350.00,
                "currency": "GBP",
                "counterparty_name": "Standing Order FOXTONS LETTINGS",
                "description": "RENT - FLAT 4 RIVERSIDE COURT",
                "category": "General Living Spend",
            },
            {
                "account_id": "acc_natwest_main",
                "transaction_id": f"klarna_{months_ago}",
                "booking_date": (base_d.replace(day=15)).strftime("%Y-%m-%d"),
                "amount": -42.50,
                "currency": "GBP",
                "counterparty_name": "Klarna",
                "description": "KLARNA* INSTALMENT 2 OF 3",
                "category": "General Living Spend",
            },
            {
                "account_id": "acc_natwest_main",
                "transaction_id": f"dd_council_{months_ago}",
                "booking_date": (base_d.replace(day=1)).strftime("%Y-%m-%d"),
                "amount": -162.00,
                "currency": "GBP",
                "counterparty_name": "Direct Debit L.B.HOUNSLOW",
                "description": "COUNCIL TAX 2026/2027",
                "category": "General Living Spend",
            },
            {
                "account_id": "acc_natwest_main",
                "transaction_id": f"dd_gas_{months_ago}",
                "booking_date": (base_d.replace(day=2)).strftime("%Y-%m-%d"),
                "amount": -78.50,
                "currency": "GBP",
                "counterparty_name": "Direct Debit BRITISH GAS",
                "description": "DUAL FUEL DD PAYMENT",
                "category": "General Living Spend",
            },
            {
                "account_id": "acc_natwest_main",
                "transaction_id": f"dd_water_{months_ago}",
                "booking_date": (base_d.replace(day=3)).strftime("%Y-%m-%d"),
                "amount": -34.20,
                "currency": "GBP",
                "counterparty_name": "Direct Debit THAMES WATER",
                "description": "WATER UTILITIES MONTHLY",
                "category": "General Living Spend",
            },
        ])

    # Discretionary & Card Transactions on Revolut
    merchants_groceries = [
        ("Sainsbury's Supermarkets", [-42.50, -58.20, -31.40, -64.10]),
        ("Tesco Stores", [-24.80, -38.90, -18.50]),
        ("Marks & Spencer", [-21.30, -34.50]),
        ("Waitrose & Partners", [-45.00, -52.80]),
    ]
    merchants_pubs = [
        ("The Carpenters Arms", [-14.40, -13.20, -18.60]),
        ("Wheatsheaf Borough", [-8.45, -9.10, -14.20]),
        ("Tap On The Line Kew", [-16.80, -12.50, -8.15]),
        ("Sq *the Kings Arms", [-15.20, -8.50, -14.40]),
        ("Southwark Tavern", [-8.45, -12.00]),
        ("Blackfriar Pub", [-8.25, -13.50]),
    ]
    merchants_dining = [
        ("Dishoom Covent Garden", [-64.50]),
        ("Uber Eats", [-24.80, -19.50]),
        ("Pizza Pilgrims", [-22.00]),
        ("Sq *vincenzo's Pizza", [-21.52]),
    ]
    merchants_subs = [
        ("Anthropic* Claude Sub", -18.00),
        ("Spotify UK", -11.99),
        ("Netflix", -10.99),
        ("GitHub Pro", -3.80),
    ]
    merchants_commute = [
        ("TfL Travel Charge", [-3.40, -7.20, -3.40, -6.80, -4.10]),
    ]
    merchants_micro = [
        ("Pret A Manger", [-3.85, -4.20, -3.95, -4.10]),
        ("Monmouth Coffee", [-4.10, -4.50, -3.80]),
    ]

    tx_idx = 100
    for day_offset in range(1, 58):
        tx_date = (now - timedelta(days=day_offset)).strftime("%Y-%m-%d")

        # Groceries every 3-4 days
        if day_offset % 4 == 0:
            m_name, amts = merchants_groceries[day_offset % len(merchants_groceries)]
            amt = random.choice(amts)
            tx_pool.append({
                "account_id": "acc_rev_main",
                "transaction_id": f"tx_groc_{tx_idx}",
                "booking_date": tx_date,
                "amount": amt,
                "currency": "GBP",
                "counterparty_name": m_name,
                "description": f"{m_name} Card Purchase",
                "category": "Groceries & Essentials",
            })
            tx_idx += 1

        # Pubs 1-2 times per week
        if day_offset % 5 == 0 or day_offset % 7 == 0:
            p_name, p_amts = merchants_pubs[day_offset % len(merchants_pubs)]
            p_amt = random.choice(p_amts)
            tx_pool.append({
                "account_id": "acc_rev_main",
                "transaction_id": f"tx_pub_{tx_idx}",
                "booking_date": tx_date,
                "amount": p_amt,
                "currency": "GBP",
                "counterparty_name": p_name,
                "description": f"{p_name} Pint / Drinks",
                "category": "Dining, Pubs & Entertainment",
            })
            tx_idx += 1

        # Dining & Restaurants once a week
        if day_offset % 6 == 0:
            d_name, d_amts = merchants_dining[day_offset % len(merchants_dining)]
            d_amt = random.choice(d_amts)
            tx_pool.append({
                "account_id": "acc_rev_main",
                "transaction_id": f"tx_dining_{tx_idx}",
                "booking_date": tx_date,
                "amount": d_amt,
                "currency": "GBP",
                "counterparty_name": d_name,
                "description": f"{d_name} Meal",
                "category": "Dining, Pubs & Entertainment",
            })
            tx_idx += 1

        # Micro coffee every 2 days
        if day_offset % 2 == 0:
            c_name, c_amts = merchants_micro[day_offset % len(merchants_micro)]
            c_amt = random.choice(c_amts)
            tx_pool.append({
                "account_id": "acc_rev_main",
                "transaction_id": f"tx_coffee_{tx_idx}",
                "booking_date": tx_date,
                "amount": c_amt,
                "currency": "GBP",
                "counterparty_name": c_name,
                "description": f"{c_name} Flat White",
                "category": "General Living Spend",
            })
            tx_idx += 1

        # Commute 3 times a week
        if day_offset % 3 == 0:
            tfl_amt = random.choice(merchants_commute[0][1])
            tx_pool.append({
                "account_id": "acc_rev_main",
                "transaction_id": f"tx_tfl_{tx_idx}",
                "booking_date": tx_date,
                "amount": tfl_amt,
                "currency": "GBP",
                "counterparty_name": "TfL Travel Charge",
                "description": "Transport for London contactless transit",
                "category": "Transport & Commute",
            })
            tx_idx += 1

    # Monthly Subscriptions (approx 20th and 24th)
    for s_name, s_amt in merchants_subs:
        for months_ago in [0, 1]:
            d_sub = (now - timedelta(days=30 * months_ago)).replace(day=22)
            tx_pool.append({
                "account_id": "acc_rev_main",
                "transaction_id": f"sub_{tx_idx}",
                "booking_date": d_sub.strftime("%Y-%m-%d"),
                "amount": s_amt,
                "currency": "GBP",
                "counterparty_name": s_name,
                "description": f"{s_name} Monthly Subscription",
                "category": "Subscriptions & Software",
            })
            tx_idx += 1

    # Insert transactions grouped by account
    accounts_txs: Dict[str, list] = {}
    for tx in tx_pool:
        acc_id = tx["account_id"]
        accounts_txs.setdefault(acc_id, []).append(tx)

    total_inserted = 0
    for acc_id, txs in accounts_txs.items():
        insert_transactions(acc_id, txs)
        total_inserted += len(txs)

    # Initial Net Worth Snapshot
    save_net_worth_snapshot()

    # Seed baseline credit bureau ratings
    save_credit_bureau_scores(
        experian=865,
        equifax=740,
        transunion=645,
        electoral_roll=True,
        notes="Verified on UK Electoral Roll at current residential address (3+ years)",
    )

    return {
        "status": "success",
        "institutions_seeded": 3,
        "accounts_seeded": 4,
        "transactions_seeded": total_inserted,
        "liquid_balance_gbp": 7455.73,
    }
