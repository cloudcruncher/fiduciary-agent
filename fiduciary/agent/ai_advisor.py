from typing import Any, Dict, Optional

from fiduciary.agent.llm_client import LLMClient


class AIFiduciaryAdvisor:
    """
    Autonomous AI Fiduciary Advisor powered by Local LM Studio (100% Private on Apple Silicon)
    or Google Gemini Cloud.
    Synthesizes read-only 30-day Open Banking transaction intelligence,
    diagnoses cashflow friction, evaluates living runway, audits spending drag,
    and produces an institutional-grade fiduciary memorandum with verified links.
    """

    def __init__(self, api_key: Optional[str] = None):
        self.llm_client = LLMClient(gemini_key=api_key)

    def is_configured(self) -> bool:
        status = self.llm_client.get_status()
        return status["mode"] != "none"

    def generate_live_briefing(self, state: Dict[str, Any], profile: Dict[str, Any]) -> str:
        if not self.is_configured():
            return (
                "⚠️ **Live AI Advisor Not Configured**\n\n"
                "To enable real-time institutional fiduciary analysis:\n"
                "1. **Local & Private (Recommended)**: Open **LM Studio**, load a model (e.g. `Meta-Llama-3.1-8B` or `Mistral-7B`), and start server on port 1234.\n"
                "2. **Or Cloud API**: Add your Gemini API key to `.env`:\n"
                "   ```bash\n"
                "   GEMINI_API_KEY=\"your_gemini_api_key_here\"\n"
                "   ```\n"
                "3. Re-run `./f a` or `./f ai` to generate the fiduciary memorandum.\n"
            )

        tax_info = profile.get("inferred_tax_profile", {})
        tax_band = tax_info.get("tax_band", "Basic Rate (20%)")
        tax_rate = tax_info.get("marginal_tax_rate", 0.20)
        psa = tax_info.get("personal_savings_allowance_gbp", 1000)
        dds_count = profile.get("switch_eligible_direct_debits_count", 0)
        dds_list = [d["merchant"] for d in profile.get("recurring_direct_debits", [])]

        # 30-day transaction intelligence
        tx_stats = profile.get("transaction_30d_summary", {})
        total_inflows = tx_stats.get("total_inflows", 0.0)
        total_outflows = tx_stats.get("total_outflows", 0.0)
        net_cashflow = tx_stats.get("net_cashflow", 0.0)
        living_spend = tx_stats.get("living_spend_total", 0.0)
        daily_burn = profile.get("daily_burn_rate", 18.72)
        runway_days = profile.get("liquid_runway_days", 1.5)
        card_spend = tx_stats.get("card_spend_total", 0.0)
        cashback_opp = profile.get("annual_cashback_potential", 0.0)
        funding_behavior = profile.get("funding_behavior", "Variable inflows")

        # Categories & merchants
        cat_lines = []
        for cat_name, c_data in tx_stats.get("categories", {}).items():
            cat_lines.append(f"  - {cat_name}: £{c_data['total']:,.2f} ({c_data['pct_of_outflow']}% of spend, {c_data['count']} transactions)")

        merchant_lines = []
        for m in tx_stats.get("top_merchants", [])[:6]:
            merchant_lines.append(f"  - {m['name']}: £{m['total']:,.2f} ({m['count']} visits, Category: {m['category']})")

        sub_lines = []
        for s in tx_stats.get("subscriptions", []):
            sub_lines.append(f"  - {s['name']}: £{s['amount']:,.2f}/mo (billed {s['date']})")

        accounts_detail = state.get("accounts_detail", [])
        acc_lines = [f"{a.get('name', 'Account')}: £{a.get('current_balance', 0.0):,.2f} ({a.get('currency', 'GBP')})" for a in accounts_detail]

        prompt = f"""
You are an elite UK Chartered Financial Planner and Independent Fiduciary Advocate.
Your fiduciary duty is 100% to this client: zero kickbacks, zero affiliate fluff, pure mathematical transparency, and actionable clarity.

The following is REAL 30-day Open Banking transaction intelligence directly extracted from their active accounts:

══════════════════════════════════════════════════════════════════════
CLIENT FINANCIAL & TRANSACTION DOSSIER (LAST 30 DAYS):
══════════════════════════════════════════════════════════════════════
• Connected Accounts:
{chr(10).join(['  • ' + al for al in acc_lines])}
• Total Liquid Capital On Hand: £{state.get('gbp_total_balance', 0.0):,.2f}
• Current Liquid Runway: {runway_days:.1f} DAYS (based on verified daily burn)
• Verified Daily Burn Rate: £{daily_burn:,.2f}/day (£{living_spend:,.2f} living expenses over 30 days)
• Normalized Monthly Living Burn: £{profile.get('monthly_burn_estimate', 560.0):,.2f}/month
• Inflows (Last 30 Days): £{total_inflows:,.2f} across {tx_stats.get('inflow_count', 0)} deposits
• Outflows (Last 30 Days): £{total_outflows:,.2f} across {tx_stats.get('outflow_count', 0)} transactions
• Net 30-Day Cashflow: £{net_cashflow:,.2f}
• Funding Pattern Detected: {funding_behavior}
• Total Debit Card Point-of-Sale Spend: £{card_spend:,.2f} (earning 0% cashback)
• Potential Annual Debit Cashback (Chase UK 1%): £{cashback_opp:,.2f}/year

ITEMIZED 30-DAY SPENDING CATEGORIES:
{chr(10).join(cat_lines) if cat_lines else '  - No categorized outflows detected'}

TOP MERCHANTS & RECURRING VENUES:
{chr(10).join(merchant_lines) if merchant_lines else '  - No merchant data'}

RECURRING SOFTWARE & SUBSCRIPTIONS DETECTED:
{chr(10).join(sub_lines) if sub_lines else '  - None detected'}

TAX & COMPLIANCE PROFILE:
• Inferred UK Tax Bracket: {tax_band} (Marginal Income Tax Rate: {int(tax_rate*100)}%)
• Personal Savings Allowance (PSA): £{psa:,.2f}/year tax-free interest
• Switch-Eligible Direct Debits / Regular Payments: {dds_count} ({', '.join(dds_list) if dds_list else 'None'})

VERIFIED LIVE UK MARKET BENCHMARKS (OCTOBER 2026):
• Chase UK Current Account: 1.0% cashback on debit card spend (groceries, dining, transit, shopping) for 12 months (up to £180/yr free cash) + 3.75% AER instant linked saver pot -> https://www.chase.co.uk/gb/en/product/chase-account/
• Trading 212 Flexible Cash ISA: 4.87% AER (100% Tax-Free, FSCS protected up to £85,000, fully flexible withdrawals that can be replaced in the same tax year without consuming allowance) -> https://www.trading212.com/isa
• Chip Cash ISA: 4.84% AER (ClearBank FSCS protected, instant access) -> https://www.getchip.uk/savings/cash-isa
• Wise In-App Feature: Wise Interest at 4.60% AER (held in BlackRock Sterling Liquidity Fund) -> https://wise.com/gb/interest/
• Bank Switch Bounties:
  - Nationwide FlexDirect: +£175 upfront cash (Requires 2 DDs) -> https://www.nationwide.co.uk/current-accounts/switch/
  - First Direct 1st Account: +£175 cash + 7% Regular Saver access (Requires 2 DDs) -> https://www.firstdirect.com/banking/current-accounts/
  - Lloyds Bank Club Lloyds: +£200 upfront cash (Requires 3 DDs) -> https://www.lloydsbank.com/current-accounts/switch.html

══════════════════════════════════════════════════════════════════════
YOUR FIDUCIARY MEMORANDUM REQUIREMENTS:
══════════════════════════════════════════════════════════════════════
Produce a comprehensive, rigorous, and highly articulate Private Wealth Advisory Memorandum structured in these 5 mandatory sections:

### 1. Executive Fiduciary Diagnosis & Liquidity Warning
- Address their current cash position (£{state.get('gbp_total_balance', 0.0):,.2f}) vs daily burn rate (£{daily_burn:,.2f}/day), emphasizing that they have only **{runway_days:.1f} days of liquid runway** on hand.
- Analyze the detected funding habit: explain why manually topping up £100 every 4-5 days from an external account creates unnecessary cognitive friction, stress, and vulnerability to declined card transactions or accidental overdraft.

### 2. 30-Day Spending & Lifestyle Audit (Where Every Pound Went)
- Provide a clear diagnostic breakdown of their £{living_spend:,.2f} living expenses (Dining ~38%, Groceries ~33%, Subscriptions ~3%).
- Highlight specific high-frequency merchants (e.g. Mum's Whole Food, Welcome Brentford, Evelyn's, PKB Angel Gardens).
- Audit their debit card rewards: quantify the exact annual loss from spending £{card_spend:,.2f}/month on 0% cashback debit cards (Revolut/Wise) instead of a 1% cashback account.
- Review tech subscriptions (Anthropic Claude Pro £18.00/mo = £216/yr + API usage) and provide advice on business tax deductibility if applicable.

### 3. Cash Flow & Capital Architecture Overhaul
- Recommend transitioning from reactive £100 top-ups to an automated monthly operating float of £{round(profile.get('monthly_burn_estimate', 560.0), -1):,.2f} scheduled on the 1st of each month via Standing Order.
- Calculate the exact calibrated Emergency Reserve:
  * 3-Month Baseline Safety Buffer: **£{profile.get('emergency_buffer_target', 1680.0):,.2f}**
  * 6-Month Full Resilience Buffer: **£{profile.get('six_month_buffer_target', 3360.0):,.2f}**
- Explain why keeping this in a 0% current account causes cash drag, and why an easy-access Flexible Cash ISA is mathematically optimal.

### 4. Tax-Free Yield Optimization & Market Benchmarks
- Compare Trading 212 Flexible Cash ISA (4.87% AER, tax-free) vs taxable accounts (Santander 4.85% gross = {round(4.85*(1-tax_rate), 2)}% after {int(tax_rate*100)}% tax) vs Wise Interest (4.60%).
- Explain the unique value of a *flexible* Cash ISA (funds withdrawn can be replaced in the same tax year without burning their £20,000 allowance).
- Show how the Personal Savings Allowance (£{psa}/yr) applies and how the Cash ISA provides permanent shelter from future tax bracket creep.

### 5. Prioritized Fiduciary Action Checklist
Provide a clean Markdown summary table with:
- Priority (Immediate / High / Medium)
- Recommended Action
- Quantified Financial Impact (Exact £/yr gain or risk mitigation)
- Time to Execute (e.g. 5-10 mins)
- Verified Direct Application Link (using markdown `[Apply here](URL)` with the exact benchmark links provided above).

Format your response in beautiful, polished GitHub-flavored Markdown with bold callouts, tables, bullet points, and exact links.
"""

        system_prompt = (
            "You are an elite UK Chartered Financial Planner and Independent Fiduciary Advocate. "
            "Your fiduciary duty is 100% to this client: zero kickbacks, zero affiliate fluff, pure mathematical transparency, and actionable clarity."
        )

        return self.llm_client.generate(
            prompt=prompt,
            system_prompt=system_prompt,
            temperature=0.2,
            max_tokens=2500,
            timeout=90,
            caller="advisor_memo"
        )
