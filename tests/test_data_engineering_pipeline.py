from fastapi.testclient import TestClient

from fiduciary.connectors.csv_importer import detect_bank_and_parse
from fiduciary.connectors.pdf_importer import PDFStatementParser
from fiduciary.observability.judge import LLMJudge
from fiduciary.storage.db import (
    get_all_transactions,
    get_statement_batches,
    init_db,
)
from fiduciary.web.app import app

client = TestClient(app)

SAMPLE_UK_CSV = """Date,Details,Paid Out,Paid In,Balance
15/09/2026,Tesco Stores Petrol,45.50,,954.50
16/09/2026,Salary Employer Acme,,3500.00,4454.50
17/09/2026,Spotify Subscription,10.99,,4443.51
18/09/2026,Costa Coffee,3.80,,4439.71
"""

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


def test_csv_importer_uk_dates_and_reconciliation():
    """Verifies that UK DD/MM/YYYY dates are normalized and accounting delta is calculated."""
    init_db()
    res = detect_bank_and_parse("natwest_september.csv", SAMPLE_UK_CSV)

    assert res["status"] == "success"
    assert res["bank_id"] == "natwest"
    assert res["transactions_imported"] == 4
    assert res["total_inflows"] == 3500.00
    assert res["total_outflows"] == 60.29  # 45.50 + 10.99 + 3.80
    assert res["calculated_delta"] == 3439.71
    assert res["batch_id"].startswith("batch_csv_")

    # Verify dates were normalized to ISO YYYY-MM-DD
    txs = res["sample_transactions"]
    dates = [t["booking_date"] for t in txs]
    assert "2026-09-15" in dates
    assert "2026-09-16" in dates
    assert "2026-09-17" in dates
    assert "2026-09-18" in dates

    # Verify categorization was applied
    tesco = next(t for t in txs if "Tesco" in t["description"])
    assert tesco["category"] in ("Groceries & Essentials", "Transport & Commute", "General Living Spend")


def test_csv_importer_idempotency():
    """Verifies that uploading the exact same CSV twice produces 0 duplicate records."""
    init_db()
    # First ingestion
    res1 = detect_bank_and_parse("revolut_statement.csv", SAMPLE_UK_CSV)
    txs_before = get_all_transactions()
    revolut_txs_1 = [t for t in txs_before if "revolut" in t["account_id"]]
    count_1 = len(revolut_txs_1)
    assert count_1 == 4

    # Second ingestion of the same file
    res2 = detect_bank_and_parse("revolut_statement.csv", SAMPLE_UK_CSV)
    txs_after = get_all_transactions()
    revolut_txs_2 = [t for t in txs_after if "revolut" in t["account_id"]]
    count_2 = len(revolut_txs_2)

    # Idempotent invariant: count must not double
    assert count_1 == count_2 == 4
    assert res1["batch_id"] == res2["batch_id"]


def test_csv_unreconciled_gap_detection():
    """Verifies that if closing balance does not equal transactions delta, discrepancy is flagged."""
    init_db()
    # A statement where transactions sum to -50, but balance changed by 1000
    corrupt_csv = """Date,Description,Amount,Balance
2026-09-01,Opening Balance,0.00,1000.00
2026-09-02,Coffee Shop,-50.00,2000.00
"""
    res = detect_bank_and_parse("chase_corrupt.csv", corrupt_csv)
    assert res["status"] == "success"
    assert res["reconciliation_status"] == "UNRECONCILED_GAP"
    assert res["discrepancy"] != 0.0


def test_statement_batch_provenance_and_api():
    """Verifies that statement batches are stored in the Bronze/Silver lineage store and queryable via API."""
    init_db()
    detect_bank_and_parse("lloyds_audit.csv", SAMPLE_UK_CSV)

    batches = get_statement_batches(limit=10)
    assert len(batches) >= 1
    latest = batches[0]
    assert "file_hash_sha256" in latest
    assert "reconciliation_status" in latest
    assert latest["file_type"] == "csv"

    # Test Web API endpoint /api/statement-batches
    api_res = client.get("/api/statement-batches")
    assert api_res.status_code == 200
    data = api_res.json()
    assert "batches" in data
    assert len(data["batches"]) >= 1


def test_pdf_importer_provenance_and_reconciliation():
    """Verifies that PDFStatementParser records cryptographic hash, reconciliation status, and batch lineage."""
    init_db()
    parser = PDFStatementParser()
    res = parser.parse_pdf("barclays_reconciled.pdf", SYNTHETIC_BARCLAYS_PDF)

    assert res["status"] == "success"
    assert res["bank_id"] == "barclays"
    assert res["transactions_imported"] == 3
    assert "batch_id" in res
    assert res["batch_id"].startswith("batch_pdf_")
    assert "reconciliation_status" in res
    assert "total_inflows" in res
    assert "total_outflows" in res
    assert res["total_inflows"] == 3500.00


def test_grounded_critic_judge_pre_audit():
    """Verifies that the LLMJudge runs deterministic fact checking before qualitative audit."""
    judge = LLMJudge()

    # Case 1: Ungrounded hallucination in response
    sys_prompt = "Total Liquid Capital: £27.26. Verified bills: none."
    hallucinated_response = "You have £27.26 in liquid cash, but you owe an urgent debt of £9,450.00 to British Gas."

    eval_result = judge.evaluate(
        user_prompt="Can I spend £50 on dinner?",
        system_prompt=sys_prompt,
        response=hallucinated_response
    )

    # Verify deterministic audit pass was attached
    assert "deterministic_audit" in eval_result
    det = eval_result["deterministic_audit"]
    assert "£9,450.00" in det["unverified_figures"] or "£9,450" in str(det["unverified_figures"])
    assert det["status"] in ("PARTIALLY_GROUNDED", "UNVERIFIED_FIGURES_DETECTED")


def test_judge_model_selection_prefers_lightweight_slms(monkeypatch):
    """Verifies that is_judge_available prioritizes small SLMs (Llama 3.2 3B, Gemma 2 2B) for Apple Silicon."""
    import requests

    class MockResponse:
        status_code = 200
        def json(self):
            return {
                "models": [
                    {"name": "qwen3.5:4b"},
                    {"name": "llama3.2:3b"},
                    {"name": "mistral:7b"}
                ]
            }

    monkeypatch.setattr(requests, "get", lambda *args, **kwargs: MockResponse())

    judge = LLMJudge()
    available, provider, model = judge.is_judge_available()
    assert available is True
    assert model == "llama3.2:3b"  # Preferred over qwen3.5:4b and mistral:7b

    # Test explicit model override
    avail_req, _, model_req = judge.is_judge_available(requested_model="qwen3.5:4b")
    assert avail_req is True
    assert model_req == "qwen3.5:4b"
