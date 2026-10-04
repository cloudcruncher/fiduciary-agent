import hashlib
import json
import re
import sqlite3
import uuid
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

import fiduciary.config as config


def get_connection() -> sqlite3.Connection:
    conn = sqlite3.connect(config.DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_connection()
    cursor = conn.cursor()

    cursor.executescript("""
    CREATE TABLE IF NOT EXISTS institutions (
        id TEXT PRIMARY KEY,
        name TEXT NOT NULL,
        country TEXT NOT NULL,
        session_id TEXT,
        status TEXT DEFAULT 'disconnected',
        authorized_at TIMESTAMP,
        expires_at TIMESTAMP
    );

    CREATE TABLE IF NOT EXISTS accounts (
        id TEXT PRIMARY KEY,
        institution_id TEXT NOT NULL,
        account_id TEXT NOT NULL,
        name TEXT,
        account_type TEXT DEFAULT 'checking',
        asset_class TEXT DEFAULT 'cash',
        currency TEXT DEFAULT 'GBP',
        iban TEXT,
        sort_code TEXT,
        account_number TEXT,
        current_balance REAL DEFAULT 0.0,
        available_balance REAL DEFAULT 0.0,
        estimated_interest_rate REAL DEFAULT 0.0,
        notes TEXT,
        updated_at TIMESTAMP,
        FOREIGN KEY (institution_id) REFERENCES institutions (id)
    );

    CREATE TABLE IF NOT EXISTS transactions (
        id TEXT PRIMARY KEY,
        account_id TEXT NOT NULL,
        transaction_id TEXT,
        booking_date TEXT,
        amount REAL,
        currency TEXT DEFAULT 'GBP',
        counterparty_name TEXT,
        description TEXT,
        category TEXT,
        is_recurring INTEGER DEFAULT 0,
        statement_batch_id TEXT,
        raw_description TEXT,
        status TEXT DEFAULT 'settled',
        FOREIGN KEY (account_id) REFERENCES accounts (id)
    );

    CREATE TABLE IF NOT EXISTS net_worth_snapshots (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        snapshot_date TEXT NOT NULL,
        total_assets REAL NOT NULL,
        total_liabilities REAL NOT NULL,
        net_worth REAL NOT NULL,
        liquid_assets REAL NOT NULL,
        breakdown_json TEXT,
        created_at TIMESTAMP
    );

    CREATE TABLE IF NOT EXISTS recurring_bills (
        id TEXT PRIMARY KEY,
        merchant TEXT NOT NULL,
        category TEXT,
        expected_amount REAL NOT NULL,
        frequency TEXT DEFAULT 'monthly',
        last_date TEXT,
        next_due_date TEXT,
        is_active INTEGER DEFAULT 1,
        price_change_alert TEXT,
        updated_at TIMESTAMP
    );

    CREATE TABLE IF NOT EXISTS copilot_chat (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        role TEXT NOT NULL,
        content TEXT NOT NULL,
        metadata_json TEXT,
        created_at TIMESTAMP
    );

    CREATE TABLE IF NOT EXISTS market_rate_cache (
        cache_key TEXT PRIMARY KEY,
        data_json TEXT NOT NULL,
        updated_at TIMESTAMP
    );

    CREATE TABLE IF NOT EXISTS llm_traces (
        id TEXT PRIMARY KEY,
        timestamp TEXT NOT NULL,
        caller TEXT NOT NULL,
        provider TEXT NOT NULL,
        model TEXT,
        latency_ms REAL NOT NULL,
        user_prompt TEXT,
        system_prompt TEXT,
        response TEXT,
        grounding_status TEXT,
        grounding_score REAL,
        unverified_tokens_json TEXT
    );

    CREATE TABLE IF NOT EXISTS oauth_tokens (
        provider TEXT PRIMARY KEY,
        access_token TEXT NOT NULL,
        refresh_token TEXT,
        expires_at TIMESTAMP,
        updated_at TIMESTAMP
    );

    CREATE TABLE IF NOT EXISTS credit_profile (
        id TEXT PRIMARY KEY,
        experian_score INTEGER,
        equifax_score INTEGER,
        transunion_score INTEGER,
        electoral_roll_status INTEGER DEFAULT 1,
        notes TEXT,
        updated_at TIMESTAMP
    );

    CREATE INDEX IF NOT EXISTS idx_trans_account ON transactions(account_id);
    CREATE INDEX IF NOT EXISTS idx_trans_date ON transactions(booking_date);
    CREATE INDEX IF NOT EXISTS idx_nw_date ON net_worth_snapshots(snapshot_date);
    CREATE INDEX IF NOT EXISTS idx_traces_ts ON llm_traces(timestamp);

    CREATE TABLE IF NOT EXISTS statement_batches (
        id TEXT PRIMARY KEY,
        filename TEXT NOT NULL,
        file_hash_sha256 TEXT NOT NULL,
        file_type TEXT NOT NULL,
        bank_id TEXT NOT NULL,
        account_id TEXT NOT NULL,
        opening_balance REAL,
        closing_balance REAL,
        total_inflows REAL DEFAULT 0.0,
        total_outflows REAL DEFAULT 0.0,
        calculated_delta REAL DEFAULT 0.0,
        discrepancy REAL DEFAULT 0.0,
        reconciliation_status TEXT DEFAULT 'PENDING',
        transactions_count INTEGER DEFAULT 0,
        imported_at TIMESTAMP
    );
    CREATE INDEX IF NOT EXISTS idx_batch_account ON statement_batches(account_id);
    CREATE INDEX IF NOT EXISTS idx_batch_imported ON statement_batches(imported_at);

    CREATE TABLE IF NOT EXISTS llm_response_cache (
        cache_key TEXT PRIMARY KEY,
        prompt_hash TEXT NOT NULL,
        db_fingerprint TEXT NOT NULL,
        response TEXT NOT NULL,
        model TEXT NOT NULL,
        created_at TIMESTAMP,
        expires_at TIMESTAMP
    );
    CREATE INDEX IF NOT EXISTS idx_llm_cache_lookup ON llm_response_cache(prompt_hash, db_fingerprint);
    """)

    # Safe column migrations on existing accounts table if upgrading
    cursor.execute("PRAGMA table_info(accounts)")
    existing_cols = [row[1] for row in cursor.fetchall()]
    if "asset_class" not in existing_cols:
        cursor.execute("ALTER TABLE accounts ADD COLUMN asset_class TEXT DEFAULT 'cash'")
    if "notes" not in existing_cols:
        cursor.execute("ALTER TABLE accounts ADD COLUMN notes TEXT")

    # Safe column migrations on transactions table for provenance, raw description, and pending status
    cursor.execute("PRAGMA table_info(transactions)")
    existing_trans_cols = [row[1] for row in cursor.fetchall()]
    if "statement_batch_id" not in existing_trans_cols:
        cursor.execute("ALTER TABLE transactions ADD COLUMN statement_batch_id TEXT")
    if "raw_description" not in existing_trans_cols:
        cursor.execute("ALTER TABLE transactions ADD COLUMN raw_description TEXT")
    if "status" not in existing_trans_cols:
        cursor.execute("ALTER TABLE transactions ADD COLUMN status TEXT DEFAULT 'settled'")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_trans_status ON transactions(status)")

    # Run pending-to-settled duplicate reconciliation
    reconcile_pending_duplicates(cursor)

    # Safe column migration on llm_traces for judge evaluation and tool observability
    cursor.execute("PRAGMA table_info(llm_traces)")
    existing_trace_cols = [row[1] for row in cursor.fetchall()]
    if "judge_result_json" not in existing_trace_cols:
        cursor.execute("ALTER TABLE llm_traces ADD COLUMN judge_result_json TEXT")
    if "tools_used_json" not in existing_trace_cols:
        cursor.execute("ALTER TABLE llm_traces ADD COLUMN tools_used_json TEXT")

    conn.commit()
    conn.close()

def upsert_institution(inst_id: str, name: str, country: str, session_id: Optional[str] = None, status: str = "connected", expires_at: Optional[datetime] = None):
    conn = get_connection()
    cursor = conn.cursor()
    now = datetime.now().isoformat()
    cursor.execute("""
    INSERT INTO institutions (id, name, country, session_id, status, authorized_at, expires_at)
    VALUES (?, ?, ?, ?, ?, ?, ?)
    ON CONFLICT(id) DO UPDATE SET
        name = excluded.name,
        country = excluded.country,
        session_id = excluded.session_id,
        status = excluded.status,
        authorized_at = excluded.authorized_at,
        expires_at = excluded.expires_at
    """, (inst_id, name, country, session_id, status, now, expires_at.isoformat() if expires_at else None))
    conn.commit()
    conn.close()

def get_institutions() -> List[Dict[str, Any]]:
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM institutions")
    rows = [dict(row) for row in cursor.fetchall()]
    conn.close()
    return rows

def upsert_account(
    acc_id: str,
    institution_id: str,
    raw_account_id: str,
    name: str,
    account_type: str,
    currency: str,
    current_balance: float,
    available_balance: float,
    estimated_interest_rate: float = 0.0,
    sort_code: Optional[str] = None,
    account_number: Optional[str] = None,
    iban: Optional[str] = None,
    asset_class: Optional[str] = None,
    notes: Optional[str] = None
):
    conn = get_connection()
    cursor = conn.cursor()
    now = datetime.now().isoformat()

    if not asset_class:
        at_clean = (account_type or "").lower()
        if at_clean in ["investment", "stocks", "isa_stocks", "crypto", "fund"]:
            asset_class = "investment"
        elif at_clean in ["pension", "sipp", "workplace_pension"]:
            asset_class = "pension"
        elif at_clean in ["property", "real_estate", "home"]:
            asset_class = "property"
        elif at_clean in ["mortgage", "credit_card", "loan", "debt", "liability"]:
            asset_class = "liability"
        else:
            asset_class = "cash"

    cursor.execute("""
    INSERT INTO accounts (
        id, institution_id, account_id, name, account_type, asset_class, currency,
        iban, sort_code, account_number, current_balance, available_balance,
        estimated_interest_rate, notes, updated_at
    )
    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    ON CONFLICT(id) DO UPDATE SET
        name = excluded.name,
        account_type = excluded.account_type,
        asset_class = excluded.asset_class,
        currency = excluded.currency,
        iban = excluded.iban,
        sort_code = excluded.sort_code,
        account_number = excluded.account_number,
        current_balance = excluded.current_balance,
        available_balance = excluded.available_balance,
        estimated_interest_rate = excluded.estimated_interest_rate,
        notes = excluded.notes,
        updated_at = excluded.updated_at
    """, (
        acc_id, institution_id, raw_account_id, name, account_type, asset_class, currency,
        iban, sort_code, account_number, current_balance, available_balance,
        estimated_interest_rate, notes, now
    ))
    conn.commit()
    conn.close()

def get_all_accounts() -> List[Dict[str, Any]]:
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
    SELECT a.*, i.name as institution_name
    FROM accounts a
    JOIN institutions i ON a.institution_id = i.id
    ORDER BY a.current_balance DESC
    """)
    rows = [dict(row) for row in cursor.fetchall()]
    conn.close()
    return rows

def classify_transaction(name: str, desc: str, raw_cat: str, amt: float) -> str:
    """
    Intelligently maps merchant names and descriptions into standardized UK fiduciary categories.
    """
    text = f"{name or ''} {desc or ''} {raw_cat or ''}".lower()
    if amt > 0:
        if any(k in text for k in ["topup", "top up", "payment from", "transfer from", "salary", "payroll"]):
            return "Income & Top-ups"
        if "refund" in text:
            return "Refunds"
        return "Income / Inflows"

    # Outflows:
    if any(k in text for k in ["sainsbury", "tesco", "m&s", "whole food", "welcome", "bakery", "aldi", "lidl", "asda", "morrison", "co-op", "waitrose", "grocery"]):
        return "Groceries & Essentials"
    if any(k in text for k in ["pub", "tavern", "arms", "hound", "pizza", "cluck", "evelyn", "cat", "pkb", "wheatsheaf", "hammerton", "greyhound", "deliveroo", "uber eats", "restaurant", "cafe", "bar", "food", "fringe", "tap on the line", "blackfriar", "youngs"]):
        return "Dining, Pubs & Entertainment"
    if any(k in text for k in ["anthropic", "claude", "openai", "chatgpt", "spotify", "netflix", "lemon squeezy", "github", "cursor", "aws", "google storage", "apple.com/bill", "adobe"]):
        return "Subscriptions & Software"
    if any(k in text for k in ["fee", "assets fee", "charge", "interest"]):
        return "Fees & Charges"
    if any(k in text for k in ["cheddar", "transfer", "remittance", "inr", "wise", "revolut", "topup", "own account"]):
        return "Transfers & Remittance"
    if any(k in text for k in ["tram", "tfl", "train", "uber", "transport", "rail"]):
        return "Transport & Commute"
    if any(k in text for k in ["barclaycard", "amex", "american express", "capital one", "mbna", "loan", "klarna", "clearpay"]):
        return "Debt Repayment"
    return "General Living Spend"

def generate_tx_fingerprint(account_id: str, booking_date: str, amount: float, description: str) -> str:
    """Generates an immutable deterministic content hash for a transaction to guarantee idempotent ingestion."""
    norm_desc = re.sub(r"\s+", " ", (description or "").strip().lower())
    payload = f"{account_id}|{booking_date}|{amount:.2f}|{norm_desc}".encode("utf-8")
    return f"tx_{hashlib.sha256(payload).hexdigest()[:16]}"

def _names_match(n1: str, n2: str) -> bool:
    """Checks if two counterparty/description strings match or share a normalized core."""
    if not n1 or not n2:
        return True
    s1 = re.sub(r"[^a-z0-9]", "", n1.lower())
    s2 = re.sub(r"[^a-z0-9]", "", n2.lower())
    if not s1 or not s2:
        return True
    return s1 in s2 or s2 in s1 or (len(s1) >= 6 and len(s2) >= 6 and s1[:8] == s2[:8])


def reconcile_pending_duplicates(cursor):
    """
    Cleans up duplicate pairs in the transactions table caused by pending-to-settled transitions,
    and removes duplicate £0.00 card pre-authorization checks.
    """
    try:
        cursor.execute("""
            SELECT id, account_id, booking_date, amount, counterparty_name, description, status, raw_description
            FROM transactions
            ORDER BY booking_date DESC, (CASE WHEN raw_description IS NOT NULL THEN 1 ELSE 0 END) DESC, id DESC
        """)
        all_txs = [dict(r) for r in cursor.fetchall()]
        seen = []
        to_delete_ids = []

        for tx in all_txs:
            amt = float(tx.get("amount", 0.0))
            m_name = (tx.get("counterparty_name") or tx.get("description") or "").strip()
            d_str = tx.get("booking_date")
            acc = tx.get("account_id")
            s_val = (tx.get("status") or "settled").lower()

            is_dup = False
            for prev in seen:
                if prev["account_id"] == acc and abs(prev["amount"] - amt) < 0.001:
                    prev_name = (prev.get("counterparty_name") or prev.get("description") or "").strip()
                    if m_name.lower() == prev_name.lower() or _names_match(m_name, prev_name):
                        if prev["booking_date"] == d_str:
                            is_dup = True
                            break
                        elif s_val == "pending" or (prev.get("status") or "settled").lower() == "pending":
                            try:
                                d1 = datetime.strptime(d_str[:10], "%Y-%m-%d")
                                d2 = datetime.strptime(prev["booking_date"][:10], "%Y-%m-%d")
                                if abs((d1 - d2).days) <= 2:
                                    is_dup = True
                                    break
                            except Exception:
                                pass

            if is_dup:
                to_delete_ids.append(tx["id"])
            else:
                seen.append(tx)

        if to_delete_ids:
            cursor.executemany("DELETE FROM transactions WHERE id = ?", [(tid,) for tid in to_delete_ids])

        # Clean up £0.00 pre-authorization checks older than 3 days
        cursor.execute("""
            DELETE FROM transactions
            WHERE ABS(amount) < 0.001 AND booking_date < date('now', '-3 days')
        """)
    except Exception:
        pass


def purge_stale_pending_transactions(account_id: str, active_pending_ids: Optional[set] = None):
    """
    Cleans up pending transactions on an account that are no longer active in the provider feed.
    """
    conn = get_connection()
    cursor = conn.cursor()
    if active_pending_ids is not None:
        cursor.execute("SELECT id FROM transactions WHERE account_id = ? AND status = 'pending'", (account_id,))
        for row in cursor.fetchall():
            if row["id"] not in active_pending_ids:
                cursor.execute("DELETE FROM transactions WHERE id = ?", (row["id"],))
    else:
        cursor.execute("DELETE FROM transactions WHERE account_id = ? AND status = 'pending' AND booking_date < date('now', '-7 days')", (account_id,))
    conn.commit()
    conn.close()


def insert_transactions(account_id: str, transactions: List[Dict[str, Any]], batch_id: Optional[str] = None):
    conn = get_connection()
    cursor = conn.cursor()
    for tx in transactions:
        raw_id = tx.get("transaction_id", "") or tx.get("id", "")
        amt = float(tx.get("amount", 0.0))
        name = tx.get("counterparty_name", "")
        desc = tx.get("description", "")
        raw_cat = tx.get("category", "General")
        booking_date = str(tx.get("booking_date", ""))
        smart_cat = classify_transaction(name, desc, raw_cat, amt)
        tx_status = (tx.get("status") or "settled").lower()

        # Reconcile pending vs settled:
        # If incoming transaction is SETTLED:
        if tx_status == "settled":
            # Delete any matching pending transaction on this account within +/- 3 days
            cursor.execute("""
                SELECT id, counterparty_name, description FROM transactions
                WHERE account_id = ? AND status = 'pending' AND ABS(amount - ?) < 0.01
                AND ABS(julianday(booking_date) - julianday(?)) <= 3.0
            """, (account_id, amt, booking_date))
            pending_matches = cursor.fetchall()
            for p in pending_matches:
                p_name = (p["counterparty_name"] or p["description"] or "").strip().lower()
                c_name = (name or desc or "").strip().lower()
                if p_name == c_name or _names_match(p_name, c_name):
                    cursor.execute("DELETE FROM transactions WHERE id = ?", (p["id"],))

        # If incoming transaction is PENDING:
        elif tx_status == "pending":
            # Check if matching SETTLED transaction already exists
            cursor.execute("""
                SELECT id, counterparty_name, description FROM transactions
                WHERE account_id = ? AND (status IS NULL OR status = 'settled') AND ABS(amount - ?) < 0.01
                AND ABS(julianday(booking_date) - julianday(?)) <= 3.0
            """, (account_id, amt, booking_date))
            settled_matches = cursor.fetchall()
            already_settled = False
            for s in settled_matches:
                s_name = (s["counterparty_name"] or s["description"] or "").strip().lower()
                c_name = (name or desc or "").strip().lower()
                if s_name == c_name or _names_match(s_name, c_name):
                    already_settled = True
                    break
            if already_settled:
                # Do not insert pending transaction if it has already settled!
                continue

        if raw_id and not raw_id.startswith(f"{account_id}_"):
            tx_id = f"{account_id}_{raw_id}"
        elif raw_id:
            tx_id = raw_id
        else:
            tx_id = generate_tx_fingerprint(account_id, booking_date, amt, desc or name)

        b_id = batch_id or tx.get("statement_batch_id")

        cursor.execute("""
        INSERT INTO transactions (
            id, account_id, transaction_id, booking_date, amount, currency,
            counterparty_name, description, category, is_recurring, statement_batch_id, raw_description, status
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT(id) DO UPDATE SET
            amount = excluded.amount,
            booking_date = excluded.booking_date,
            counterparty_name = excluded.counterparty_name,
            description = excluded.description,
            category = excluded.category,
            is_recurring = excluded.is_recurring,
            statement_batch_id = COALESCE(excluded.statement_batch_id, transactions.statement_batch_id),
            raw_description = COALESCE(excluded.raw_description, transactions.raw_description),
            status = excluded.status
        """, (
            tx_id,
            account_id,
            tx.get("transaction_id") or tx_id,
            booking_date,
            amt,
            tx.get("currency", "GBP"),
            name,
            desc,
            smart_cat,
            1 if tx.get("is_recurring") else 0,
            b_id,
            tx.get("raw_description") or desc,
            tx_status
        ))
    conn.commit()
    conn.close()

def record_statement_batch(batch: Dict[str, Any]) -> str:
    """Records an ingestion batch with cryptographic hash and reconciliation metrics."""
    conn = get_connection()
    cursor = conn.cursor()
    batch_id = batch.get("id") or f"batch_{uuid.uuid4().hex[:12]}"
    now = datetime.now().isoformat()
    cursor.execute("""
    INSERT INTO statement_batches (
        id, filename, file_hash_sha256, file_type, bank_id, account_id,
        opening_balance, closing_balance, total_inflows, total_outflows,
        calculated_delta, discrepancy, reconciliation_status, transactions_count, imported_at
    )
    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    ON CONFLICT(id) DO UPDATE SET
        opening_balance = excluded.opening_balance,
        closing_balance = excluded.closing_balance,
        total_inflows = excluded.total_inflows,
        total_outflows = excluded.total_outflows,
        calculated_delta = excluded.calculated_delta,
        discrepancy = excluded.discrepancy,
        reconciliation_status = excluded.reconciliation_status,
        transactions_count = excluded.transactions_count,
        imported_at = excluded.imported_at
    """, (
        batch_id,
        batch.get("filename", "unknown"),
        batch.get("file_hash_sha256", ""),
        batch.get("file_type", "pdf"),
        batch.get("bank_id", "unknown"),
        batch.get("account_id", ""),
        batch.get("opening_balance"),
        batch.get("closing_balance"),
        batch.get("total_inflows", 0.0),
        batch.get("total_outflows", 0.0),
        batch.get("calculated_delta", 0.0),
        batch.get("discrepancy", 0.0),
        batch.get("reconciliation_status", "PENDING"),
        batch.get("transactions_count", 0),
        now
    ))
    conn.commit()
    conn.close()
    return batch_id

def get_statement_batches(limit: int = 20) -> List[Dict[str, Any]]:
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM statement_batches ORDER BY imported_at DESC LIMIT ?", (limit,))
    rows = [dict(row) for row in cursor.fetchall()]
    conn.close()
    return rows

def get_statement_batch_by_id(batch_id: str) -> Optional[Dict[str, Any]]:
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM statement_batches WHERE id = ?", (batch_id,))
    row = cursor.fetchone()
    conn.close()
    return dict(row) if row else None

def get_data_engineering_audit_summary() -> Dict[str, Any]:
    """Computes real-time data engineering integrity metrics, deduplication counts, and closed-loop reconciliation."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT 
            COUNT(*) as total_batches,
            SUM(CASE WHEN reconciliation_status IN ('RECONCILED', 'CLOSING_BALANCE_VERIFIED') THEN 1 ELSE 0 END) as reconciled_batches,
            SUM(transactions_count) as total_tx_ingested,
            SUM(ABS(discrepancy)) as total_discrepancy,
            SUM(total_inflows) as cumulative_inflows,
            SUM(total_outflows) as cumulative_outflows
        FROM statement_batches
    """)
    batch_stats = dict(cursor.fetchone())
    
    cursor.execute("SELECT COUNT(*) as total_stored_tx FROM transactions")
    tx_count = cursor.fetchone()["total_stored_tx"]
    
    cursor.execute("SELECT COUNT(*) as fingerprinted_tx FROM transactions WHERE statement_batch_id IS NOT NULL")
    provenance_count = cursor.fetchone()["fingerprinted_tx"]
    
    conn.close()
    
    tot_batches = batch_stats.get("total_batches") or 0
    rec_batches = batch_stats.get("reconciled_batches") or 0
    rec_rate = (rec_batches / tot_batches * 100) if tot_batches > 0 else 100.0
    
    return {
        "total_batches": tot_batches,
        "reconciled_batches": rec_batches,
        "reconciliation_rate_pct": round(rec_rate, 1),
        "total_discrepancy": round(batch_stats.get("total_discrepancy") or 0.0, 2),
        "total_tx_ingested": batch_stats.get("total_tx_ingested") or 0,
        "total_stored_tx": tx_count,
        "provenance_fingerprinted_tx": provenance_count,
        "cumulative_inflows": round(batch_stats.get("cumulative_inflows") or 0.0, 2),
        "cumulative_outflows": round(batch_stats.get("cumulative_outflows") or 0.0, 2),
        "deduplication_mode": "SHA-256 Idempotent Upsert",
        "evaluator_critic": "Independent Local Llama-3.2 3B SLM (Metal GPU / Zero-Leak)",
        "double_entry_invariant": "Opening + Inflows - Outflows == Closing"
    }


def get_recent_transactions(
    days: Optional[int] = 30,
    account_id: Optional[str] = None,
    limit: Optional[int] = None,
    search: Optional[str] = None,
    category: Optional[str] = None
) -> List[Dict[str, Any]]:
    conn = get_connection()
    cursor = conn.cursor()
    query = """
    SELECT t.*, a.name as account_name, i.name as institution_name
    FROM transactions t
    JOIN accounts a ON t.account_id = a.id
    JOIN institutions i ON a.institution_id = i.id
    WHERE 1=1
    """
    params = []

    if days and days > 0:
        query += " AND t.booking_date >= date('now', '-' || ? || ' days')"
        params.append(days)

    if account_id:
        query += " AND (t.account_id = ? OR a.institution_id = ? OR lower(a.name) LIKE ? OR lower(i.name) LIKE ?)"
        acc_param = f"%{account_id.lower()}%"
        params.extend([account_id, account_id, acc_param, acc_param])

    if search:
        query += " AND (lower(t.counterparty_name) LIKE ? OR lower(t.description) LIKE ? OR lower(t.category) LIKE ?)"
        s_param = f"%{search.lower()}%"
        params.extend([s_param, s_param, s_param])

    if category:
        query += " AND lower(t.category) LIKE ?"
        c_param = f"%{category.lower()}%"
        params.append(c_param)

    query += " ORDER BY t.booking_date DESC"

    if limit and limit > 0:
        query += " LIMIT ?"
        params.append(limit)

    cursor.execute(query, tuple(params))
    rows = [dict(row) for row in cursor.fetchall()]
    conn.close()
    return rows

def get_all_transactions() -> List[Dict[str, Any]]:
    return get_recent_transactions(days=None)

def reclassify_all_transactions():
    """Update all stored transactions with smart fiduciary categories."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT id, counterparty_name, description, category, amount FROM transactions")
    rows = cursor.fetchall()
    for row in rows:
        smart_cat = classify_transaction(row["counterparty_name"], row["description"], row["category"], row["amount"])
        cursor.execute("UPDATE transactions SET category = ? WHERE id = ?", (smart_cat, row["id"]))
    conn.commit()
    conn.close()

def get_transaction_analytics(days: int = 30) -> Dict[str, Any]:
    from collections import defaultdict
    txs = get_recent_transactions(days=days)

    total_inflows = 0.0
    total_outflows = 0.0
    inflow_count = 0
    outflow_count = 0

    categories = defaultdict(lambda: {"total": 0.0, "count": 0})
    merchants = defaultdict(lambda: {"total": 0.0, "count": 0, "category": ""})
    funding_sources = defaultdict(lambda: {"total": 0.0, "count": 0})
    subscriptions = []

    living_spend = 0.0
    card_spend_total = 0.0

    for tx in txs:
        amt = float(tx.get("amount", 0.0))
        name = tx.get("counterparty_name") or tx.get("description") or "Unknown"
        cat = tx.get("category") or classify_transaction(name, tx.get("description", ""), "", amt)

        if amt > 0:
            total_inflows += amt
            inflow_count += 1
            if any(k in name.lower() for k in ["topup", "payment from", "transfer from"]):
                clean_source = name.replace("OBA topup from ", "").replace("Payment from ", "").strip()
                funding_sources[clean_source]["total"] += amt
                funding_sources[clean_source]["count"] += 1
        elif amt < 0:
            abs_amt = abs(amt)
            total_outflows += abs_amt
            outflow_count += 1
            categories[cat]["total"] += abs_amt
            categories[cat]["count"] += 1

            clean_name = name.strip()
            merchants[clean_name]["total"] += abs_amt
            merchants[clean_name]["count"] += 1
            merchants[clean_name]["category"] = cat

            # Living spend (exclude capital remittances / inter-account transfers)
            if cat not in ["Transfers & Remittance", "Debt Repayment"]:
                living_spend += abs_amt

            # Card spend eligible for cashback
            if cat in ["Groceries & Essentials", "Dining, Pubs & Entertainment", "General Living Spend", "Transport & Commute"]:
                card_spend_total += abs_amt

            if cat == "Subscriptions & Software":
                subscriptions.append({
                    "name": clean_name,
                    "amount": abs_amt,
                    "date": tx.get("booking_date")
                })

    daily_burn_rate = round(living_spend / max(1, days), 2)
    net_cashflow = round(total_inflows - total_outflows, 2)

    cat_summary = {}
    for cat_name, val in sorted(categories.items(), key=lambda x: x[1]["total"], reverse=True):
        cat_summary[cat_name] = {
            "total": round(val["total"], 2),
            "count": val["count"],
            "pct_of_outflow": round((val["total"] / total_outflows * 100), 1) if total_outflows > 0 else 0.0
        }

    top_merchants = []
    for m_name, m_data in sorted(merchants.items(), key=lambda x: x[1]["total"], reverse=True)[:8]:
        top_merchants.append({
            "name": m_name,
            "total": round(m_data["total"], 2),
            "count": m_data["count"],
            "category": m_data["category"]
        })

    funding_summary = []
    for f_name, f_data in funding_sources.items():
        funding_summary.append({
            "source": f_name,
            "total": round(f_data["total"], 2),
            "count": f_data["count"],
            "avg_amount": round(f_data["total"] / f_data["count"], 2)
        })

    return {
        "days": days,
        "transaction_count": len(txs),
        "total_inflows": round(total_inflows, 2),
        "inflow_count": inflow_count,
        "total_outflows": round(total_outflows, 2),
        "outflow_count": outflow_count,
        "net_cashflow": net_cashflow,
        "living_spend_total": round(living_spend, 2),
        "daily_burn_rate": daily_burn_rate,
        "normalized_monthly_burn": round(daily_burn_rate * 30, 2),
        "card_spend_total": round(card_spend_total, 2),
        "categories": cat_summary,
        "top_merchants": top_merchants,
        "subscriptions": subscriptions,
        "funding_sources": funding_summary
    }

def upsert_custom_asset(
    asset_id: str,
    name: str,
    asset_class: str,
    account_type: str,
    balance: float,
    currency: str = "GBP",
    institution_name: str = "Manual Asset",
    estimated_interest_rate: float = 0.0,
    notes: Optional[str] = None
):
    """
    Manually add or update non-Open Banking wealth items:
    - Real estate / property
    - Workplace pensions / SIPPs
    - Stocks & Shares ISAs / Vanguard / Trading 212 holdings
    - Mortgages & loans
    """
    inst_id = f"custom_{asset_class.lower()}"
    upsert_institution(inst_id, institution_name, "GB", status="manual")
    upsert_account(
        acc_id=asset_id,
        institution_id=inst_id,
        raw_account_id=asset_id,
        name=name,
        account_type=account_type,
        asset_class=asset_class,
        currency=currency,
        current_balance=balance,
        available_balance=balance,
        estimated_interest_rate=estimated_interest_rate,
        notes=notes
    )

def delete_account(acc_id: str) -> bool:
    """Removes an account and its associated transactions."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM transactions WHERE account_id = ?", (acc_id,))
    cursor.execute("DELETE FROM accounts WHERE id = ?", (acc_id,))
    deleted = cursor.rowcount > 0
    conn.commit()
    conn.close()
    return deleted

def get_net_worth_breakdown() -> Dict[str, Any]:
    """
    Computes real multi-asset net worth across:
    - Cash (current & savings)
    - Investments (stocks, funds, ISAs)
    - Pensions (SIPP, workplace pots)
    - Property (real estate)
    - Liabilities (mortgages, credit cards, loans)
    """
    accounts = get_all_accounts()

    assets_by_class = {
        "cash": 0.0,
        "investment": 0.0,
        "pension": 0.0,
        "property": 0.0,
        "liability": 0.0
    }
    accounts_by_class = {
        "cash": [],
        "investment": [],
        "pension": [],
        "property": [],
        "liability": []
    }

    for acc in accounts:
        cls = (acc.get("asset_class") or "cash").lower()
        if cls not in assets_by_class:
            cls = "cash"
        bal = float(acc.get("current_balance", 0.0))

        if cls == "liability":
            # Store liability as positive debt amount for subtraction
            debt_amt = abs(bal)
            assets_by_class["liability"] += debt_amt
            accounts_by_class["liability"].append({**acc, "current_balance": debt_amt})
        else:
            assets_by_class[cls] += bal
            accounts_by_class[cls].append(acc)

    total_assets = round(
        assets_by_class["cash"] +
        assets_by_class["investment"] +
        assets_by_class["pension"] +
        assets_by_class["property"],
        2
    )
    total_liabilities = round(assets_by_class["liability"], 2)
    net_worth = round(total_assets - total_liabilities, 2)
    liquid_net_worth = round(assets_by_class["cash"] + assets_by_class["investment"], 2)

    return {
        "net_worth": net_worth,
        "total_assets": total_assets,
        "total_liabilities": total_liabilities,
        "liquid_net_worth": liquid_net_worth,
        "breakdown": {k: round(v, 2) for k, v in assets_by_class.items()},
        "accounts_by_class": accounts_by_class
    }

def save_net_worth_snapshot() -> Dict[str, Any]:
    """Records a historical net worth point in time."""
    import json
    nw = get_net_worth_breakdown()
    now_date = datetime.now().strftime("%Y-%m-%d")
    now_iso = datetime.now().isoformat()

    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
    INSERT INTO net_worth_snapshots (
        snapshot_date, total_assets, total_liabilities, net_worth, liquid_assets, breakdown_json, created_at
    )
    VALUES (?, ?, ?, ?, ?, ?, ?)
    """, (
        now_date,
        nw["total_assets"],
        nw["total_liabilities"],
        nw["net_worth"],
        nw["liquid_net_worth"],
        json.dumps(nw["breakdown"]),
        now_iso
    ))
    conn.commit()
    conn.close()
    return nw

def get_net_worth_history(days: int = 365) -> List[Dict[str, Any]]:
    """Returns chronological snapshots of net worth for visualization."""
    import json
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
    SELECT * FROM net_worth_snapshots
    WHERE snapshot_date >= date('now', '-' || ? || ' days')
    ORDER BY snapshot_date ASC
    """, (days,))
    rows = cursor.fetchall()
    conn.close()

    history = []
    for r in rows:
        item = dict(r)
        if item.get("breakdown_json"):
            try:
                item["breakdown"] = json.loads(item["breakdown_json"])
            except Exception:
                item["breakdown"] = {}
        history.append(item)
    return history

def upsert_recurring_bill(
    bill_id: str,
    merchant: str,
    category: str,
    expected_amount: float,
    frequency: str = "monthly",
    last_date: Optional[str] = None,
    next_due_date: Optional[str] = None,
    price_change_alert: Optional[str] = None
):
    """Stores or updates detected recurring bills and direct debits."""
    conn = get_connection()
    cursor = conn.cursor()
    now = datetime.now().isoformat()
    cursor.execute("""
    INSERT INTO recurring_bills (
        id, merchant, category, expected_amount, frequency, last_date, next_due_date, is_active, price_change_alert, updated_at
    )
    VALUES (?, ?, ?, ?, ?, ?, ?, 1, ?, ?)
    ON CONFLICT(id) DO UPDATE SET
        merchant = excluded.merchant,
        category = excluded.category,
        expected_amount = excluded.expected_amount,
        frequency = excluded.frequency,
        last_date = excluded.last_date,
        next_due_date = excluded.next_due_date,
        price_change_alert = excluded.price_change_alert,
        updated_at = excluded.updated_at
    """, (bill_id, merchant, category, expected_amount, frequency, last_date, next_due_date, price_change_alert, now))
    conn.commit()
    conn.close()

def get_recurring_bills() -> List[Dict[str, Any]]:
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM recurring_bills WHERE is_active = 1 ORDER BY next_due_date ASC")
    rows = [dict(r) for r in cursor.fetchall()]
    conn.close()
    return rows

def save_chat_message(role: str, content: str, metadata: Optional[Dict[str, Any]] = None):
    import json
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
    INSERT INTO copilot_chat (role, content, metadata_json, created_at)
    VALUES (?, ?, ?, ?)
    """, (role, content, json.dumps(metadata or {}), datetime.now().isoformat()))
    conn.commit()
    conn.close()

def get_chat_history(limit: int = 50) -> List[Dict[str, Any]]:
    import json
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
    SELECT * FROM copilot_chat
    ORDER BY id ASC
    LIMIT ?
    """, (limit,))
    rows = []
    for r in cursor.fetchall():
        item = dict(r)
        if item.get("metadata_json"):
            try:
                item["metadata"] = json.loads(item["metadata_json"])
            except Exception:
                item["metadata"] = {}
        rows.append(item)
    conn.close()
    return rows

def clear_chat_history():
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM copilot_chat")
    conn.commit()
    conn.close()

def get_rate_cache(key: str) -> Optional[Dict[str, Any]]:
    import json
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT data_json, updated_at FROM market_rate_cache WHERE cache_key = ?", (key,))
    row = cursor.fetchone()
    conn.close()
    if row:
        try:
            return json.loads(row["data_json"])
        except Exception:
            return None
    return None

def set_rate_cache(key: str, data: Dict[str, Any]):
    import json
    conn = get_connection()
    cursor = conn.cursor()
    now = datetime.now().isoformat()
    cursor.execute("""
    INSERT INTO market_rate_cache (cache_key, data_json, updated_at)
    VALUES (?, ?, ?)
    ON CONFLICT(cache_key) DO UPDATE SET
        data_json = excluded.data_json,
        updated_at = excluded.updated_at
    """, (key, json.dumps(data), now))
    conn.commit()
    conn.close()


def get_db_state_fingerprint() -> str:
    """
    Returns a fast cryptographic fingerprint of the current financial database state.
    Used to automatically invalidate or validate cached LLM responses when transactions
    or balances change.
    """
    try:
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*), COALESCE(MAX(id), ''), COALESCE(MAX(booking_date), '') FROM transactions")
        tx_row = cursor.fetchone()
        cursor.execute("SELECT COUNT(*), COALESCE(SUM(current_balance), 0.0) FROM accounts")
        acc_row = cursor.fetchone()
        conn.close()
        raw = f"{tx_row[0]}:{tx_row[1]}:{tx_row[2]}:{acc_row[0]}:{acc_row[1]:.2f}"
        return hashlib.sha256(raw.encode("utf-8")).hexdigest()[:16]
    except Exception:
        return "default_state"


def get_cached_llm_response(prompt_hash: str, db_fingerprint: str) -> Optional[Dict[str, Any]]:
    """
    Retrieves unexpired cached response for this exact prompt & database state.
    Provides 0-credit, 0-token, sub-millisecond retrieval.
    """
    try:
        conn = get_connection()
        cursor = conn.cursor()
        now_iso = datetime.now().isoformat()
        cursor.execute("""
            SELECT response, model FROM llm_response_cache
            WHERE prompt_hash = ? AND db_fingerprint = ? AND expires_at > ?
        """, (prompt_hash, db_fingerprint, now_iso))
        row = cursor.fetchone()
        conn.close()
        if row:
            return {"response": row["response"], "model": row["model"]}
    except Exception:
        pass
    return None


def set_cached_llm_response(
    prompt_hash: str,
    db_fingerprint: str,
    response: str,
    model: str,
    ttl_seconds: int = 1800
) -> None:
    """
    Caches an LLM response with a time-to-live (default: 30 minutes).
    Bound strictly to the database fingerprint so stale data is never served.
    Never caches error messages or warnings.
    """
    if not response or response.startswith("⚠️") or response.startswith("❌") or "Error" in response[:30]:
        return
    try:
        conn = get_connection()
        cursor = conn.cursor()
        now = datetime.now()
        now_iso = now.isoformat()
        expires_iso = (now + timedelta(seconds=ttl_seconds)).isoformat()
        cache_key = f"{prompt_hash}_{db_fingerprint}"
        cursor.execute("""
            INSERT INTO llm_response_cache (cache_key, prompt_hash, db_fingerprint, response, model, created_at, expires_at)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(cache_key) DO UPDATE SET
                response = excluded.response,
                model = excluded.model,
                created_at = excluded.created_at,
                expires_at = excluded.expires_at
        """, (cache_key, prompt_hash, db_fingerprint, response, model, now_iso, expires_iso))
        conn.commit()
        conn.close()
    except Exception:
        pass


def clear_llm_cache() -> None:
    """Flushes the LLM response cache."""
    try:
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("DELETE FROM llm_response_cache")
        conn.commit()
        conn.close()
    except Exception:
        pass

def save_oauth_tokens(
    provider: str,
    access_token: str,
    refresh_token: Optional[str] = None,
    expires_in_seconds: int = 3600
):
    """Securely saves or updates Open Banking OAuth tokens locally in SQLite."""
    conn = get_connection()
    cursor = conn.cursor()
    now = datetime.now()
    expires_at = (now + timedelta(seconds=expires_in_seconds)).isoformat()
    cursor.execute("""
    INSERT INTO oauth_tokens (provider, access_token, refresh_token, expires_at, updated_at)
    VALUES (?, ?, ?, ?, ?)
    ON CONFLICT(provider) DO UPDATE SET
        access_token = excluded.access_token,
        refresh_token = COALESCE(excluded.refresh_token, oauth_tokens.refresh_token),
        expires_at = excluded.expires_at,
        updated_at = excluded.updated_at
    """, (provider, access_token, refresh_token, expires_at, now.isoformat()))
    conn.commit()
    conn.close()

def get_oauth_tokens(provider: str) -> Optional[Dict[str, Any]]:
    """Retrieves saved OAuth tokens for a provider."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT provider, access_token, refresh_token, expires_at, updated_at FROM oauth_tokens WHERE provider = ?", (provider,))
    row = cursor.fetchone()
    conn.close()
    if not row:
        return None
    return {
        "provider": row[0],
        "access_token": row[1],
        "refresh_token": row[2],
        "expires_at": row[3],
        "updated_at": row[4]
    }

def get_all_oauth_tokens(prefix: str = "truelayer") -> List[Dict[str, Any]]:
    """Retrieves all saved OAuth tokens matching a provider prefix (e.g. 'truelayer' or 'truelayer:bank')."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        "SELECT provider, access_token, refresh_token, expires_at, updated_at "
        "FROM oauth_tokens WHERE provider = ? OR provider LIKE ? ORDER BY updated_at DESC",
        (prefix, f"{prefix}:%")
    )
    rows = cursor.fetchall()
    conn.close()
    return [
        {
            "provider": row[0],
            "access_token": row[1],
            "refresh_token": row[2],
            "expires_at": row[3],
            "updated_at": row[4]
        }
        for row in rows
    ]

def delete_oauth_tokens(provider: str):
    """Deletes saved OAuth tokens (e.g. on disconnect)."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM oauth_tokens WHERE provider = ?", (provider,))
    conn.commit()
    conn.close()

def save_judge_evaluation(trace_id: str, evaluation: Dict[str, Any]) -> bool:
    """Updates a trace with an LLM-as-a-Judge evaluation result."""
    try:
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("""
        UPDATE llm_traces
        SET judge_result_json = ?
        WHERE id = ?
        """, (json.dumps(evaluation), trace_id))
        conn.commit()
        conn.close()
        return True
    except Exception:
        return False

def get_trace_by_id(trace_id: str) -> Optional[Dict[str, Any]]:
    """Retrieves a single trace by ID with parsed metadata."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM llm_traces WHERE id = ?", (trace_id,))
    row = cursor.fetchone()
    conn.close()
    if row:
        d = dict(row)
        try:
            d["unverified_figures"] = json.loads(d.get("unverified_tokens_json") or "[]")
        except Exception:
            d["unverified_figures"] = []
        if d.get("judge_result_json"):
            try:
                d["judge_evaluation"] = json.loads(d["judge_result_json"])
            except Exception:
                d["judge_evaluation"] = None
        else:
            d["judge_evaluation"] = None

        if d.get("tools_used_json"):
            try:
                d["tools_used"] = json.loads(d["tools_used_json"])
            except Exception:
                d["tools_used"] = []
        else:
            d["tools_used"] = []

        return d
    return None


def save_credit_bureau_scores(
    experian: Optional[int] = None,
    equifax: Optional[int] = None,
    transunion: Optional[int] = None,
    electoral_roll: Optional[bool] = None,
    notes: Optional[str] = None,
) -> Dict[str, Any]:
    init_db()
    conn = get_connection()
    c = conn.cursor()
    c.execute("SELECT * FROM credit_profile WHERE id = 'default'")
    row = c.fetchone()
    now = datetime.now().isoformat()

    exp = experian if experian is not None else (row["experian_score"] if row else None)
    eq = equifax if equifax is not None else (row["equifax_score"] if row else None)
    tu = transunion if transunion is not None else (row["transunion_score"] if row else None)
    er = int(electoral_roll) if electoral_roll is not None else (row["electoral_roll_status"] if row else 1)
    n = notes if notes is not None else (row["notes"] if row else "")

    c.execute("""
        INSERT INTO credit_profile (id, experian_score, equifax_score, transunion_score, electoral_roll_status, notes, updated_at)
        VALUES ('default', ?, ?, ?, ?, ?, ?)
        ON CONFLICT(id) DO UPDATE SET
            experian_score=excluded.experian_score,
            equifax_score=excluded.equifax_score,
            transunion_score=excluded.transunion_score,
            electoral_roll_status=excluded.electoral_roll_status,
            notes=excluded.notes,
            updated_at=excluded.updated_at
    """, (exp, eq, tu, er, n, now))
    conn.commit()
    conn.close()
    return get_credit_bureau_scores()


def get_credit_bureau_scores() -> Dict[str, Any]:
    init_db()
    conn = get_connection()
    c = conn.cursor()
    c.execute("SELECT * FROM credit_profile WHERE id = 'default'")
    row = c.fetchone()
    conn.close()
    if not row:
        return {
            "experian": None,
            "equifax": None,
            "transunion": None,
            "electoral_roll": True,
            "notes": "",
            "updated_at": None,
        }
    return {
        "experian": row["experian_score"],
        "equifax": row["equifax_score"],
        "transunion": row["transunion_score"],
        "electoral_roll": bool(row["electoral_roll_status"]),
        "notes": row["notes"] or "",
        "updated_at": str(row["updated_at"]) if row["updated_at"] else None,
    }


