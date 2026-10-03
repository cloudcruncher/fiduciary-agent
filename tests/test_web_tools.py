from unittest.mock import MagicMock, patch

from fiduciary.agent.web_tools import (
    fetch_boe_base_rate,
    fetch_top_savings_and_isas,
    get_live_web_context,
)


def test_fetch_boe_base_rate_mock():
    with patch("urllib.request.urlopen") as mock_urlopen:
        mock_resp = MagicMock()
        mock_resp.read.return_value = b"<html>Bank Rate held at 4.25% by the committee</html>"
        mock_resp.__enter__.return_value = mock_resp
        mock_urlopen.return_value = mock_resp

        # Clear cache for test
        from fiduciary.agent import web_tools
        web_tools._BOE_CACHE["timestamp"] = 0

        res = fetch_boe_base_rate()
        assert res["bank_rate_pct"] == 4.25
        assert res["formatted"] == "4.25%"
        assert "Bank of England" in res["source"]

def test_fetch_top_savings_and_isas():
    data = fetch_top_savings_and_isas()
    assert len(data["cash_isas"]) >= 1
    assert data["cash_isas"][0]["aer"] > 4.0
    assert len(data["regular_savers"]) >= 1
    assert len(data["bank_switches"]) >= 1

def test_get_live_web_context_boe():
    context = get_live_web_context("What is the Bank of England base rate right now?")
    assert "LIVE BANK OF ENGLAND BASE RATE" in context

def test_get_live_web_context_isa():
    context = get_live_web_context("What is the top Cash ISA rate?")
    assert "LIVE UK MARKET BENCHMARKS" in context
    assert "Cash ISA" in context

def test_get_live_web_context_empty_for_tx():
    context = get_live_web_context("What are my last 3 transactions?")
    assert context == ""

def test_tool_catalog_and_observability():
    from fiduciary.agent.web_tools import get_available_tools_catalog, get_live_web_context_with_tools
    catalog = get_available_tools_catalog()
    assert len(catalog) >= 3
    tool_names = [t["tool_name"] for t in catalog]
    assert "fetch_top_savings_and_isas" in tool_names
    assert "fetch_boe_base_rate" in tool_names

    ctx, tools = get_live_web_context_with_tools("Tell me the top cash isa rate and first direct saver")
    assert "LIVE UK MARKET BENCHMARKS" in ctx
    assert len(tools) == 1
    assert tools[0]["tool_name"] == "fetch_top_savings_and_isas"
    assert tools[0]["status"] == "SUCCESS"
    assert "First Direct" in tools[0]["summary"]

