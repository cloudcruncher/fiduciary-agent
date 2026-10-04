import hashlib
import io
import re
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple

import pypdf

from fiduciary.storage.db import (
    classify_transaction,
    generate_tx_fingerprint,
    insert_transactions,
    record_statement_batch,
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


def extract_pdf_data(pdf_bytes: bytes) -> Tuple[str, List[List[List[Optional[str]]]]]:
    """
    Extracts layout-aware text and structured grid tables using pdfplumber,
    falling back seamlessly to pypdf.
    """
    full_text_pages = []
    all_tables: List[List[List[Optional[str]]]] = []

    try:
        import pdfplumber
        with pdfplumber.open(io.BytesIO(pdf_bytes)) as pdf:
            for page in pdf.pages:
                txt = page.extract_text(layout=True)
                if txt and txt.strip():
                    full_text_pages.append(txt)
                tables = page.extract_tables()
                if tables:
                    for tbl in tables:
                        if tbl and len(tbl) > 1:
                            all_tables.append(tbl)
    except Exception:
        pass

    if not full_text_pages:
        try:
            reader = pypdf.PdfReader(io.BytesIO(pdf_bytes))
            for page in reader.pages:
                txt = page.extract_text()
                if txt and txt.strip():
                    full_text_pages.append(txt)
        except Exception:
            pass

    return "\n".join(full_text_pages), all_tables


def extract_text_from_pdf(pdf_bytes: bytes) -> str:
    """Extracts raw text from PDF bytes."""
    text, _ = extract_pdf_data(pdf_bytes)
    return text


def detect_bank_from_text(filename: str, full_text: str) -> Tuple[str, str]:
    """Identifies the issuing UK financial institution."""
    combined = (filename + " " + full_text[:2000]).lower()
    for bank_id, bank_name in UK_BANKS:
        if bank_id in combined:
            return bank_id, bank_name
    return "imported_pdf_bank", "Imported Bank (PDF)"


def parse_date_str(raw: str, default_year: int = 2026) -> Optional[str]:
    """Normalizes varied date formats into YYYY-MM-DD."""
    if not raw:
        return None
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


def clean_amount(val_str: Optional[str]) -> Optional[float]:
    """Cleans currency strings like '£1,234.50', '24.50 CR', '-12.00' into a float."""
    if not val_str:
        return None
    v = str(val_str).replace("£", "").replace(",", "").replace("$", "").replace("€", "").strip()
    if not v:
        return None

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
    Combines spatial tabular extraction, layout-aware regex, cryptographic lineage,
    and double-entry accounting balance reconciliation.
    """

    def __init__(self):
        pass

    def parse_pdf(self, filename: str, pdf_bytes: bytes) -> Dict[str, Any]:
        # Bronze layer: Compute cryptographic SHA-256 provenance hash
        content_hash = hashlib.sha256(pdf_bytes).hexdigest()
        batch_id = f"batch_pdf_{content_hash[:12]}"

        raw_text, tables = extract_pdf_data(pdf_bytes)
        if not raw_text.strip() and not tables:
            raise ValueError("Could not extract any readable text or tables from this PDF. It may be a scanned image or protected.")

        bank_id, bank_name = detect_bank_from_text(filename, raw_text)
        account_id = f"acc_{bank_id}_imported"

        # PII Shielding: auto-mask sort code & account number
        sort_code_match = re.search(r"\b(\d{2}-\d{2}-\d{2})\b", raw_text)
        account_num_match = re.search(r"\b(\d{8})\b", raw_text)
        raw_sort = sort_code_match.group(1) if sort_code_match else "00-00-00"
        raw_acc = account_num_match.group(1) if account_num_match else "00000000"
        sort_code = f"••-••-{raw_sort[-2:]}"
        account_num = f"••••{raw_acc[-4:]}"

        # Determine statement year
        year_match = re.search(r"\b(202[3-7])\b", raw_text)
        statement_year = int(year_match.group(1)) if year_match else datetime.now().year

        # 1. Detect opening and closing balances from summary metadata and text
        detected_open = self._detect_opening_balance(raw_text, tables)
        detected_close = self._detect_closing_balance(raw_text, tables)

        # 2. Try spatial grid table extraction first if structured tables exist
        table_txs, table_open, table_close = self._extract_transactions_tables(tables, statement_year)

        # 3. Try layout-aware regex extraction with opening balance context
        init_open = detected_open or table_open
        regex_txs, regex_close = self._extract_transactions_regex(raw_text, statement_year, opening_balance=init_open)

        # Determine balance figures
        opening_balance = detected_open or table_open or (
            regex_txs[0].get("running_bal") - regex_txs[0].get("amount")
            if regex_txs and regex_txs[0].get("running_bal") is not None and regex_txs[0].get("amount") is not None
            else None
        )
        closing_balance = detected_close or regex_close or table_close

        # Candidate selection using closed-loop invariant validation:
        # Opening + Inflows - Outflows == Closing
        if opening_balance is not None and closing_balance is not None:
            expected_delta = round(closing_balance - opening_balance, 2)
            regex_delta = round(sum(t["amount"] for t in regex_txs), 2) if regex_txs else None
            table_delta = round(sum(t["amount"] for t in table_txs), 2) if table_txs else None

            regex_matches = regex_delta is not None and abs(regex_delta - expected_delta) < 0.05
            table_matches = table_delta is not None and abs(table_delta - expected_delta) < 0.05

            if regex_matches and not table_matches:
                transactions = regex_txs
            elif table_matches and not regex_matches:
                transactions = table_txs
            elif regex_matches and table_matches:
                transactions = regex_txs if len(regex_txs) >= len(table_txs) else table_txs
            else:
                transactions = regex_txs if len(regex_txs) >= len(table_txs) else table_txs
        else:
            if len(regex_txs) >= len(table_txs):
                transactions = regex_txs
            else:
                transactions = table_txs

        # 3. If very few records extracted from a long document, attempt local LLM extraction
        if len(transactions) < 2 and len(raw_text.splitlines()) > 15:
            llm_txs = self._extract_via_local_llm(raw_text)
            if len(llm_txs) > len(transactions):
                transactions = llm_txs

        # 4. Closed-Loop Accounting Balance Invariant Verification:
        # Opening Balance + Inflows - Outflows == Closing Balance
        total_inflows = round(sum(t["amount"] for t in transactions if t["amount"] > 0), 2)
        total_outflows = round(sum(abs(t["amount"]) for t in transactions if t["amount"] < 0), 2)
        calculated_delta = round(total_inflows - total_outflows, 2)

        discrepancy = 0.0
        reconciliation_status = "UNVERIFIED_NO_BALANCES"

        if opening_balance is not None and closing_balance is not None:
            expected_delta = round(closing_balance - opening_balance, 2)
            discrepancy = round(calculated_delta - expected_delta, 2)
            if abs(discrepancy) < 0.02:
                reconciliation_status = "RECONCILED"
                discrepancy = 0.0
            else:
                reconciliation_status = "UNRECONCILED_GAP"
            detected_balance = closing_balance
        elif closing_balance is not None:
            reconciliation_status = "CLOSING_BALANCE_VERIFIED"
            detected_balance = closing_balance
            opening_balance = round(closing_balance - calculated_delta, 2)
        elif opening_balance is not None:
            reconciliation_status = "OPENING_BALANCE_VERIFIED"
            detected_balance = round(opening_balance + calculated_delta, 2)
            closing_balance = detected_balance
        else:
            reconciliation_status = "CASHFLOW_ESTIMATED"
            detected_balance = max(0.0, calculated_delta)

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

        # Categorize transactions and generate deterministic idempotent SHA-256 fingerprints
        final_txs = []
        for t in transactions:
            desc = t.get("description", "Transaction")
            amt = round(float(t.get("amount", 0.0)), 2)
            date_val = t.get("date", datetime.now().strftime("%Y-%m-%d"))
            category = classify_transaction(desc[:40], desc, "General", amt)
            fingerprint = generate_tx_fingerprint(account_id, date_val, amt, desc)

            final_txs.append({
                "transaction_id": fingerprint,
                "amount": amt,
                "currency": "GBP",
                "description": desc,
                "booking_date": date_val,
                "category": category,
                "counterparty_name": desc[:60],
                "raw_description": t.get("full_line") or desc,
                "statement_batch_id": batch_id
            })

        if final_txs:
            insert_transactions(account_id, final_txs, batch_id=batch_id)

        # Record Provenance & Batch Lineage in Bronze/Silver store
        record_statement_batch({
            "id": batch_id,
            "filename": filename,
            "file_hash_sha256": content_hash,
            "file_type": "pdf",
            "bank_id": bank_id,
            "account_id": account_id,
            "opening_balance": opening_balance,
            "closing_balance": detected_balance,
            "total_inflows": total_inflows,
            "total_outflows": total_outflows,
            "calculated_delta": calculated_delta,
            "discrepancy": discrepancy,
            "reconciliation_status": reconciliation_status,
            "transactions_count": len(final_txs)
        })

        return {
            "status": "success",
            "batch_id": batch_id,
            "bank_id": bank_id,
            "bank_name": bank_name,
            "account_id": account_id,
            "transactions_imported": len(final_txs),
            "detected_balance": detected_balance,
            "opening_balance": opening_balance,
            "closing_balance": detected_balance,
            "total_inflows": total_inflows,
            "total_outflows": total_outflows,
            "calculated_delta": calculated_delta,
            "discrepancy": discrepancy,
            "reconciliation_status": reconciliation_status,
            "sample_transactions": final_txs[:5]
        }

    def _extract_transactions_tables(
        self,
        tables: List[List[List[Optional[str]]]],
        default_year: int
    ) -> Tuple[List[Dict[str, Any]], Optional[float], Optional[float]]:
        """Parses structured vector table grids extracted by pdfplumber."""
        transactions = []
        opening_bal = None
        closing_bal = None

        for tbl in tables:
            if not tbl or len(tbl) < 2:
                continue

            header_idx = -1
            date_col = -1
            desc_col = -1
            paid_out_col = -1
            paid_in_col = -1
            amount_col = -1
            balance_col = -1

            # Identify header row
            for r_idx, row in enumerate(tbl[:5]):
                row_str = " ".join(str(c or "").lower() for c in row)
                if any(k in row_str for k in ["date", "description", "details", "narrative", "amount", "paid out", "money out", "balance"]):
                    header_idx = r_idx
                    for c_idx, cell in enumerate(row):
                        cell_clean = str(cell or "").lower()
                        if "date" in cell_clean:
                            date_col = c_idx
                        elif any(k in cell_clean for k in ["description", "narrative", "details", "merchant", "reference"]):
                            desc_col = c_idx
                        elif any(k in cell_clean for k in ["paid out", "money out", "debit", "withdrawal"]):
                            paid_out_col = c_idx
                        elif any(k in cell_clean for k in ["paid in", "money in", "credit", "deposit"]):
                            paid_in_col = c_idx
                        elif "balance" in cell_clean:
                            balance_col = c_idx
                        elif any(k in cell_clean for k in ["amount", "value"]):
                            amount_col = c_idx
                    break

            if header_idx == -1 or date_col == -1:
                continue

            # Process data rows
            for row in tbl[header_idx + 1:]:
                if len(row) <= max(date_col, desc_col):
                    continue

                raw_date = str(row[date_col] or "").strip()
                parsed_date = parse_date_str(raw_date, default_year=default_year)
                if not parsed_date:
                    continue

                desc_text = str(row[desc_col] or "").strip().replace("\n", " ") if desc_col != -1 and len(row) > desc_col else "Transaction"
                amt = 0.0

                # Spatial Column Extraction: Paid Out vs Paid In
                if paid_out_col != -1 and paid_in_col != -1:
                    po_val = clean_amount(row[paid_out_col]) if len(row) > paid_out_col else None
                    pi_val = clean_amount(row[paid_in_col]) if len(row) > paid_in_col else None
                    if po_val is not None and po_val != 0.0:
                        amt = -abs(po_val)
                    elif pi_val is not None and pi_val != 0.0:
                        amt = abs(pi_val)
                elif amount_col != -1 and len(row) > amount_col:
                    clean_amt = clean_amount(row[amount_col])
                    if clean_amt is not None:
                        amt = clean_amt

                bal_val = clean_amount(row[balance_col]) if balance_col != -1 and len(row) > balance_col else None
                if bal_val is not None:
                    if opening_bal is None:
                        opening_bal = bal_val
                    closing_bal = bal_val

                if amt != 0.0:
                    transactions.append({
                        "date": parsed_date,
                        "description": desc_text,
                        "amount": amt,
                        "running_bal": bal_val,
                        "full_line": " | ".join(str(c or "") for c in row)
                    })

        return transactions, opening_bal, closing_bal

    def _detect_opening_balance(self, text: str, tables: Optional[List[Any]] = None) -> Optional[float]:
        """Detects opening or brought-forward balance from statement tables and text."""
        if tables:
            for tbl in tables:
                for row in tbl:
                    if not row or len(row) < 2:
                        continue
                    label = str(row[0] or "").lower()
                    if any(k in label for k in ["previous balance", "opening balance", "starting balance", "brought forward"]):
                        val = clean_amount(row[1])
                        if val is not None:
                            return val

        for ln in text.splitlines():
            m_open = re.search(r"(?:previous|opening|starting|carried\s+forward|brought\s+forward)\s+balance[:\s]+£?([0-9,]+\.[0-9]{2})", ln, re.IGNORECASE)
            if m_open:
                cleaned = clean_amount(m_open.group(1))
                if cleaned is not None:
                    return cleaned
            m_bf = re.search(r"(?:^|\s)brought\s+forward\s+£?([0-9,]+\.[0-9]{2})", ln, re.IGNORECASE)
            if m_bf:
                cleaned = clean_amount(m_bf.group(1))
                if cleaned is not None:
                    return cleaned
        return None

    def _detect_closing_balance(self, text: str, tables: Optional[List[Any]] = None) -> Optional[float]:
        """Detects closing or ending balance from statement tables and text."""
        if tables:
            for tbl in tables:
                for row in tbl:
                    if not row or len(row) < 2:
                        continue
                    label = str(row[0] or "").lower()
                    if any(k in label for k in ["new balance", "closing balance", "ending balance"]):
                        val = clean_amount(row[1])
                        if val is not None:
                            return val

        for ln in text.splitlines():
            m_new = re.search(r"(?:new|closing|ending)\s+balance[:\s]+£?([0-9,]+\.[0-9]{2})", ln, re.IGNORECASE)
            if m_new:
                cleaned = clean_amount(m_new.group(1))
                if cleaned is not None:
                    return cleaned
        return None

    def _extract_transactions_regex(
        self,
        text: str,
        default_year: int,
        opening_balance: Optional[float] = None
    ) -> Tuple[List[Dict[str, Any]], Optional[float]]:
        """Parses standard multi-column and single-column UK bank statements via layout-aware text regex."""
        lines = [ln.strip() for ln in text.splitlines() if ln.strip()]
        transactions = []
        closing_balance = None

        # Pre-detect closing balance if present in text
        for ln in lines:
            m_bal = re.search(r"(?:closing|ending|new|carried forward)\s+balance[:\s]+£?([0-9,]+\.[0-9]{2})", ln, re.IGNORECASE)
            if m_bal:
                cleaned = clean_amount(m_bal.group(1))
                if cleaned is not None and closing_balance is None:
                    closing_balance = cleaned

        date_pattern = re.compile(
            r"^(\d{4}[/.-]\d{1,2}[/.-]\d{1,2}|\d{1,2}[/.-]\d{1,2}[/.-](?:\d{4}|\d{2})|\d{1,2}[\s-]+[A-Za-z]{3,9}(?:[\s-]+(?:\d{4}|\d{2}))?)\s+(.*)$"
        )
        amount_finder = re.compile(r"[-+]?£?[0-9,]+\.[0-9]{2}(?:\s*(?:CR|DR))?(?!%)")

        current_date = f"{default_year}-01-01"
        running_bal = opening_balance
        pending_lines: List[str] = []
        in_tx_section = False
        has_seen_first_date = False

        has_section_headers = any(k in ln.lower() for ln in lines for k in ["date   description", "date details", "date narrative"])

        for ln in lines:
            # Stop at legal footers / overdraft tables
            if any(k in ln.lower() for k in [
                "interest (variable)", "when you stay within", "amount account overdrawn",
                "overdraft arrangements", "below are the most common", "ways to bank with",
                "important information about compensation"
            ]):
                break

            # Check for brought forward line with date
            if "brought forward" in ln.lower():
                in_tx_section = True
                pending_lines = []
                m_bf_date = date_pattern.match(ln)
                if m_bf_date:
                    parsed = parse_date_str(m_bf_date.group(1), default_year=default_year)
                    if parsed:
                        current_date = parsed
                        has_seen_first_date = True
                continue

            if any(k in ln.lower() for k in ["date   description", "date details", "date narrative"]):
                in_tx_section = True
                pending_lines = []
                continue

            if has_section_headers and not in_tx_section:
                continue

            # Skip headers / boilerplate
            if any(k in ln.lower() for k in [
                "welcome to your", "reward account", "account name",
                "statement date", "period covered", "previous balance", "paid in £",
                "withdrawn £", "new balance £", "bic nwb", "iban gb", "statement abbreviations",
                "lost or s tolen", "national westminster bank", "retstmt -", "sort code page no",
                "page no", "account no sort", "carried forward balance"
            ]):
                continue

            m_date = date_pattern.match(ln)
            if m_date:
                parsed = parse_date_str(m_date.group(1), default_year=default_year)
                if parsed:
                    current_date = parsed
                    has_seen_first_date = True
                rest = m_date.group(2)
            else:
                if not has_seen_first_date:
                    continue
                rest = ln

            amts = amount_finder.findall(rest)
            if len(amts) >= 2:
                tx_amt_raw = amts[-2]
                bal_raw = amts[-1]
                tx_amt_val = clean_amount(tx_amt_raw)
                new_bal = clean_amount(bal_raw)

                idx = rest.rfind(tx_amt_raw)
                line_desc = rest[:idx].strip() if idx != -1 else rest.strip()
                full_desc = " ".join(pending_lines + ([line_desc] if line_desc else [])).strip()
                pending_lines = []

                delta = round(new_bal - running_bal, 2) if (running_bal is not None and new_bal is not None) else None
                if delta is not None and tx_amt_val is not None and abs(abs(delta) - abs(tx_amt_val)) < 0.05:
                    signed_amt = delta
                else:
                    is_credit_signal = any(k in (line_desc.lower() + " " + tx_amt_raw.lower()) for k in [
                        "cr", "credit", "money in", "paid in", "salary", "refund", "topup"
                    ])
                    amt_val = abs(tx_amt_val) if tx_amt_val is not None else 0.0
                    signed_amt = amt_val if is_credit_signal else -amt_val

                desc_clean = re.sub(r"^(?:CARD PAYMENT TO|DIRECT DEBIT TO|FASTER PAYMENT TO|PAYMENT TO|DD|BACS|SO|POS|DEB|CP)\s*", "", full_desc, flags=re.IGNORECASE).strip()
                if not desc_clean:
                    desc_clean = full_desc or "Bank Transaction"

                transactions.append({
                    "date": current_date,
                    "description": desc_clean,
                    "amount": signed_amt,
                    "running_bal": new_bal,
                    "full_line": ln
                })
                if new_bal is not None:
                    running_bal = new_bal
                    closing_balance = new_bal
            elif len(amts) == 1:
                tx_amt_raw = amts[0]
                amt_val = clean_amount(tx_amt_raw)
                if (m_date or pending_lines) and amt_val is not None:
                    idx = rest.rfind(tx_amt_raw)
                    line_desc = rest[:idx].strip() if idx != -1 else rest.strip()
                    full_desc = " ".join(pending_lines + ([line_desc] if line_desc else [])).strip()
                    pending_lines = []

                    if any(k in full_desc.lower() for k in ["brought forward", "carried forward", "opening balance", "closing balance", "balance from previous"]):
                        continue

                    if "cr" in tx_amt_raw.lower() or any(k in full_desc.lower() for k in ["cr", "credit", "salary", "refund"]):
                        signed_amt = abs(amt_val)
                    elif amt_val < 0:
                        signed_amt = amt_val
                    else:
                        signed_amt = -abs(amt_val)

                    desc_clean = re.sub(r"^(?:CARD PAYMENT TO|DIRECT DEBIT TO|FASTER PAYMENT TO|PAYMENT TO|DD|BACS|SO|POS|DEB|CP)\s*", "", full_desc, flags=re.IGNORECASE).strip()
                    if not desc_clean:
                        desc_clean = full_desc or "Bank Transaction"

                    transactions.append({
                        "date": current_date,
                        "description": desc_clean,
                        "amount": signed_amt,
                        "running_bal": None,
                        "full_line": ln
                    })
                else:
                    pending_lines.append(rest)
            else:
                pending_lines.append(rest)

        # Multi-pass reconciliation using running balance differences if available
        for idx in range(len(transactions)):
            item = transactions[idx]
            amt = item["amount"]
            cur_bal = item["running_bal"]

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
                # Compare with next transaction (reverse-chronological order)
                elif idx + 1 < len(transactions) and transactions[idx + 1]["running_bal"] is not None:
                    next_bal = transactions[idx + 1]["running_bal"]
                    if item["date"] >= transactions[idx + 1]["date"]:
                        delta = cur_bal - next_bal
                        if abs(abs(delta) - abs(amt)) < 0.05:
                            amt = delta
                            reconciled = True

            # If not reconciled by balance difference and amount is positive, check UK banking signals
            if not reconciled and amt > 0:
                is_credit_signal = any(k in (item.get("full_line", "").lower() + " " + item.get("description", "").lower()) for k in [
                    " cr", "cr ", "credit", "money in", "paid in", "salary", "payroll", "dividend",
                    "interest paid", "refund", "inbound", "transfer from", "topup"
                ])
                if not is_credit_signal:
                    amt = -abs(amt)

            item["amount"] = round(amt, 2)

        final_list = []
        for item in transactions:
            final_list.append({
                "date": item["date"],
                "description": item["description"],
                "amount": item["amount"],
                "running_bal": item.get("running_bal"),
                "full_line": item.get("full_line")
            })

        return final_list, closing_balance

    def _extract_via_local_llm(self, text: str) -> List[Dict[str, Any]]:
        """
        Uses local model to parse unconventional or noisy PDF statement layouts.
        100% on-device on Apple Silicon GPU; zero network egress.
        """
        try:
            import json

            from fiduciary.agent.llm_client import LLMClient

            client = LLMClient()
            status = client.get_status()
            if not status["local_server_online"]:
                return []

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
