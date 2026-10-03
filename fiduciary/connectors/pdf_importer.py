import io
import re
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple

import pypdf

from fiduciary.storage.db import (
    classify_transaction,
    insert_transactions,
    upsert_account,
    upsert_institution,
)

UK_BANKS = [
    ("barclays", "Barclays Bank UK"),
    ("hsbc", "HSBC UK"),
    ("natwest", "NatWest"),
    ("lloyds", "Lloyds Bank"),
    ("santander", "Santander UK"),
    ("nationwide", "Nationwide Building Society"),
    ("chase", "Chase UK"),
    ("monzo", "Monzo Bank"),
    ("starling", "Starling Bank"),
    ("revolut", "Revolut UK"),
    ("halifax", "Halifax"),
    ("first direct", "First Direct"),
    ("tsb", "TSB Bank"),
    ("virgin money", "Virgin Money"),
    ("metro bank", "Metro Bank"),
    ("co-operative", "The Co-operative Bank"),
    ("zopa", "Zopa Bank"),
]

MONTH_NAMES = {
    "jan": 1, "january": 1,
    "feb": 2, "february": 2,
    "mar": 3, "march": 3,
    "apr": 4, "april": 4,
    "may": 5,
    "jun": 6, "june": 6,
    "jul": 7, "july": 7,
    "aug": 8, "august": 8,
    "sep": 9, "sept": 9, "september": 9,
    "oct": 10, "october": 10,
    "nov": 11, "november": 11,
    "dec": 12, "december": 12
}

def extract_text_from_pdf(pdf_bytes: bytes) -> str:
    """Extracts raw text from PDF bytes using pypdf."""
    reader = pypdf.PdfReader(io.BytesIO(pdf_bytes))
    pages_text = []
    for page in reader.pages:
        txt = page.extract_text()
        if txt:
            pages_text.append(txt)
    return "\n".join(pages_text)

def detect_bank_from_text(filename: str, full_text: str) -> Tuple[str, str]:
    """Identifies the issuing UK financial institution."""
    combined = (filename + " " + full_text[:2000]).lower()
    for bank_id, bank_name in UK_BANKS:
        if bank_id in combined:
            return bank_id, bank_name
    return "imported_pdf_bank", "Imported Bank (PDF)"

def parse_date_str(raw: str, default_year: int = 2026) -> Optional[str]:
    """Normalizes varied date formats into YYYY-MM-DD."""
    raw = raw.strip()
    # YYYY-MM-DD or YYYY/MM/DD
    m = re.match(r"^(\d{4})[/.-](\d{1,2})[/.-](\d{1,2})$", raw)
    if m:
        year, month, day = int(m.group(1)), int(m.group(2)), int(m.group(3))
        return f"{year:04d}-{month:02d}-{day:02d}"

    # DD/MM/YYYY or DD-MM-YYYY or DD.MM.YYYY
    m = re.match(r"^(\d{1,2})[/.-](\d{1,2})[/.-](\d{4})$", raw)
    if m:
        day, month, year = int(m.group(1)), int(m.group(2)), int(m.group(3))
        return f"{year:04d}-{month:02d}-{day:02d}"

    # DD/MM/YY or DD-MM-YY
    m = re.match(r"^(\d{1,2})[/.-](\d{1,2})[/.-](\d{2})$", raw)
    if m:
        day, month, year = int(m.group(1)), int(m.group(2)), 2000 + int(m.group(3))
        return f"{year:04d}-{month:02d}-{day:02d}"

    # DD-Mon-YYYY or DD Mon YYYY (e.g. 15 Sep 2026 or 15-Sep-2026)
    m = re.match(r"^(\d{1,2})[\s-]+([A-Za-z]+)[\s-]+(\d{4})$", raw)
    if m:
        day = int(m.group(1))
        mon_str = m.group(2).lower()
        year = int(m.group(3))
        mon = MONTH_NAMES.get(mon_str[:3])
        if mon:
            return f"{year:04d}-{mon:02d}-{day:02d}"

    # DD-Mon-YY or DD Mon YY (e.g. 15 Sep 26 or 15-Sep-26)
    m = re.match(r"^(\d{1,2})[\s-]+([A-Za-z]+)[\s-]+(\d{2})$", raw)
    if m:
        day = int(m.group(1))
        mon_str = m.group(2).lower()
        year = 2000 + int(m.group(3))
        mon = MONTH_NAMES.get(mon_str[:3])
        if mon:
            return f"{year:04d}-{mon:02d}-{day:02d}"

    # DD-Mon or DD Mon (e.g. 15 Sep or 15-Sep)
    m = re.match(r"^(\d{1,2})[\s-]+([A-Za-z]+)$", raw)
    if m:
        day = int(m.group(1))
        mon_str = m.group(2).lower()
        mon = MONTH_NAMES.get(mon_str[:3])
        if mon:
            return f"{default_year:04d}-{mon:02d}-{day:02d}"

    return None

def clean_amount(val_str: str) -> Optional[float]:
    """Cleans currency strings like '£1,234.50', '24.50 CR', '-12.00' into a float."""
    v = val_str.replace("£", "").replace(",", "").strip()
    is_credit = False
    is_debit = False

    if v.upper().endswith("CR"):
        is_credit = True
        v = v[:-2].strip()
    elif v.upper().endswith("DR"):
        is_debit = True
        v = v[:-2].strip()

    try:
        amt = float(v)
        if is_debit and amt > 0:
            amt = -amt
        elif is_credit and amt < 0:
            amt = abs(amt)
        return amt
    except ValueError:
        return None

class PDFStatementParser:
    """
    High-fidelity, privacy-preserving UK Bank Statement PDF Parser.
    Extracts tabular statements directly from PDF text using deterministic regex
    and optional local LLM parsing assistance (running 100% on Apple Silicon GPU).
    """

    def __init__(self):
        pass

    def parse_pdf(self, filename: str, pdf_bytes: bytes) -> Dict[str, Any]:
        raw_text = extract_text_from_pdf(pdf_bytes)
        if not raw_text.strip():
            raise ValueError("Could not extract any readable text from this PDF. It may be a scanned image or protected.")

        bank_id, bank_name = detect_bank_from_text(filename, raw_text)
        account_id = f"acc_{bank_id}_imported"

        # Look for Sort Code and Account Number (auto-masked for zero-risk privacy)
        sort_code_match = re.search(r"\b(\d{2}-\d{2}-\d{2})\b", raw_text)
        account_num_match = re.search(r"\b(\d{8})\b", raw_text)
        raw_sort = sort_code_match.group(1) if sort_code_match else "00-00-00"
        raw_acc = account_num_match.group(1) if account_num_match else "00000000"
        sort_code = f"••-••-{raw_sort[-2:]}"
        account_num = f"••••{raw_acc[-4:]}"

        # Determine statement year
        year_match = re.search(r"\b(202[3-7])\b", raw_text)
        statement_year = int(year_match.group(1)) if year_match else datetime.now().year

        transactions, detected_balance = self._extract_transactions_regex(raw_text, statement_year)

        # If regex extracted very few records from a lengthy statement, attempt local LLM extraction
        if len(transactions) < 2 and len(raw_text.splitlines()) > 15:
            llm_txs = self._extract_via_local_llm(raw_text)
            if len(llm_txs) > len(transactions):
                transactions = llm_txs

        # Register institution & account in SQLite
        upsert_institution(bank_id, bank_name, "GB", status="connected")
        upsert_account(
            acc_id=account_id,
            institution_id=bank_id,
            raw_account_id=account_id,
            name=f"{bank_name} Statement",
            account_type="TRANSACTION",
            currency="GBP",
            current_balance=detected_balance if detected_balance is not None else 0.0,
            available_balance=detected_balance if detected_balance is not None else 0.0,
            sort_code=sort_code,
            account_number=account_num,
            asset_class="cash"
        )

        # Categorize transactions
        final_txs = []
        for idx, t in enumerate(transactions):
            desc = t.get("description", "Transaction")
            amt = t.get("amount", 0.0)
            date_val = t.get("date", datetime.now().strftime("%Y-%m-%d"))
            category = classify_transaction(desc[:40], desc, "General", amt)

            final_txs.append({
                "transaction_id": f"tx_pdf_{bank_id}_{idx}_{abs(hash(desc + date_val + str(amt))) % 1000000}",
                "amount": amt,
                "currency": "GBP",
                "description": desc,
                "booking_date": date_val,
                "category": category,
                "counterparty_name": desc[:40]
            })

        if final_txs:
            insert_transactions(account_id, final_txs)

        return {
            "status": "success",
            "bank_id": bank_id,
            "bank_name": bank_name,
            "account_id": account_id,
            "transactions_imported": len(final_txs),
            "detected_balance": detected_balance,
            "sample_transactions": final_txs[:5]
        }

    def _extract_transactions_regex(self, text: str, default_year: int) -> Tuple[List[Dict[str, Any]], Optional[float]]:
        """Parses standard multi-column and single-column UK bank statements."""
        lines = [ln.strip() for ln in text.splitlines() if ln.strip()]
        transactions = []
        detected_balance = None

        # Detect closing balance
        for ln in lines:
            m_bal = re.search(r"(?:closing|ending|new|carried forward)\s+balance[:\s]+£?([0-9,]+\.[0-9]{2})", ln, re.IGNORECASE)
            if m_bal:
                cleaned = clean_amount(m_bal.group(1))
                if cleaned is not None:
                    detected_balance = cleaned

        # Regex for finding lines that begin with a Date
        # Supports: "2026-09-15", "15/09/2026", "15-09-2026", "15.09.2026", "15 Sep 2026", "15-Sep-2026", "15 Sep", etc.
        date_pattern = re.compile(
            r"^(\d{4}[/.-]\d{1,2}[/.-]\d{1,2}|\d{1,2}[/.-]\d{1,2}[/.-](?:\d{4}|\d{2})|\d{1,2}[\s-]+[A-Za-z]{3,9}(?:[\s-]+(?:\d{4}|\d{2}))?)\s+(.*)$"
        )

        # Regex for amounts at the end of a line (e.g. "-12.50", "£12.50", "12.50 1,450.00")
        amount_finder = re.compile(r"[-+]?£?[0-9,]+\.[0-9]{2}(?:\s*(?:CR|DR))?")

        i = 0
        while i < len(lines):
            line = lines[i]
            m_date = date_pattern.match(line)
            if m_date:
                raw_date = m_date.group(1)
                rest = m_date.group(2)

                normalized_date = parse_date_str(raw_date, default_year=default_year)
                if not normalized_date:
                    i += 1
                    continue

                # Find all money figures on this line
                amounts = amount_finder.findall(rest)

                # If no amounts on this line, check if the amount appears on the immediately following line
                if not amounts and i + 1 < len(lines):
                    next_line = lines[i + 1].strip()
                    next_amounts = amount_finder.findall(next_line)
                    if next_amounts and not date_pattern.match(next_line):
                        rest = f"{rest} {next_line}"
                        amounts = next_amounts
                        i += 1

                if amounts:
                    desc = ""
                    running_bal = None
                    if len(amounts) >= 2:
                        tx_amt_raw = amounts[-2]
                        bal_raw = amounts[-1]
                        idx = rest.rfind(tx_amt_raw)
                        desc = rest[:idx].strip() if idx != -1 else rest.strip()
                        running_bal = clean_amount(bal_raw)
                        if detected_balance is None and running_bal is not None:
                            detected_balance = running_bal
                    else:
                        tx_amt_raw = amounts[-1]
                        idx = rest.rfind(tx_amt_raw)
                        desc = rest[:idx].strip() if idx != -1 else ""
                        if not desc:
                            desc = rest[idx + len(tx_amt_raw):].strip()

                    # Check if next line is continuation of description (e.g. no date and no amount)
                    if i + 1 < len(lines):
                        next_line = lines[i + 1].strip()
                        if not date_pattern.match(next_line) and not amount_finder.search(next_line):
                            if not any(k in next_line.lower() for k in ["page ", "statement", "sort code", "account no", "iban", "bic", "swift"]):
                                desc = f"{desc} {next_line}".strip()
                                i += 1

                    if not desc:
                        desc = "Bank Transaction"

                    amt = clean_amount(tx_amt_raw)
                    if any(k in desc.lower() for k in ["brought forward", "carried forward", "opening balance", "closing balance", "balance from previous"]):
                        i += 1
                        continue

                    if amt is not None:
                        # Clean up description
                        desc_clean = re.sub(r"^(?:CARD PAYMENT TO|DIRECT DEBIT TO|FASTER PAYMENT TO|PAYMENT TO|DD|BACS|SO|POS|DEB|CP)\s*", "", desc, flags=re.IGNORECASE).strip()
                        if not desc_clean:
                            desc_clean = desc

                        transactions.append({
                            "date": normalized_date,
                            "description": desc_clean,
                            "amount": amt,
                            "running_bal": running_bal,
                            "full_line": line
                        })
            i += 1

        # Multi-pass reconciliation using running balance differences if available
        for idx in range(len(transactions)):
            item = transactions[idx]
            amt = item["amount"]
            cur_bal = item["running_bal"]

            # Check adjacent transaction for balance delta
            reconciled = False
            if cur_bal is not None:
                # Compare with previous transaction (chronological order)
                if idx > 0 and transactions[idx - 1]["running_bal"] is not None:
                    prev_bal = transactions[idx - 1]["running_bal"]
                    if item["date"] >= transactions[idx - 1]["date"]:
                        delta = cur_bal - prev_bal
                        if abs(abs(delta) - abs(amt)) < 0.05:
                            amt = delta
                            reconciled = True
                # Compare with next transaction (reverse-chronological order, newest first)
                elif idx + 1 < len(transactions) and transactions[idx + 1]["running_bal"] is not None:
                    next_bal = transactions[idx + 1]["running_bal"]
                    if item["date"] >= transactions[idx + 1]["date"]:
                        delta = cur_bal - next_bal
                        if abs(abs(delta) - abs(amt)) < 0.05:
                            amt = delta
                            reconciled = True

            # If not reconciled by balance difference and amount is positive, check UK banking signals
            if not reconciled and amt > 0:
                is_credit_signal = any(k in item["full_line"].lower() for k in [
                    " cr", "cr ", "credit", "money in", "paid in", "salary", "payroll", "dividend",
                    "interest paid", "refund", "inbound", "transfer from", "topup"
                ])
                if not is_credit_signal:
                    amt = -abs(amt)

            item["amount"] = round(amt, 2)

        # Remove temporary fields
        final_list = []
        for item in transactions:
            final_list.append({
                "date": item["date"],
                "description": item["description"],
                "amount": item["amount"]
            })

        return final_list, detected_balance

    def _extract_via_local_llm(self, text: str) -> List[Dict[str, Any]]:
        """
        Uses local LM Studio model to parse unconventional or noisy PDF statement layouts.
        100% on-device on Apple Silicon GPU; zero network egress.
        """
        try:
            import json

            from fiduciary.agent.llm_client import LLMClient

            client = LLMClient()
            status = client.get_status()
            if not status["local_server_online"]:
                return []

            # Take a relevant slice of the text
            sample_lines = text.splitlines()[:60]
            sample_text = "\n".join(sample_lines)

            prompt = f"""You are a bank statement parser. Extract all financial transactions from this UK bank statement text into a clean JSON array.
Respond ONLY with a valid JSON array of objects with keys: "date" (YYYY-MM-DD), "description" (string), "amount" (negative float for money out / expense, positive float for income / money in).

STATEMENT TEXT:
{sample_text}

JSON:"""

            resp = client.generate(
                prompt=prompt,
                system_prompt="You are a strict data extraction parser. Return pure JSON only.",
                temperature=0.1,
                max_tokens=1500
            )

            # Extract JSON block
            json_match = re.search(r"\[\s*\{.*\}\s*\]", resp, re.DOTALL)
            if json_match:
                parsed = json.loads(json_match.group(0))
                valid_txs = []
                for item in parsed:
                    if "description" in item and "amount" in item:
                        valid_txs.append({
                            "date": item.get("date", datetime.now().strftime("%Y-%m-%d")),
                            "description": str(item["description"]),
                            "amount": float(item["amount"])
                        })
                return valid_txs
        except Exception:
            pass
        return []
