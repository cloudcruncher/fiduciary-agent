import csv
import io
from typing import Any, Dict

from fiduciary.storage.db import insert_transactions, upsert_account, upsert_institution


def detect_bank_and_parse(filename: str, content: str) -> Dict[str, Any]:
    """
    Parses statement exports from Chase, HSBC, Lloyds, NatWest, Revolut, Zopa,
    or generic bank CSVs.
    """
    reader = csv.reader(io.StringIO(content))
    rows = [r for r in reader if any(field.strip() for field in r)]
    if not rows:
        raise ValueError("CSV file is empty.")

    header = [h.strip().lower() for h in rows[0]]
    data_rows = rows[1:]

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
        elif any(k in col for k in ["description", "narrative", "merchant", "details"]):
            desc_idx = idx
        elif col in ["amount", "value"]:
            amount_idx = idx
        elif "debit" in col:
            debit_idx = idx
        elif "credit" in col:
            credit_idx = idx
        elif "balance" in col:
            balance_idx = idx

    transactions = []
    latest_balance = 0.0

    for r in data_rows:
        if len(r) <= max(date_idx, desc_idx):
            continue

        date_str = r[date_idx].strip() if date_idx != -1 else ""
        desc_str = r[desc_idx].strip() if desc_idx != -1 else "Transaction"

        # Determine Amount
        amt = 0.0
        if amount_idx != -1 and len(r) > amount_idx:
            val_clean = r[amount_idx].replace("£", "").replace(",", "").strip()
            try:
                amt = float(val_clean)
            except ValueError:
                amt = 0.0
        elif debit_idx != -1 and credit_idx != -1:
            debit_val = r[debit_idx].replace("£", "").replace(",", "").strip() if len(r) > debit_idx else ""
            credit_val = r[credit_idx].replace("£", "").replace(",", "").strip() if len(r) > credit_idx else ""
            if debit_val:
                try:
                    amt = -abs(float(debit_val))
                except ValueError:
                    pass
            elif credit_val:
                try:
                    amt = abs(float(credit_val))
                except ValueError:
                    pass

        # Check balance column if available
        if balance_idx != -1 and len(r) > balance_idx:
            b_clean = r[balance_idx].replace("£", "").replace(",", "").strip()
            try:
                latest_balance = float(b_clean)
            except ValueError:
                pass

        if date_str:
            transactions.append({
                "transaction_id": f"{bank_id}_{len(transactions)+1}",
                "booking_date": date_str[:10],
                "amount": amt,
                "currency": "GBP",
                "counterparty_name": desc_str,
                "description": desc_str,
                "category": "General"
            })

    # If no balance column was found, approximate from cumulative transactions or default
    final_balance = latest_balance if balance_idx != -1 else max(0.0, sum(t["amount"] for t in transactions))

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
        insert_transactions(acc_id, transactions)

    return {
        "bank_name": bank_name,
        "account_name": acc_name,
        "balance": final_balance,
        "transactions_imported": len(transactions)
    }
