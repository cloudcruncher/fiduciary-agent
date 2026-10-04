from fastapi.testclient import TestClient

from fiduciary.agent.mcp_gateway import MCPGateway
from fiduciary.web.app import app

client = TestClient(app)


def test_mcp_list_tools():
    tools = MCPGateway.list_tools()
    assert len(tools) >= 7
    tool_names = [t["name"] for t in tools]
    assert "fetch_boe_base_rate" in tool_names
    assert "fetch_top_savings_and_isas" in tool_names
    assert "search_web_instant" in tool_names
    assert "query_spending_and_transactions" in tool_names
    assert "credit_affordability_audit" in tool_names
    assert "tax_wealth_audit" in tool_names
    assert "financial_watchdog_audit" in tool_names

    # Check schema structure conforms to standard
    for t in tools:
        assert "name" in t
        assert "description" in t
        assert "parameters" in t
        assert t["parameters"]["type"] == "object"


def test_mcp_call_tool_boe():
    res = MCPGateway.call_tool("fetch_boe_base_rate", {"timeout": 2.0})
    assert res["tool_name"] == "fetch_boe_base_rate"
    assert res["status"] == "SUCCESS"
    assert "formatted" in res["result"]
    assert res["latency_ms"] >= 0.0


def test_mcp_call_tool_savings():
    res = MCPGateway.call_tool("fetch_top_savings_and_isas")
    assert res["status"] == "SUCCESS"
    assert "cash_isas" in res["result"]
    assert "regular_savers" in res["result"]
    assert len(res["result"]["cash_isas"]) > 0


def test_mcp_call_tool_spending():
    res = MCPGateway.call_tool("query_spending_and_transactions", {"query": "groceries", "limit": 5})
    assert res["status"] == "SUCCESS"
    assert "narrative" in res["result"]
    assert "total_spent_gbp" in res["result"]


def test_mcp_call_tool_credit():
    res = MCPGateway.call_tool("credit_affordability_audit")
    assert res["status"] == "SUCCESS"
    assert "borrowing_readiness_score" in res["result"]
    assert "cash_flow_affordability" in res["result"]


def test_mcp_call_tool_not_found():
    res = MCPGateway.call_tool("non_existent_tool_123")
    assert res["status"] == "NOT_FOUND"
    assert res["error"] is not None


def test_mcp_resolve_and_ground():
    p = {"emergency_buffer_target": 8263.80, "gbp_balance": 7462.12}
    wd = {}
    tax = {}
    blocks, tools = MCPGateway.resolve_and_ground("What is the Bank of England rate?", p, wd, tax)
    assert len(tools) >= 1
    assert any(t["tool_name"] == "fetch_boe_base_rate" for t in tools)
    assert any("BANK OF ENGLAND" in b for b in blocks)


def test_mcp_api_endpoints():
    # Test GET /api/mcp/tools
    resp = client.get("/api/mcp/tools")
    assert resp.status_code == 200
    data = resp.json()
    assert "tools" in data
    assert len(data["tools"]) >= 7

    # Test POST /api/mcp/execute
    exec_resp = client.post("/api/mcp/execute", json={
        "tool_name": "fetch_top_savings_and_isas",
        "arguments": {}
    })
    assert exec_resp.status_code == 200
    exec_data = exec_resp.json()
    assert exec_data["status"] == "SUCCESS"
    assert "cash_isas" in exec_data["result"]


def test_mcp_pydantic_argument_validation():
    # Valid arguments
    res_valid = MCPGateway.call_tool("fetch_boe_base_rate", {"timeout": 3.0})
    assert res_valid["status"] == "SUCCESS"

    # Coerced string to integer
    res_coerced = MCPGateway.call_tool("query_spending_and_transactions", {"query": "coffee", "limit": "5"})
    assert res_coerced["status"] == "SUCCESS"

    # Negative timeout violates ge=0.1 constraint, returning VALIDATION_ERROR cleanly
    res_invalid = MCPGateway.call_tool("fetch_boe_base_rate", {"timeout": -10.0})
    assert res_invalid["status"] == "VALIDATION_ERROR"
    assert "error" in res_invalid["result"]
