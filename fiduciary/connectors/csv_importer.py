import csv
import hashlib
import io
from typing import Any, Dict

from fiduciary.connectors.pdf_importer import clean_amount, parse_date_str
from fiduciary.storage.db import (
    classify_transaction,
    generate_tx_fingerprint,
    insert_transactions,
    record_statement_batch,
    upsert_account,
    upsert_institution,
)


def detect_bank_and_parse(filename: str, content: str) -> Dict[str, Any]:
    """
    Parses statement exports from Chase, HSBC, Lloyds, NatWest, Revolut, Zopa,
    or generic bank CSVs with cryptographic lineage, idempotent deduplication,
    and closed-loop double-entry accounting reconciliation.
    """
    reader = csv.reader(io.StringIO(content))
    rows = [r for r in reader if any(field.strip() for field in r)]
    if not rows:
        raise ValueError("CSV file is empty.")

    header = [h.strip().lower() for h in rows[0]]
    data_rows = rows[1:]

    # Compute raw file cryptographic provenance hash (Bronze layer)
    content_hash = hashlib.sha256(content.encode("utf-8")).hexdigest()
    batch_id = f"batch_csv_{content_hash[:12]}"

    # Detect institution from filename or header
    fn_lower = filename.lower()
    if "chase" in fn_lower:
        bank_id, bank_name = "chase", "Chase UK"
    elif "hsbc" in fn_lower:
        bank_id, bank_name = "hsbc", "HSBC UK"
    elif "lloyds" in fn_lower:
        bank_id, bank_name = "lloyds", "Lloyds Bank"
    elif "natwest" in fn_lower:
        bank_id, bank_name = "natwest", "NatWest"
    elif "revolut" in fn_lower:
        bank_id, bank_name = "revolut", "Revolut UK"
    elif "zopa" in fn_lower:
        bank_id, bank_name = "zopa", "Zopa Bank"
    elif "barclays" in fn_lower:
        bank_id, bank_name = "barclays", "Barclays Bank UK"
    elif "santander" in fn_lower:
        bank_id, bank_name = "santander", "Santander UK"
    elif "monzo" in fn_lower:
        bank_id, bank_name = "monzo", "Monzo Bank"
    elif "starling" in fn_lower:
        bank_id, bank_name = "starling", "Starling Bank"
    else:
        bank_id, bank_name = "imported_bank", "Imported Bank"

    upsert_institution(bank_id, bank_name, "GB", status="connected")

    # Find column indices
    date_idx = -1
    desc_idx = -1
    amount_idx = -1
    debit_idx = -1
    credit_idx = -1
    balance_idx = -1

    for idx, col in enumerate(header):
        if any(k in col for k in ["date", "started date", "booking"]):
            date_idx = idx
        elif any(k in col for k in ["description", "narrative", "merchant", "details", "reference"]):
            desc_idx = idx
        elif col in ["amount", "value", "net"]:
            amount_idx = idx
        elif "debit" in col or "paid out" in col or "money out" in col:
            debit_idx = idx
        elif "credit" in col or "paid in" in col or "money in" in col:
            credit_idx = idx
        elif "balance" in col:
            balance_idx = idx

    transactions = []
    observed_balances = []

    for r in data_rows:
        if len(r) <= max(date_idx, desc_idx):
            continue

        raw_date = r[date_idx].strip() if date_idx != -1 else ""
        desc_str = r[desc_idx].strip() if desc_idx != -1 else "Transaction"

        # Normalize Date (properly handles UK DD/MM/YYYY, DD-MM-YYYY, YYYY-MM-DD)
        booking_date = parse_date_str(raw_date) or (raw_date[:10] if raw_date else "2026-01-01")

        # Determine Amount
        amt = 0.0
        if amount_idx != -1 and len(r) > amount_idx:
            amt_val = clean_amount(r[amount_idx])
            amt = amt_val if amt_val is not None else 0.0
        elif debit_idx != -1 and credit_idx != -1:
            debit_val = clean_amount(r[debit_idx]) if len(r) > debit_idx else None
            credit_val = clean_amount(r[credit_idx]) if len(r) > credit_idx else None
            if debit_val is not None and debit_val != 0.0:
                amt = -abs(debit_val)
            elif credit_val is not None and credit_val != 0.0:
                amt = abs(credit_val)

        # Check balance column if available
        row_balance = None
        if balance_idx != -1 and len(r) > balance_idx:
            bal_val = clean_amount(r[balance_idx])
            if bal_val is not None:
                row_balance = bal_val
                observed_balances.append((booking_date, bal_val))

        if raw_date and amt != 0.0:
            category = classify_transaction(desc_str[:40], desc_str, "General", amt)
            acc_id = f"{bank_id}_statement_account"
            fingerprint = generate_tx_fingerprint(acc_id, booking_date, amt, desc_str)

            transactions.append({
                "transaction_id": fingerprint,
                "booking_date": booking_date,
                "amount": round(amt, 2),
                "currency": "GBP",
                "counterparty_name": desc_str[:60],
                "description": desc_str,
                "category": category,
                "raw_description": desc_str,
                "row_balance": row_balance,
                "statement_batch_id": batch_id
            })

    # Closed-Loop Accounting Balance Invariant Verification:
    # Opening + Inflows - Outflows == Closing
    total_inflows = round(sum(t["amount"] for t in transactions if t["amount"] > 0), 2)
    total_outflows = round(sum(abs(t["amount"]) for t in transactions if t["amount"] < 0), 2)
    calculated_delta = round(total_inflows - total_outflows, 2)

    opening_balance = None
    closing_balance = None
    discrepancy = 0.0
    reconciliation_status = "UNVERIFIED_NO_BALANCES"

    if observed_balances:
        first_row_bal = observed_balances[0][1]
        last_row_bal = observed_balances[-1][1]
        is_reverse_chrono = observed_balances[0][0] >= observed_balances[-1][0] and len(observed_balances) > 1

        if is_reverse_chrono:
            closing_balance = first_row_bal
            # Oldest transaction is the last transaction in reverse-chrono
            oldest_tx_amt = transactions[-1]["amount"] if transactions else 0.0
            opening_balance = round(last_row_bal - oldest_tx_amt, 2)
        else:
            closing_balance = last_row_bal
            # Oldest transaction is the first transaction in chrono order
            first_tx_amt = transactions[0]["amount"] if transactions else 0.0
            opening_balance = round(first_row_bal - first_tx_amt, 2)

        expected_delta = round(closing_balance - opening_balance, 2)
        discrepancy = round(calculated_delta - expected_delta, 2)

        if abs(discrepancy) < 0.02:
            reconciliation_status = "RECONCILED"
            discrepancy = 0.0
        else:
            reconciliation_status = "UNRECONCILED_GAP"

        final_balance = closing_balance
    else:
        final_balance = max(0.0, calculated_delta)
        reconciliation_status = "CASHFLOW_ESTIMATED"

    acc_id = f"{bank_id}_statement_account"
    acc_name = f"{bank_name} Imported Account"

    upsert_account(
        acc_id=acc_id,
        institution_id=bank_id,
        raw_account_id=acc_id,
        name=acc_name,
        account_type="checking",
        currency="GBP",
        current_balance=final_balance,
        available_balance=final_balance,
        estimated_interest_rate=0.0
    )

    if transactions:
        insert_transactions(acc_id, transactions, batch_id=batch_id)

    # Record Provenance & Batch Lineage in Bronze/Silver store
    record_statement_batch({
        "id": batch_id,
        "filename": filename,
        "file_hash_sha256": content_hash,
        "file_type": "csv",
        "bank_id": bank_id,
        "account_id": acc_id,
        "opening_balance": opening_balance,
        "closing_balance": final_balance,
        "total_inflows": total_inflows,
        "total_outflows": total_outflows,
        "calculated_delta": calculated_delta,
        "discrepancy": discrepancy,
        "reconciliation_status": reconciliation_status,
        "transactions_count": len(transactions)
    })

    return {
        "status": "success",
        "batch_id": batch_id,
        "bank_id": bank_id,
        "bank_name": bank_name,
        "account_id": acc_id,
        "account_name": acc_name,
        "balance": final_balance,
        "transactions_imported": len(transactions),
        "total_inflows": total_inflows,
        "total_outflows": total_outflows,
        "calculated_delta": calculated_delta,
        "opening_balance": opening_balance,
        "closing_balance": final_balance,
        "discrepancy": discrepancy,
        "reconciliation_status": reconciliation_status,
        "sample_transactions": transactions[:5]
    }
