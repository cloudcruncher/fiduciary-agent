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
