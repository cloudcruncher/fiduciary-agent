import io

from fastapi.testclient import TestClient

from fiduciary.connectors.pdf_importer import (
    PDFStatementParser,
    clean_amount,
    detect_bank_from_text,
    parse_date_str,
)
from fiduciary.web.app import app

client = TestClient(app)

SYNTHETIC_BARCLAYS_PDF = b"""%PDF-1.4
1 0 obj << /Type /Catalog /Pages 2 0 R >> endobj
2 0 obj << /Type /Pages /Kids [3 0 R] /Count 1 >> endobj
3 0 obj << /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] /Resources << /Font << /F1 4 0 R >> >> /Contents 5 0 R >> endobj
4 0 obj << /Type /Font /Subtype /Type1 /BaseFont /Helvetica >> endobj
5 0 obj << /Length 260 >> stream
BT
/F1 12 Tf
72 700 Td
(Barclays Bank UK - Sort Code: 20-04-15 Account: 12345678) Tj
0 -20 Td
(Closing Balance: 4745.50) Tj
0 -20 Td
(15 Sep 2026 TESCO STORES 14.50 1245.50) Tj
0 -20 Td
(16 Sep 2026 SALARY EMPLOYER 3500.00 CR 4745.50) Tj
0 -20 Td
(18 Sep 2026 DIRECT DEBIT TO THAMES WATER 42.10 4703.40) Tj
ET
endstream
endobj
xref
0 6
0000000000 65535 f 
0000000009 00000 n 
0000000058 00000 n 
0000000115 00000 n 
0000000224 00000 n 
0000000293 00000 n 
trailer << /Size 6 /Root 1 0 R >>
startxref
604
%%EOF"""


def test_parse_date_str():
    assert parse_date_str("15/09/2026") == "2026-09-15"
    assert parse_date_str("01-04-2025") == "2025-04-01"
    assert parse_date_str("15/09/26") == "2026-09-15"
    assert parse_date_str("15 Sep 2026") == "2026-09-15"
    assert parse_date_str("15 September 2026") == "2026-09-15"
    assert parse_date_str("15 Sep", default_year=2026) == "2026-09-15"
    assert parse_date_str("Invalid Date") is None


def test_clean_amount():
    assert clean_amount("123.45") == 123.45
    assert clean_amount("£1,234.50") == 1234.50
    assert clean_amount("-45.00") == -45.00
    assert clean_amount("500.00 CR") == 500.00
    assert clean_amount("35.50 DR") == -35.50
    assert clean_amount("invalid") is None


def test_detect_bank():
    bid, name = detect_bank_from_text("my_file.pdf", "Welcome to HSBC UK Bank Statement")
    assert bid == "hsbc"
    assert name == "HSBC UK"

    bid2, name2 = detect_bank_from_text("natwest_statement.pdf", "Account overview")
    assert bid2 == "natwest"

    bid3, name3 = detect_bank_from_text("unknown.pdf", "Generic personal ledger")
    assert bid3 == "imported_pdf_bank"


def test_pdf_parser_direct():
    parser = PDFStatementParser()
    res = parser.parse_pdf("barclays_september.pdf", SYNTHETIC_BARCLAYS_PDF)
    assert res["status"] == "success"
    assert res["bank_id"] == "barclays"
    assert res["transactions_imported"] == 3
    assert res["detected_balance"] == 4745.50

    descriptions = [t["description"] for t in res["sample_transactions"]]
    assert "TESCO STORES" in descriptions
    assert "SALARY EMPLOYER" in descriptions
    assert "THAMES WATER" in descriptions

    # Outflow check
    tesco_tx = next(t for t in res["sample_transactions"] if "TESCO" in t["description"])
    assert tesco_tx["amount"] < 0
    assert tesco_tx["category"] == "Groceries & Essentials"

    # Inflow check
    salary_tx = next(t for t in res["sample_transactions"] if "SALARY" in t["description"])
    assert salary_tx["amount"] > 0
    assert salary_tx["category"] == "Income & Top-ups"


def test_pdf_upload_api():
    # Test valid PDF upload
    files = {"file": ("barclays_2026.pdf", io.BytesIO(SYNTHETIC_BARCLAYS_PDF), "application/pdf")}
    res = client.post("/api/upload", files=files)
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "success"
    assert data["bank_id"] == "barclays"
    assert data["transactions_imported"] >= 1

    # Test invalid empty PDF upload
    files_empty = {"file": ("empty.pdf", io.BytesIO(b""), "application/pdf")}
    res_empty = client.post("/api/upload", files=files_empty)
    assert res_empty.status_code == 400


def test_single_amount_lines_and_desc_scoping():
    """Verifies lines with only one amount (no running balance) parse without scoping error."""
    parser = PDFStatementParser()
    text = """
    Revolut UK Statement
    15 Sep 2026 TESCO STORES -14.50
    16 Sep 2026 SALARY EMPLOYER 3500.00 CR
    17 Sep 2026 Spotify UK 11.99
    18 Sep 2026 Carried Forward Balance 3500.00
    """
    txs, bal = parser._extract_transactions_regex(text, 2026)
    assert len(txs) == 3
    # Balance row skipped
    assert not any("Carried Forward" in t["description"] for t in txs)
    # Debits signed negative
    assert next(t for t in txs if "TESCO" in t["description"])["amount"] == -14.50
    assert next(t for t in txs if "Spotify" in t["description"])["amount"] == -11.99
    # Credit signed positive
    assert next(t for t in txs if "SALARY" in t["description"])["amount"] == 3500.00


def test_iso_and_hyphenated_date_formats():
    """Verifies ISO 8601 (YYYY-MM-DD) and hyphenated UK dates (15-Sep-2026, 15-09-2026) parse cleanly."""
    parser = PDFStatementParser()
    text = """
    Monzo Bank Statement
    2026-09-15 Sainsbury's Supermarkets -24.50
    16-Sep-2026 Costa Coffee -3.85
    17-09-2026 TFL Travel -2.80
    """
    txs, _ = parser._extract_transactions_regex(text, 2026)
    assert len(txs) == 3
    dates = [t["date"] for t in txs]
    assert dates == ["2026-09-15", "2026-09-16", "2026-09-17"]


def test_split_line_amount_and_continuation():
    """Verifies statements where amount is on the next line or description wraps across lines."""
    parser = PDFStatementParser()
    text = """
    NatWest Statement
    15 Sep 2026 AMAZON EU SARL UK
    -49.99
    16 Sep 2026 DIRECT DEBIT TO
    BRITISH GAS TRADING LTD -75.00
    """
    txs, _ = parser._extract_transactions_regex(text, 2026)
    assert len(txs) >= 1
    amazon_tx = next(t for t in txs if "AMAZON" in t["description"])
    assert amazon_tx["amount"] == -49.99


SYNTHETIC_REVOLUT_PDF = b"""%PDF-1.4
1 0 obj << /Type /Catalog /Pages 2 0 R >> endobj
2 0 obj << /Type /Pages /Kids [3 0 R] /Count 1 >> endobj
3 0 obj << /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] /Resources << /Font << /F1 4 0 R >> >> /Contents 5 0 R >> endobj
4 0 obj << /Type /Font /Subtype /Type1 /BaseFont /Helvetica >> endobj
5 0 obj << /Length 230 >> stream
BT
/F1 12 Tf
72 700 Td
(Revolut UK Statement - Sort Code: 04-00-75 Account: 87654321) Tj
0 -20 Td
(2026-09-15 TESCO STORES -14.50) Tj
0 -20 Td
(2026-09-16 SALARY EMPLOYER 3500.00 CR) Tj
0 -20 Td
(2026-09-17 Spotify UK -11.99) Tj
ET
endstream
endobj
xref
0 6
0000000000 65535 f 
0000000009 00000 n 
0000000058 00000 n 
0000000115 00000 n 
0000000224 00000 n 
0000000293 00000 n 
trailer << /Size 6 /Root 1 0 R >>
startxref
574
%%EOF"""


def test_pdf_upload_api_single_amounts():
    """End-to-end test uploading a PDF where lines only have single amounts (no running balance column)."""
    files = {"file": ("revolut_statement.pdf", io.BytesIO(SYNTHETIC_REVOLUT_PDF), "application/pdf")}
    res = client.post("/api/upload", files=files)
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "success"
    assert data["bank_id"] == "revolut"
    assert data["transactions_imported"] == 3


