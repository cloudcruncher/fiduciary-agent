import pytest
from fastapi.testclient import TestClient

from fiduciary.enrichment.engine import EnrichmentEngine
from fiduciary.enrichment.models import TransactionInput
from fiduciary.storage.db import init_db
from fiduciary.web.app import app


@pytest.fixture(scope="module")
def client():
    return TestClient(app)


@pytest.fixture
def engine():
    return EnrichmentEngine()


def test_narrative_cleaning(engine):
    cases = [
        ("SUMUP *THE BLUE ANCHOR", "the_blue_anchor", "THE BLUE ANCHOR"),
        ("SWITCH2 ENERGY LTD7F56CFA33 TPP MONEYHUB FINANFP 01/10/26", "switch2_energy_lt", "SWITCH2 ENERGY LT"),
        ("SQUARE *COFFEE ROASTERS VIA MOBILE", "coffee_roasters", "COFFEE ROASTERS"),
        ("DIRECT DEBIT THAMES WATER", "thames_water", "THAMES WATER"),
        ("CRV*NETFLIX.COM", "netflix_com", "NETFLIX COM"),
    ]
    for raw, expected_slug_contains, expected_name in cases:
        slug, clean_name = engine.clean_narrative(raw)
        assert expected_slug_contains in slug, f"Expected {expected_slug_contains} in {slug}"
        assert len(clean_name) > 0


def test_knowledge_base_enrichment(engine):
    tx = TransactionInput(
        raw_narrative="SWITCH2 ENERGY LTD7F56CFA33 TPP MONEYHUB FINANFP 01/10/26",
        amount=-42.35,
        currency="GBP"
    )
    res = engine.enrich_single(tx)
    assert res.clean_merchant.name == "Switch2 Energy"
    assert res.clean_merchant.domain == "switch2.co.uk"
    assert res.enrichment.category_l1 == "Utilities & Housing"
    assert res.enrichment.category_l2 == "Energy & Heating"
    assert res.enrichment.category_l3 == "District Community Heating"
    assert res.enrichment.is_contractual_commitment is True
    assert res.fiduciary_insights.is_essential_living_cost is True
    assert res.fiduciary_insights.cadence == "monthly"
    assert res.source == "deterministic_rule"


def test_amount_aware_apple_disambiguation(engine):
    # Micro/subscription amount -> Apple Services / iCloud
    sub_tx = TransactionInput(raw_narrative="APPLE.COM/BILL", amount=-2.99)
    sub_res = engine.enrich_single(sub_tx)
    assert sub_res.clean_merchant.name == "Apple Services"
    assert sub_res.enrichment.category_l1 == "Subscriptions & Software"
    assert sub_res.fiduciary_insights.cadence == "monthly"

    # High-ticket amount -> Apple Store / Hardware
    hw_tx = TransactionInput(raw_narrative="APPLE.COM/BILL", amount=-1299.00)
    hw_res = engine.enrich_single(hw_tx)
    assert hw_res.clean_merchant.name == "Apple Store"
    assert hw_res.enrichment.category_l1 == "Shopping & Lifestyle"
    assert hw_res.fiduciary_insights.cadence == "discretionary_one_off"


def test_amount_aware_tfl_disambiguation(engine):
    # Routine transit fare
    fare_tx = TransactionInput(raw_narrative="TfL Travel Charge", amount=-3.40)
    fare_res = engine.enrich_single(fare_tx)
    assert fare_res.enrichment.category_l2 == "Public Transit"
    assert fare_res.fiduciary_insights.hmrc_tax_deductible is True

    # Penalty fare
    penalty_tx = TransactionInput(raw_narrative="TfL Travel Charge", amount=-80.00)
    penalty_res = engine.enrich_single(penalty_tx)
    assert penalty_res.enrichment.category_l2 == "Fines & Penalties"
    assert penalty_res.fiduciary_insights.hmrc_tax_deductible is False
    assert "Penalty" in penalty_res.fiduciary_insights.action_insight or "penalty" in penalty_res.fiduciary_insights.action_insight


def test_batch_enrichment(engine):
    batch = [
        TransactionInput(raw_narrative="Welcome Brentford", amount=-31.46),
        TransactionInput(raw_narrative="Anthropic* Claude Sub", amount=-18.00),
        TransactionInput(raw_narrative="L.B.HOUNSLOW COUNCIL TAX", amount=-162.00),
    ]
    res = engine.enrich_batch(batch)
    assert res.total_transactions == 3
    assert len(res.enriched_transactions) == 3
    assert res.processing_time_ms >= 0.0

    merchants = [t.clean_merchant.name for t in res.enriched_transactions]
    assert "Welcome (Brentford)" in merchants
    assert "Anthropic PBC" in merchants
    assert "London Borough of Hounslow" in merchants


def test_api_endpoints(client):
    init_db()

    # 1. Single transaction endpoint
    resp = client.post("/api/v1/enrich/transaction", json={
        "raw_narrative": "Welcome Brentford",
        "amount": -31.46,
        "currency": "GBP"
    })
    assert resp.status_code == 200
    data = resp.json()
    assert data["clean_merchant"]["name"] == "Welcome (Brentford)"
    assert data["enrichment"]["category_l1"] == "Groceries & Essentials"

    # 2. Batch endpoint
    batch_resp = client.post("/api/v1/enrich/batch", json={
        "transactions": [
            {"raw_narrative": "SWITCH2 ENERGY LTD", "amount": -42.35},
            {"raw_narrative": "Direct Debit THAMES WATER", "amount": -48.00}
        ]
    })
    assert batch_resp.status_code == 200
    batch_data = batch_resp.json()
    assert batch_data["total_transactions"] == 2

    # 3. Cache stats endpoint
    stats_resp = client.get("/api/v1/enrich/cache/stats")
    assert stats_resp.status_code == 200
    stats = stats_resp.json()
    assert "total_cached_merchants" in stats
    assert "total_cache_hits" in stats
