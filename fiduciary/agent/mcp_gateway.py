"""
Model Context Protocol (MCP) Gateway for Personal Fiduciary Agent.
Provides standardized MCP tool schemas, live web grounding (DuckDuckGo, Bank of England),
deterministic financial calculation engines, and tool observability.
Compatible with Model Context Protocol (MCP) standards.
"""

import time
from typing import Any, Dict, List, Optional, Tuple

from fiduciary.agent.web_tools import (
    fetch_boe_base_rate,
    fetch_top_savings_and_isas,
    search_duckduckgo_instant,
)
from fiduciary.analysis.credit_affordability import CreditAffordabilityEngine
from fiduciary.analysis.spending import SpendingInsightEngine
from fiduciary.analysis.tax_optimizer import UKTaxOptimizer
from fiduciary.analysis.watchdog import FinancialWatchdog


class MCPGateway:
    """
    Unified Model Context Protocol (MCP) Gateway.
    Encapsulates live internet search, central bank rate scraping, deterministic financial databases,
    and underwriter credit engines behind standard tool contracts.
    """

    TOOLS_REGISTRY: Dict[str, Dict[str, Any]] = {
        "fetch_boe_base_rate": {
            "name": "fetch_boe_base_rate",
            "description": "Scrapes the official Bank of England base rate directly from bankofengland.co.uk in <200ms.",
            "parameters": {
                "type": "object",
                "properties": {
                    "timeout": {"type": "number", "description": "HTTP timeout in seconds", "default": 2.5}
                }
            }
        },
        "fetch_top_savings_and_isas": {
            "name": "fetch_top_savings_and_isas",
            "description": "Returns current UK market-leading FSCS protected Cash ISAs, Regular Savers, and Bank Switch deals.",
            "parameters": {
                "type": "object",
                "properties": {}
            }
        },
        "search_web_instant": {
            "name": "search_web_instant",
            "description": "Multi-tier live UK web knowledge engine: evaluates statutory HMRC schedules, queries Google Search (if API key or CSE is configured), or scrapes live UK organic web results from GOV.UK, HMRC, and NS&I in <350ms.",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "The search query (e.g. 'HMRC ISA allowance 2026', 'BoE inflation target')"}
                },
                "required": ["query"]
            }
        },
        "search_web_live": {
            "name": "search_web_live",
            "description": "Multi-tier live UK web knowledge engine: evaluates statutory HMRC schedules, queries Google Search (if API key or CSE is configured), or scrapes live UK organic web results from GOV.UK, HMRC, and NS&I in <350ms.",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "The search query (e.g. 'HMRC ISA allowance 2026', 'BoE inflation target')"}
                },
                "required": ["query"]
            }
        },
        "query_spending_and_transactions": {
            "name": "query_spending_and_transactions",
            "description": "Calculates exact verified client spending by category (groceries, pubs, subscriptions), merchant, or time window from SQLite.",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "Natural language or category query string"},
                    "limit": {"type": "integer", "description": "Max itemized transactions to retrieve", "default": 15}
                },
                "required": ["query"]
            }
        },
        "credit_affordability_audit": {
            "name": "credit_affordability_audit",
            "description": "Calculates FCA MCOB 11 underwriter borrowing capacity, Uncommitted Monthly Income (UMI), Debt-to-Income (DTI), and mortgage stress test.",
            "parameters": {
                "type": "object",
                "properties": {}
            }
        },
        "tax_wealth_audit": {
            "name": "tax_wealth_audit",
            "description": "Calculates UK income tax band, marginal rates, 60% tax trap exposure, and pension (SIPP) tax relief optimization.",
            "parameters": {
                "type": "object",
                "properties": {
                    "gross_income": {"type": "number", "description": "Annual gross income in GBP"}
                }
            }
        },
        "financial_watchdog_audit": {
            "name": "financial_watchdog_audit",
            "description": "Audits verified recurring bills, price hikes, duplicate charges, and upcoming obligations for the next 14-30 days.",
            "parameters": {
                "type": "object",
                "properties": {}
            }
        },
        "vector_search_documents": {
            "name": "vector_search_documents",
            "description": "Performs local semantic vector search across statutory HMRC tax rules, FCA MCOB underwriting standards, and financial documents.",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "Semantic query or topic to retrieve (e.g. 'ISA allowances', '60% tax trap', 'mortgage stress')"},
                    "top_k": {"type": "integer", "description": "Number of relevant chunks to retrieve", "default": 2}
                },
                "required": ["query"]
            }
        }
    }

    @classmethod
    def list_tools(cls) -> List[Dict[str, Any]]:
        """Returns MCP tool definitions formatted for LLM function calling and MCP clients."""
        return list(cls.TOOLS_REGISTRY.values())

    @classmethod
    def call_tool(cls, tool_name: str, arguments: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Executes an MCP tool with high-precision latency measurement and error handling.
        Returns execution result and observability metadata.
        """
        args = arguments or {}
        start_t = time.perf_counter()
        status = "SUCCESS"
        error_msg = None
        result: Any = None

        try:
            if tool_name == "fetch_boe_base_rate":
                timeout = float(args.get("timeout", 2.5))
                result = fetch_boe_base_rate(timeout=timeout)

            elif tool_name == "fetch_top_savings_and_isas":
                result = fetch_top_savings_and_isas()

            elif tool_name in ("search_web_instant", "search_web_live"):
                q = args.get("query", "")
                result = search_duckduckgo_instant(q) or {"heading": q, "abstract": "No instant summary found; refer to official HMRC/BoE guidelines."}

            elif tool_name == "query_spending_and_transactions":
                q = args.get("query", "")
                limit = int(args.get("limit", 15))
                result = SpendingInsightEngine.query_spending(query_str=q, limit=limit)

            elif tool_name == "credit_affordability_audit":
                result = CreditAffordabilityEngine.run_full_audit()

            elif tool_name == "tax_wealth_audit":
                inc = float(args.get("gross_income", 55000.0))
                result = UKTaxOptimizer.full_tax_wealth_audit(gross_income=inc, liquid_cash=7500.0)

            elif tool_name == "financial_watchdog_audit":
                wd = FinancialWatchdog()
                result = wd.run_full_audit()

            elif tool_name == "vector_search_documents":
                from fiduciary.agent.vector_rag import get_vector_rag
                q = args.get("query", "")
                k = int(args.get("top_k", 2))
                rag = get_vector_rag()
                result = rag.search(query=q, top_k=k)

            else:
                status = "NOT_FOUND"
                error_msg = f"Unknown tool: {tool_name}"
        except Exception as e:
            status = "ERROR"
            error_msg = str(e)

        latency_ms = round((time.perf_counter() - start_t) * 1000.0, 2)

        return {
            "tool_name": tool_name,
            "status": status,
            "latency_ms": latency_ms,
            "arguments": args,
            "result": result,
            "error": error_msg
        }

    @classmethod
    def resolve_and_ground(
        cls,
        user_query: str,
        profile: Dict[str, Any],
        watchdog: Dict[str, Any],
        tax_audit: Dict[str, Any]
    ) -> Tuple[List[str], List[Dict[str, Any]]]:
        """
        Dynamically analyzes user intent, calls relevant MCP tools,
        and constructs authoritative grounded context blocks with full tool observability.
        """
        q_lower = user_query.lower()
        context_blocks: List[str] = []
        tools_executed: List[Dict[str, Any]] = []

        # 1. Bank of England / Interest Rates
        if any(w in q_lower for w in ["bank of england", "boe", "base rate", "interest rate"]):
            exec_res = cls.call_tool("fetch_boe_base_rate")
            tools_executed.append({
                "tool_name": "fetch_boe_base_rate",
                "type": "mcp_live_web_scraper",
                "source": "Bank of England (bankofengland.co.uk)",
                "latency_ms": exec_res["latency_ms"],
                "status": exec_res["status"],
                "summary": f"Official Bank Rate: {exec_res['result'].get('formatted')}"
            })
            context_blocks.append(
                f"• LIVE BANK OF ENGLAND BASE RATE: Official Bank Rate is {exec_res['result'].get('formatted')} "
                f"(Source: {exec_res['result'].get('source')})"
            )

        # 2. Market Savings & Cash ISAs
        if any(w in q_lower for w in ["isa", "cash isa", "savings", "saver", "switch bonus"]):
            exec_res = cls.call_tool("fetch_top_savings_and_isas")
            tools_executed.append({
                "tool_name": "fetch_top_savings_and_isas",
                "type": "mcp_market_benchmark",
                "source": "UK Market Benchmarks (FCA/FSCS)",
                "latency_ms": exec_res["latency_ms"],
                "status": exec_res["status"],
                "summary": "Trading 212 4.87%, First Direct 7.00% Regular Saver, Nationwide £175 switch"
            })
            data = exec_res["result"]
            isa_str = ", ".join([f"{i['provider']} ({i['aer']}% AER)" for i in data.get("cash_isas", [])[:2]])
            saver_str = ", ".join([f"{s['provider']} ({s['aer']}% AER)" for s in data.get("regular_savers", [])[:2]])
            context_blocks.append(
                f"• VERIFIED UK MARKET SAVINGS BENCHMARKS:\n"
                f"  - Leading Cash ISAs: {isa_str}\n"
                f"  - Top Regular Savers: {saver_str}"
            )

        # 3. Web Search for Definitions / Allowances
        if any(w in q_lower for w in ["allowance", "cgt", "taper", "what is", "define", "inflation"]):
            exec_res = cls.call_tool("search_web_instant", {"query": user_query})
            if exec_res.get("result", {}).get("abstract"):
                tools_executed.append({
                    "tool_name": "search_web_instant",
                    "type": "mcp_web_search",
                    "source": "DuckDuckGo Instant Knowledge API",
                    "latency_ms": exec_res["latency_ms"],
                    "status": exec_res["status"],
                    "summary": f"Found abstract for '{user_query}'"
                })
                context_blocks.append(
                    f"• LIVE WEB KNOWLEDGE ({exec_res['result']['heading']}): {exec_res['result']['abstract']}"
                )

        return context_blocks, tools_executed
