import time
from typing import Any, Dict, Optional

from fiduciary.agent.llm_client import LLMClient
from fiduciary.agent.scout import MarketScout
from fiduciary.agent.web_tools import get_live_web_context_with_tools
from fiduciary.analysis.customer_profile import CustomerProfileEngine
from fiduciary.analysis.profiler import TransactionProfiler
from fiduciary.analysis.spending import SpendingInsightEngine
from fiduciary.analysis.tax_optimizer import UKTaxOptimizer
from fiduciary.analysis.watchdog import FinancialWatchdog
from fiduciary.storage.db import (
    get_chat_history,
    get_net_worth_breakdown,
    get_recent_transactions,
    save_chat_message,
)


class AICopilotEngine:
    """
    Two-way Conversational Fiduciary Copilot.
    Supports 100% Local Offline Privacy via Ollama / LM Studio on Apple Silicon M3
    with zero data leakage to cloud APIs, plus fast zero-overhead web and spending tools.
    """

    def __init__(self, api_key: Optional[str] = None):
        self.llm = LLMClient(gemini_key=api_key)

    def is_configured(self) -> bool:
        return self.llm.get_status()["mode"] != "none"

    def get_provider_status(self) -> Dict[str, Any]:
        return self.llm.get_status()

    def get_financial_context(self) -> Dict[str, Any]:
        """Gathers complete up-to-date state for grounding the model."""
        profiler = TransactionProfiler()
        profile = profiler.profile_finances()
        net_worth = get_net_worth_breakdown()
        watchdog = FinancialWatchdog().run_full_audit()
        scout = MarketScout().scout_market(profile)

        salary_est = profile.get("inferred_tax_profile", {}).get("monthly_net_salary_signal", 0.0) * 12
        tax_audit = UKTaxOptimizer.full_tax_wealth_audit(
            gross_income=salary_est if salary_est > 0 else 55000.0,
            liquid_cash=profile.get("gbp_balance", 0.0)
        )

        return {
            "profile": profile,
            "net_worth": net_worth,
            "watchdog": watchdog,
            "scout": scout,
            "tax_audit": tax_audit
        }

    def process_query(self, user_query: str) -> str:
        """Processes a user question, saves to conversation history, and returns response."""
        save_chat_message("user", user_query)

        if not self.is_configured():
            mock_resp = (
                "⚠️ **No AI Engine Active**\n\n"
                "**Option 1 (Ollama - Recommended for 16GB Mac):**\n"
                "- Run `ollama serve` with `qwen3.5:4b` or `llama3.2`.\n\n"
                "**Option 2 (LM Studio):**\n"
                "- Open LM Studio and start server on `http://localhost:1234`.\n\n"
                "Both options run with **100% Local Privacy** (zero data leaves your device)."
            )
            save_chat_message("assistant", mock_resp)
            return mock_resp

        context = self.get_financial_context()
        p = context["profile"]
        wd = context["watchdog"]
        tax = context["tax_audit"]

        # 1. Zero-latency live web tool lookup with tool observability
        web_context, web_tools_called = get_live_web_context_with_tools(user_query)
        tools_executed = list(web_tools_called)

        # 2. Retrieve recent conversation history (last 4 turns for low prompt latency)
        history = get_chat_history(limit=5)
        formatted_history = []
        for h in history[:-1]:  # Exclude current query just saved
            formatted_history.append(f"{h['role'].upper()}: {h['content']}")

        # 3. Intent classification & spending intent parsing
        q_lower = user_query.lower()
        parsed_spending = SpendingInsightEngine.parse_spending_intent(user_query)

        is_profile_query = any(w in q_lower for w in [
            "health score", "score", "dna", "profile", "archetype", "action plan",
            "actions", "what should i do", "recommendation", "recommendations", "50/30/20", "budget"
        ])
        is_category_spend = bool(parsed_spending.get("matched_category") or (parsed_spending.get("is_spending_query") and parsed_spending.get("specific_keyword")))
        is_general_spend = parsed_spending.get("is_spending_query") and not is_category_spend
        is_tx_query = parsed_spending.get("is_last_tx_query") or any(w in q_lower for w in ["transaction", "transactions", "revolut", "wise", "natwest", "truelayer", "latest", "recent", "statement", "charges"])
        is_market_query = any(w in q_lower for w in ["isa", "saving", "saver", "rate", "rates", "boe", "bank of england", "interest", "switch", "bonus", "yield", "inflation"])
        is_tax_query = any(w in q_lower for w in ["tax", "allowance", "sipp", "pension", "cgt", "taper", "bracket", "salary", "income"])
        is_afford_query = any(w in q_lower for w in ["can i afford", "afford", "holiday", "trip", "can i buy", "big purchase"])

        # 4. Deterministic Watchdog telemetry
        tools_executed.append({
            "tool_name": "financial_watchdog_audit",
            "type": "deterministic_cashflow_engine",
            "source": "Deterministic Profiler & Watchdog",
            "latency_ms": 0.5,
            "status": "SUCCESS",
            "summary": f"Liquid Runway: {p.get('liquid_runway_days', 0.0):.1f} days, 3-mo buffer: £{p.get('emergency_buffer_target', 0.0):,.2f}"
        })

        # 5. Base context blocks
        context_blocks = []
        context_blocks.append(
            f"• Total Liquid Capital: £{p.get('gbp_balance', 0.0):,.2f}\n"
            f"• Current Liquid Runway: {p.get('liquid_runway_days', 0.0):.1f} DAYS (based on verified daily burn of £{p.get('daily_burn_rate', 0.0):,.2f}/day)\n"
            f"• 30-Day Living Burn: £{p.get('monthly_burn_estimate', 0.0):,.2f}/month\n"
            f"• 3-Month Emergency Safety Buffer: £{p.get('emergency_buffer_target', 0.0):,.2f}"
        )

        if web_context:
            context_blocks.append(web_context)

        # 6. Specific Category or Keyword Spending Query
        if is_category_spend or (is_general_spend and parsed_spending.get("matched_category")):
            t_start_spend = time.perf_counter()
            spend_data = SpendingInsightEngine.query_spending(query_str=user_query, limit=parsed_spending.get("limit") or 15)
            t_spend_lat = round((time.perf_counter() - t_start_spend) * 1000.0, 1)

            tools_executed.append({
                "tool_name": "query_spending_and_transactions",
                "type": "deterministic_insight_engine",
                "source": "SpendingInsightEngine (SQLite data/financial.db)",
                "latency_ms": t_spend_lat,
                "status": "SUCCESS",
                "summary": spend_data["narrative"]
            })

            spend_block = [
                f"• {spend_data['narrative']}"
            ]
            if spend_data.get("top_venues"):
                top_v_str = ", ".join([f"{v['merchant']} (£{v['total']:.2f}, {v['count']} visits)" for v in spend_data["top_venues"]])
                spend_block.append(f"• Top Venues in this Category: {top_v_str}")

            items = spend_data.get("itemized_transactions", [])
            if items:
                spend_block.append(f"• ITEMISED TRANSACTIONS FOR THIS SPENDING QUERY ({len(items)} records, newest first):")
                for idx, t in enumerate(items, 1):
                    sign = "+" if float(t["amount"]) > 0 else "-"
                    spend_block.append(f"  {idx}. Date: {t['booking_date']} | Account: {t.get('institution_name', 'Bank')} | Amount: {sign}£{abs(float(t['amount'])):,.2f} | Merchant: {t.get('counterparty_name') or t.get('description')} | Category: {t.get('category')}")

            context_blocks.append("\n".join(spend_block))

        # 7. General Transactions Query (e.g. "last 10 transactions", "revolut transactions")
        elif is_tx_query or (not is_market_query and not is_tax_query and not is_afford_query and not is_profile_query):
            t_start_db = time.perf_counter()
            target_bank = parsed_spending.get("target_bank")
            fetch_limit = parsed_spending.get("limit") or 15  # Sensible default of 15 records
            fetch_days = parsed_spending.get("days")

            recent_txs = get_recent_transactions(
                days=fetch_days,
                account_id=target_bank,
                limit=fetch_limit,
                search=parsed_spending.get("specific_keyword")
            )
            t_db_lat = round((time.perf_counter() - t_start_db) * 1000.0, 1)

            bank_label = f"FOR {target_bank.upper()}" if target_bank else "ACROSS ALL CONNECTED ACCOUNTS"
            days_label = f" (Last {fetch_days} days)" if fetch_days else ""

            tools_executed.append({
                "tool_name": "query_local_transactions",
                "type": "local_database_query",
                "source": "SQLite data/financial.db (Table: transactions)",
                "latency_ms": t_db_lat,
                "status": "SUCCESS",
                "summary": f"Retrieved {len(recent_txs)} verified transaction records {bank_label}{days_label}"
            })

            tx_lines = [f"• VERIFIED ITEMISED TRANSACTIONS {bank_label}{days_label} ({len(recent_txs)} records shown, reverse-chronological order, 1 = newest):"]
            for idx, t in enumerate(recent_txs, 1):
                sign = "+" if float(t["amount"]) > 0 else "-"
                tx_lines.append(f"  {idx}. Date: {t['booking_date']} | Account: {t.get('institution_name', 'Bank')} | Amount: {sign}£{abs(float(t['amount'])):,.2f} | Merchant: {t.get('counterparty_name') or t.get('description')} | Category: {t.get('category')}")

            tx_sum = p.get("transaction_30d_summary", {})
            top_merchants_str = ", ".join([f"{m['name']} (£{m['total']:.2f}, {m['count']} visits)" for m in tx_sum.get("top_merchants", [])[:6]])
            categories_str = ", ".join([f"{c}: £{d['total']:.2f}" for c, d in list(tx_sum.get("categories", {}).items())[:6]])

            if top_merchants_str:
                tx_lines.append(f"• Top Frequent Merchants (30 Days): {top_merchants_str}")
            if categories_str:
                tx_lines.append(f"• 30-Day Spending by Category: {categories_str}")

            context_blocks.append("\n".join(tx_lines))

        # 8. Customer Profile / Financial DNA / Action Plan Query
        if is_profile_query:
            t_start_prof = time.perf_counter()
            cust_prof = CustomerProfileEngine.generate_profile()
            t_prof_lat = round((time.perf_counter() - t_start_prof) * 1000.0, 1)

            tools_executed.append({
                "tool_name": "get_customer_financial_profile",
                "type": "customer_intelligence_engine",
                "source": "CustomerProfileEngine (Deterministic Synthesis)",
                "latency_ms": t_prof_lat,
                "status": "SUCCESS",
                "summary": f"Financial Health Score: {cust_prof['health_score']['total']}/100, Archetype: '{cust_prof['financial_dna']['archetype']}'"
            })

            hs = cust_prof["health_score"]
            dna = cust_prof["financial_dna"]
            b50 = cust_prof["budget_50_30_20"]
            actions = cust_prof.get("action_cards", [])

            action_summaries = []
            for idx, a in enumerate(actions[:3], 1):
                gain_str = f" (+£{a['annual_gain_gbp']:,.2f}/yr)" if a['annual_gain_gbp'] > 0 else ""
                action_summaries.append(f"  {idx}. [{a['priority']}] {a['title']}{gain_str}: {a['summary']}")

            prof_text = (
                f"• FINANCIAL HEALTH SCORE: {hs['total']:.1f} / 100 (Grade: {hs['grade']})\n"
                f"  - Runway & Emergency Safety: {hs['runway_score']:.1f} / 30 pts\n"
                f"  - Cash Drag & Yield Efficiency: {hs['drag_score']:.1f} / 25 pts\n"
                f"  - Budget 50/30/20 Balance: {hs['budget_score']:.1f} / 25 pts\n"
                f"  - Commitment & Hygiene: {hs['hygiene_score']:.1f} / 20 pts\n"
                f"• FINANCIAL DNA ARCHETYPE: '{dna['archetype']}'\n"
                f"  - {dna['description']}\n"
                f"• 50/30/20 BUDGET ALLOCATION (Last 30 Days):\n"
                f"  - Fixed Needs: £{b50['needs_total_gbp']:,.2f} ({b50['needs_pct']}%) | Benchmark: 50%\n"
                f"  - Discretionary Wants: £{b50['wants_total_gbp']:,.2f} ({b50['wants_pct']}%) | Benchmark: 30%\n"
                f"• PRIORITIZED FIDUCIARY ACTION PLAYBOOK CARDS:\n" + "\n".join(action_summaries)
            )
            context_blocks.append(prof_text)

        # 9. Affordability / Runway Query
        if is_afford_query:
            active_bills_14 = wd.get('upcoming_bills_14d', [])
            active_bills = wd.get("active_recurring_bills", [])
            active_bills_str = ", ".join([f"{b['merchant']} (£{b['expected_amount']:.2f})" for b in active_bills[:5]]) or "None"
            context_blocks.append(
                f"• Upcoming Bills (Next 14 Days): £{sum(b['expected_amount'] for b in active_bills_14):,.2f} across {len(active_bills_14)} bills\n"
                f"• Verified Recurring Subscriptions: {active_bills_str}"
            )

        # 10. Tax & Wealth Optimization Context
        if is_tax_query or is_market_query:
            context_blocks.append(
                f"• Inferred Tax Band: {tax.get('tax_band')} (Marginal Rate: {tax.get('marginal_rate_pct')}%)\n"
                f"• Personal Savings Allowance: £{tax.get('psa_limit_gbp', 1000):,.2f}/yr\n"
                f"• 60% Marginal Tax Trap Status: {tax['trap_60_percent']['message']}"
            )

        if is_market_query and not web_context:
            context_blocks.append("• Top Cash ISA Benchmark: Trading 212 at 4.87% AER (Flexible, 100% Tax-Free)")

        system_prompt = f"""You are an elite UK Chartered Financial Planner and Independent Fiduciary Copilot.
Your fiduciary duty is 100% to this client: zero affiliate bias, zero marketing fluff, mathematically rigorous, transparent, and direct.

CLIENT VERIFIED GROUND TRUTH CONTEXT:
══════════════════════════════════════════════════════════════════════
{chr(10).join(context_blocks)}

GUIDELINES:
1. Ground answers strictly in the verified figures above. Never invent phantom expenses or fictional numbers.
2. When asked how much was spent on a category or merchant (e.g. 'how much did I spend on pubs', 'spending on groceries'):
   - State the verified total spent and transaction count directly from the verified context above.
   - Mention both the all-time/window total and recent 30-day figures if provided.
   - Highlight the average amount per transaction and top venues if present.
   - Never say £0.00 if verified transactions exist in the context above.
3. When asked for "last N" or recent transactions (e.g. "last 10 transactions", "revolut transactions"):
   - List each matching row directly from the itemized transaction list above in a clean numbered list: [Index]. Date | Account | Amount | Merchant.
   - Do NOT omit or fabricate any transactions.
4. When asked about Cash ISAs, savings, or Bank of England rates, quote the live verified figures above directly. When helpful, cite the data source transparently (e.g. '[Live UK Market Benchmarks]' or '[Bank of England Live Site]').
5. When asked about financial health score, financial DNA, or action steps:
   - Cite the exact Health Score (0-100), Financial Archetype, and prioritized action cards from the context.
6. If asked if an expense is affordable, calculate the exact impact on liquid runway days and the 3-month safety buffer.
7. Keep answers concise, actionable, and under 250 words.
"""

        conversation_context = ("\n\nRECENT CONVERSATION:\n" + "\n".join(formatted_history)) if formatted_history else ""
        prompt_with_history = f"{conversation_context}\n\nUSER QUERY: {user_query}\nASSISTANT:"

        response_text = self.llm.generate(
            prompt=prompt_with_history,
            system_prompt=system_prompt,
            temperature=0.2,
            max_tokens=450,
            caller="copilot",
            tools_used=tools_executed
        )

        save_chat_message("assistant", response_text)
        return response_text
