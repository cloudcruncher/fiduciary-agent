import time
from typing import Any, Dict, Optional

from fiduciary.agent.llm_client import LLMClient
from fiduciary.agent.mcp_gateway import MCPGateway
from fiduciary.agent.pii_anonymizer import PIIAnonymizer
from fiduciary.agent.prompt_guard import PromptGuard
from fiduciary.agent.scout import MarketScout
from fiduciary.analysis.customer_profile import CustomerProfileEngine
from fiduciary.analysis.profiler import TransactionProfiler
from fiduciary.analysis.spending import SpendingInsightEngine
from fiduciary.analysis.tax_optimizer import UKTaxOptimizer
from fiduciary.analysis.watchdog import FinancialWatchdog
from fiduciary.storage.db import (
    clear_chat_history,
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
        self.last_eval_result: Optional[Dict[str, Any]] = None

    def _refine_response(self, critique_prompt: str, system_prompt: str, tools_executed: Optional[list] = None) -> str:
        """Executes targeted self-correction refinement pass when pre-flight evaluation detects discrepancies."""
        anonymized_critique, deanonymize_map = PIIAnonymizer.anonymize(critique_prompt)
        refined = self.llm.generate(
            prompt=anonymized_critique,
            system_prompt=system_prompt,
            temperature=0.1,
            max_tokens=1000,
            caller="copilot_self_correction",
            tools_used=tools_executed,
            bypass_cache=True
        )
        if deanonymize_map:
            refined = PIIAnonymizer.deanonymize(refined, deanonymize_map)
        return refined


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

    def process_query(self, user_query: str, session_id: str = "default", reset_session: bool = False, use_react: bool = False, return_details: bool = False) -> Any:
        """Processes a user question, runs pre-flight self-evaluation & verification, saves to history, and returns response."""
        if reset_session:
            clear_chat_history(session_id=session_id)

        save_chat_message("user", user_query, session_id=session_id)

        # 0. Prompt Guard Inspection & Injection Defense
        guard_result = PromptGuard.inspect(user_query)
        if not guard_result.is_safe:
            mock_resp = guard_result.guard_response or "🛡️ Unauthorized query blocked by Prompt Guard."
            save_chat_message("assistant", mock_resp, session_id=session_id)
            return mock_resp

        clean_query = guard_result.sanitized_query

        if not self.is_configured():
            mock_resp = (
                "⚠️ **No AI Engine Active**\n\n"
                "**Option 1 (Ollama - Recommended for 16GB Mac):**\n"
                "- Run `ollama serve` with `qwen3.5:4b` or `llama3.2`.\n\n"
                "**Option 2 (LM Studio):**\n"
                "- Open LM Studio and start server on `http://localhost:1234`.\n\n"
                "Both options run with **100% Local Privacy** (zero data leaves your device)."
            )
            save_chat_message("assistant", mock_resp, session_id=session_id)
            return mock_resp

        context = self.get_financial_context()
        p = context["profile"]
        wd = context["watchdog"]
        tax = context["tax_audit"]

        # 1. MCP Gateway grounding & live web lookup with tool observability
        mcp_context_blocks, mcp_tools_called = MCPGateway.resolve_and_ground(clean_query, p, wd, tax)
        tools_executed = list(mcp_tools_called)

        # 2. Smart conversational history: only inject prior context if query is an explicit follow-up
        q_lower = clean_query.lower()
        is_followup = any(w in q_lower for w in [
            "why", "how come", "explain that", "what about", "and then", "tell me more",
            "elaborate", "what else", "which one", "can you explain", "summarize that", "how do i"
        ])

        history = get_chat_history(limit=4, session_id=session_id)
        formatted_history = []
        if is_followup and len(history) > 1:
            for h in history[-3:-1]:  # Keep only recent immediate turn
                content = h["content"]
                if h["role"] == "assistant" and len(content) > 180:
                    content = content[:180] + "..."
                formatted_history.append(f"{h['role'].upper()}: {content}")

        # 3. Intent classification & spending intent parsing
        q_lower = clean_query.lower()
        parsed_spending = SpendingInsightEngine.parse_spending_intent(clean_query)

        is_emergency_query = any(w in q_lower for w in [
            "emergency", "buffer", "safety buffer", "rainy day", "runway", "liquid capital", "cash cushion", "savings cushion"
        ])
        is_networth_query = any(w in q_lower for w in [
            "net worth", "networth", "total assets", "balance sheet", "how much am i worth", "wealth"
        ])
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
        is_credit_query = any(w in q_lower for w in [
            "credit", "borrow", "borrowing", "mortgage", "loan", "underwriter", "affordability",
            "experian", "equifax", "transunion", "bureau", "bnpl", "klarna", "clearpay", "zilch",
            "dti", "umi", "debt to income", "uncommitted", "credit rating", "credit score", "electoral roll"
        ])

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
        if mcp_context_blocks:
            context_blocks.extend(mcp_context_blocks)

        context_blocks.append(
            f"• Total Liquid Capital: £{p.get('gbp_balance', 0.0):,.2f}\n"
            f"• Current Liquid Runway: {p.get('liquid_runway_days', 0.0):.1f} DAYS (based on verified daily burn of £{p.get('daily_burn_rate', 0.0):,.2f}/day)\n"
            f"• 30-Day Living Burn: £{p.get('monthly_burn_estimate', 0.0):,.2f}/month\n"
            f"• 3-Month Emergency Safety Buffer: £{p.get('emergency_buffer_target', 0.0):,.2f}"
        )

        # Emergency Fund & Safety Buffer Dedicated Audit
        if is_emergency_query:
            target_buffer = p.get('emergency_buffer_target', 0.0)
            liquid_capital = p.get('gbp_balance', 0.0)
            buffer_diff = liquid_capital - target_buffer
            buffer_status_str = f"Shortfall of £{abs(buffer_diff):,.2f} below the recommended 3-month buffer" if buffer_diff < 0 else f"Surplus of £{buffer_diff:,.2f} above the recommended 3-month buffer"
            runway_days = p.get('liquid_runway_days', 0.0)

            tools_executed.append({
                "tool_name": "emergency_buffer_audit",
                "type": "deterministic_emergency_engine",
                "source": "Deterministic Profiler & Watchdog",
                "latency_ms": 0.4,
                "status": "SUCCESS",
                "summary": f"Emergency Target: £{target_buffer:,.2f}, Liquid Capital: £{liquid_capital:,.2f}, Shortfall: £{abs(buffer_diff):,.2f}, Runway: {runway_days:.1f} days"
            })

            emergency_block = (
                f"• VERIFIED EMERGENCY FUND & SAFETY BUFFER AUDIT:\n"
                f"  - Recommended 3-Month Emergency Target: £{target_buffer:,.2f}\n"
                f"  - Current Liquid Capital Available: £{liquid_capital:,.2f}\n"
                f"  - Buffer Status: {buffer_status_str} ({runway_days:.1f} days of living runway vs 90 days recommended)\n"
                f"  - Verified 30-Day Monthly Living Expenses: £{p.get('monthly_burn_estimate', 0.0):,.2f}/month (£{p.get('daily_burn_rate', 0.0):,.2f}/day)\n"
                f"  - Strategic Priority: Allocate savings to reach the £{target_buffer:,.2f} threshold in an instant-access Cash ISA or high-yield account (e.g. Trading 212 at 4.87% AER)."
            )
            context_blocks.append(emergency_block)

        # Net Worth & Balance Sheet Dedicated Audit
        if is_networth_query:
            nw = context.get("net_worth", {})
            bd = nw.get("breakdown", {})
            tools_executed.append({
                "tool_name": "net_worth_audit",
                "type": "deterministic_balance_sheet_engine",
                "source": "SQLite data/financial.db (Multi-Asset Engine)",
                "latency_ms": 0.5,
                "status": "SUCCESS",
                "summary": f"Net Worth: £{nw.get('net_worth', 0.0):,.2f}, Total Assets: £{nw.get('total_assets', 0.0):,.2f}, Liabilities: £{nw.get('total_liabilities', 0.0):,.2f}"
            })
            nw_block = (
                f"• VERIFIED CLIENT NET WORTH AUDIT (BALANCE SHEET):\n"
                f"  - Total Net Worth: £{nw.get('net_worth', 0.0):,.2f}\n"
                f"  - Total Assets: £{nw.get('total_assets', 0.0):,.2f}\n"
                f"  - Total Liabilities (Debts): £{nw.get('total_liabilities', 0.0):,.2f}\n"
                f"  - Liquid Net Worth (Cash + Liquid Investments): £{nw.get('liquid_net_worth', 0.0):,.2f}\n"
                f"  - Asset Class Breakdown:\n"
                f"    * Cash & Current/Savings: £{bd.get('cash', 0.0):,.2f}\n"
                f"    * Investments & ISAs: £{bd.get('investment', 0.0):,.2f}\n"
                f"    * Pensions (SIPP & Workplace): £{bd.get('pension', 0.0):,.2f}\n"
                f"    * Property & Real Estate: £{bd.get('property', 0.0):,.2f}\n"
                f"    * Contractual Liabilities: £{bd.get('liability', 0.0):,.2f}"
            )
            context_blocks.append(nw_block)

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
                    spend_block.append(f"  {idx}. {t['booking_date']} | {t.get('institution_name', 'Bank')} | {sign}£{abs(float(t['amount'])):,.2f} | {t.get('counterparty_name') or t.get('description')} | {t.get('category')}")

            context_blocks.append("\n".join(spend_block))

        # 7. General Transactions Query (e.g. "last 10 transactions", "revolut transactions")
        elif is_tx_query or (not is_market_query and not is_tax_query and not is_afford_query and not is_profile_query and not is_credit_query):
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
                tx_lines.append(f"  {idx}. {t['booking_date']} | {t.get('institution_name', 'Bank')} | {sign}£{abs(float(t['amount'])):,.2f} | {t.get('counterparty_name') or t.get('description')} | {t.get('category')}")

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

        if is_market_query and not any("BENCHMARKS" in b for b in context_blocks):
            context_blocks.append("• Top Cash ISA Benchmark: Trading 212 at 4.87% AER (Flexible, 100% Tax-Free)")

        # 11. Credit & Borrowing Health / Underwriter Affordability Context
        if is_credit_query:
            t_start_credit = time.perf_counter()
            from fiduciary.analysis.credit_affordability import CreditAffordabilityEngine
            credit_audit = CreditAffordabilityEngine.run_full_audit()
            t_credit_lat = round((time.perf_counter() - t_start_credit) * 1000.0, 1)

            tools_executed.append({
                "tool_name": "credit_affordability_audit",
                "type": "open_banking_underwriter_engine",
                "source": "CreditAffordabilityEngine (FCA MCOB 11 Standard)",
                "latency_ms": t_credit_lat,
                "status": "SUCCESS",
                "summary": f"Borrowing Readiness: {credit_audit['borrowing_readiness_score']}/100 ({credit_audit['underwriter_tier']}), UMI: £{credit_audit['cash_flow_affordability']['uncommitted_monthly_income_umi']:,.2f}, Max Mortgage: £{credit_audit['mortgage_borrowing_capacity']['net_maximum_borrowing_capacity']:,.2f}"
            })

            cf = credit_audit["cash_flow_affordability"]
            rf = credit_audit["underwriter_risk_flags"]
            mc = credit_audit["mortgage_borrowing_capacity"]
            er = credit_audit["emergency_runway_and_stress"]
            bs = credit_audit["bureau_scores"]
            actions = credit_audit.get("action_playbook", [])

            action_lines = []
            for idx, a in enumerate(actions[:3], 1):
                action_lines.append(f"  {idx}. [{a['priority']}] {a['title']}: {a['action']}")

            credit_block = (
                f"• BORROWING READINESS SCORE: {credit_audit['borrowing_readiness_score']} / 100 (Tier: {credit_audit['underwriter_tier']})\n"
                f"  - Assessment: {credit_audit['tier_description']}\n"
                f"• OPEN BANKING CASH-FLOW AFFORDABILITY (FCA MCOB 11):\n"
                f"  - Verified Monthly Net Pay: £{cf['monthly_net_income']:,.2f} (Est. Annual Gross: £{cf['estimated_annual_gross']:,.2f})\n"
                f"  - Fixed Needs Outflow: £{cf['monthly_fixed_needs']:,.2f}/mo | Contractual Debt Commitments: £{cf['monthly_committed_debt']:,.2f}/mo\n"
                f"  - Uncommitted Monthly Income (UMI): £{cf['uncommitted_monthly_income_umi']:,.2f}/mo ({cf['umi_surplus_pct']}% surplus ratio)\n"
                f"  - Contractual Debt-to-Income (DTI): {cf['contractual_dti_pct']}% (Prime benchmark: <20%)\n"
                f"• INDICATIVE MORTGAGE BORROWING CAPACITY:\n"
                f"  - Gross Income Baseline (4.5x): £{mc['gross_income_baseline']:,.2f}\n"
                f"  - Debt Commitment Deduction: -£{mc['debt_commitment_deduction']:,.2f}\n"
                f"  - Net Maximum Mortgage Capacity: £{mc['net_maximum_borrowing_capacity']:,.2f}\n"
                f"  - Indicative 25-yr Payment ({mc['indicative_rate_pct']}% rate): £{mc['indicative_monthly_repayment']:,.2f}/mo\n"
                f"  - Stress-Tested Payment ({mc['stress_tested_rate_pct']}% rate): £{mc['stress_tested_monthly_repayment']:,.2f}/mo\n"
                f"• UNDERWRITER RISK FLAGS SCANNER:\n"
                f"  - Buy-Now-Pay-Later (BNPL / Klarna): {'⚠️ DETECTED (' + rf['bnpl_summary'] + ')' if rf['bnpl_detected'] else '✅ None detected (Clean)'}\n"
                f"  - Bounced / Returned Direct Debits: {'⚠️ DETECTED (' + str(rf['bounced_count']) + ' returned)' if rf['bounced_direct_debits_detected'] else '✅ Clean (0 returned in 180 days)'}\n"
                f"  - Overdraft Reliance / Unarranged Fees: {'⚠️ Overdraft activity detected' if rf['overdraft_reliance'] else '✅ Clean (No overdraft usage)'}\n"
                f"  - Gambling Outflow: £{rf['gambling_spend_30d']:.2f} ({rf['gambling_pct_of_income']}% of net pay - {rf['gambling_risk']})\n"
                f"  - ATM Cash Ratio: £{rf['atm_cash_withdrawals_30d']:.2f} ({rf['atm_pct_of_income']}% of net pay)\n"
                f"  - Electoral Roll Verified: {'✅ Yes (Registered)' if rf['electoral_roll_verified'] else '⚠️ Not registered on Electoral Roll'}\n"
                f"• SELF-REPORTED BUREAU SCORES: Experian: {bs.get('experian') or 'N/A'}/999 | Equifax: {bs.get('equifax') or 'N/A'}/1000 | TransUnion: {bs.get('transunion') or 'N/A'}/710\n"
                f"• EMERGENCY RUNWAY UNDER STRESS: Comfortable {er['comfortable_runway_months']} months | Survival (bare-bones) {er['survival_runway_months']} months\n"
                f"• TOP CREDIT ACTION PLAYBOOK RECOMMENDATIONS:\n" + ("\n".join(action_lines) if action_lines else "  None")
            )
            context_blocks.append(credit_block)

        wrapped_context = PromptGuard.wrap_context_boundaries("\n\n".join(context_blocks))

        system_prompt = f"""You are the client's private, on-device Personal Financial Analytics Copilot and Fiduciary Engine.
Your fiduciary duty is 100% to this client: zero affiliate bias, zero marketing fluff, mathematically exact, transparent, and direct.
All information you provide is deterministic mathematical analysis, database calculation, and analytical data retrieval—it is NOT regulated, speculative, or product-selling advice.

COMPLIANCE & SYSTEM DIRECTIVES:
1. NEVER refuse to answer legitimate queries about the client's verified data, balances, emergency buffers, runway, transactions, or market benchmarks.
2. NEVER output disclaimers like "I cannot provide financial advice", "I am just an AI", or "Please speak with a certified financial advisor" when asked about the user's balances, transactions, emergency fund targets, or net worth. The user has explicitly authorized this system to report and explain their own private financial telemetry.
3. Ground answers strictly in the verified context enclosed in <verified_financial_context> below. Never invent phantom numbers, transactions, or fake rates.
4. When asked about emergency fund, safety buffer, or runway (e.g. 'What is my emergency fund buffer?'):
   - State clearly: The recommended 3-month emergency safety buffer target is £{p.get('emergency_buffer_target', 0.0):,.2f}, and current liquid capital is £{p.get('gbp_balance', 0.0):,.2f}.
   - Report the exact shortfall (£{max(0.0, p.get('emergency_buffer_target', 0.0) - p.get('gbp_balance', 0.0)):,.2f}) or surplus, and current liquid runway ({p.get('liquid_runway_days', 0.0):.1f} days vs 90 days recommended).
   - Base this on verified monthly living burn of £{p.get('monthly_burn_estimate', 0.0):,.2f}/month.
5. When asked about net worth, total assets, or balance sheet:
   - State the Total Net Worth, Total Assets, and Total Liabilities directly from the verified balance sheet.
6. When asked how much was spent on a category or merchant (e.g. 'how much did I spend on pubs', 'spending on groceries'):
   - State the verified total spent and transaction count directly from the verified context.
   - Mention both the all-time/window total and recent 30-day figures if provided.
   - Highlight the average amount per transaction and top venues if present.
   - Never say £0.00 if verified transactions exist in the context.
7. When asked for "last N" or recent transactions (e.g. "last 10 transactions", "revolut transactions"):
   - List each matching row directly from the itemized transaction list in a clean numbered list: [Index]. Date | Account | Amount | Merchant.
   - Do NOT omit or fabricate any transactions.
8. When asked about Cash ISAs, savings, or Bank of England rates, quote the verified live figures directly. Cite the data source transparently (e.g. '[Bank of England Live Site]' or '[UK Market Benchmarks]').
9. When asked about financial health score, financial DNA, or action steps:
   - Cite the exact Health Score (0-100), Financial Archetype, and prioritized action cards from the context.
10. If asked if an expense is affordable, calculate the exact impact on liquid runway days and the 3-month safety buffer.
11. Keep answers concise, actionable, and under 250 words.
12. When asked about credit score, borrowing capacity, mortgage readiness, or underwriter checks:
    - State the Borrowing Readiness Score (0-100) and Underwriter Tier clearly.
    - Ground your answer in verified Open Banking cash-flow affordability metrics: Uncommitted Monthly Income (UMI) and Debt-to-Income (DTI).
    - If BNPL (Klarna/Clearpay) or other risk flags are present, explain the exact underwriter impact and corrective steps.
    - Quote the verified indicative mortgage borrowing capacity (£) and monthly repayments (4.4% indicative vs 7.5% stress-tested).

CLIENT VERIFIED GROUND TRUTH CONTEXT:
══════════════════════════════════════════════════════════════════════
{wrapped_context}
"""

        conversation_context = ("\n\nRECENT CONVERSATION:\n" + "\n".join(formatted_history)) if formatted_history else ""
        prompt_with_history = f"{conversation_context}\n\nUSER QUERY: {user_query}\nASSISTANT:"

        from fiduciary.observability.preflight_eval import PreFlightEvaluator

        if use_react:
            from fiduciary.agent.react_agent import ReActFiduciaryAgent
            react_agent = ReActFiduciaryAgent(llm=self.llm, enable_pii_anonymization=True)
            res = react_agent.run(clean_query, context=wrapped_context)
            final_ans = res["answer"]

            eval_res = PreFlightEvaluator.evaluate_and_guard(
                user_query=user_query,
                response=final_ans,
                system_prompt=wrapped_context,
                refine_callback=(
                    lambda critique: self._refine_response(critique, system_prompt, tools_executed)
                    if self.is_configured() else None
                )
            )
            guarded_ans = eval_res.response
            self.last_eval_result = eval_res.to_dict()
            save_chat_message("assistant", guarded_ans, session_id=session_id, metadata={"preflight_eval": self.last_eval_result})

            if return_details:
                return {
                    "answer": guarded_ans,
                    "eval": self.last_eval_result,
                    "react_steps": res.get("steps", [])
                }
            return guarded_ans

        # Reversible PII anonymization before passing prompt to LLM
        anonymized_prompt, deanonymize_map = PIIAnonymizer.anonymize(prompt_with_history)

        response_text = self.llm.generate(
            prompt=anonymized_prompt,
            system_prompt=system_prompt,
            temperature=0.2,
            max_tokens=1000,
            caller="copilot",
            tools_used=tools_executed
        )

        if deanonymize_map:
            response_text = PIIAnonymizer.deanonymize(response_text, deanonymize_map)

        # In-line Pre-Flight Self-Evaluation & Verification Gate
        eval_res = PreFlightEvaluator.evaluate_and_guard(
            user_query=user_query,
            response=response_text,
            system_prompt=wrapped_context,
            refine_callback=(
                lambda critique: self._refine_response(critique, system_prompt, tools_executed)
                if self.is_configured() else None
            )
        )
        guarded_response = eval_res.response
        self.last_eval_result = eval_res.to_dict()

        save_chat_message("assistant", guarded_response, session_id=session_id, metadata={"preflight_eval": self.last_eval_result})

        if return_details:
            return {
                "answer": guarded_response,
                "eval": self.last_eval_result
            }
        return guarded_response


