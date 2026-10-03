from typing import Any, Dict, List, Optional

from fiduciary.analysis.market_rates import UKMarketRates


class FiduciaryAdvisor:
    """
    Fiduciary Advisory Engine.
    Strictly customer-first:
    - 0% affiliate kickbacks or steering bias
    - Mathematical transparency
    - Solves cash flow friction, captures card cashback, and maximizes tax-free yield
    """

    def generate_recommendations(self, state: Dict[str, Any], profile: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
        actions = []
        idle_cash = state.get("idle_cash_gbp", 0.0)
        gbp_total = state.get("gbp_total_balance", 0.0)
        monthly_burn = state.get("estimated_monthly_burn", 560.0)
        runway_days = state.get("liquid_runway_days", 1.5)
        analytics = state.get("transaction_analytics", {})
        card_spend = analytics.get("card_spend_total", 0.0)
        funding_sources = analytics.get("funding_sources", [])

        benchmarks = UKMarketRates.get_benchmarks()
        wise_yield = benchmarks["wise_interest_gbp_pct"]
        top_isa_yield = benchmarks["top_cash_isa_pct"]

        # Rec 1: Cash Flow & Liquidity Float Overhaul
        if runway_days < 7.0 and funding_sources:
            actions.append({
                "priority": "HIGH",
                "category": "Cash Flow Resilience",
                "title": f"Automate Monthly Float (£{monthly_burn:,.2f}/mo) to Stop Micro Top-Ups",
                "annual_gain_gbp": 0.0,
                "summary": (
                    f"You currently have £{gbp_total:,.2f} in liquid accounts with ~{runway_days:.1f} days of runway. "
                    f"Our audit detected {analytics.get('inflow_count', 0)} manual top-ups totaling £{analytics.get('total_inflows', 0.0):,.2f} "
                    f"from '{funding_sources[0]['source']}' to fund daily spend. "
                    f"This creates mental friction, cognitive load, and risk of declined payments."
                ),
                "steps": [
                    f"Set up an automated Standing Order of £{round(monthly_burn, -1):,.2f} on the 1st of each month from your primary account to your spending account.",
                    "Keep a predictable 30-day operational float in your current account.",
                    "Eliminates the stress and friction of 5 separate manual £100 transfers per month."
                ]
            })

        # Rec 2: 1% Everyday Debit Card Cashback Capture
        if card_spend > 100:
            annual_cashback = round(card_spend * 12 * 0.01, 2)
            actions.append({
                "priority": "HIGH",
                "category": "Effortless Card Reward",
                "title": f"Switch Daily Card Spending to Chase UK (Earn +£{annual_cashback:,.2f}/yr)",
                "annual_gain_gbp": annual_cashback,
                "summary": (
                    f"You spent £{card_spend:,.2f} on debit card point-of-sale purchases in the last 30 days (Groceries, Dining, Coffee) "
                    f"earning 0% cashback. Switching everyday card spending to Chase UK gives 1% instant cashback on debit card spend for 12 months."
                ),
                "steps": [
                    "Open a fee-free Chase UK current account (5-minute app signup)",
                    "Transfer your monthly grocery & dining budget into Chase",
                    f"Spend via Chase debit card / Apple Pay to bank ~£{round(annual_cashback/12, 2):,.2f}/mo in free risk-free cash."
                ]
            })

        # Rec 3: Sizing & Siting the 3-Month Emergency Reserve
        emergency_target = round(monthly_burn * 3, 2)
        annual_isa_gain = round(emergency_target * (top_isa_yield / 100.0), 2)
        actions.append({
            "priority": "HIGH",
            "category": "Tax-Free Wealth Shield",
            "title": f"Park £{emergency_target:,.2f} Emergency Buffer in Trading 212 Flexible Cash ISA",
            "annual_gain_gbp": annual_isa_gain,
            "summary": (
                f"Based on your actual 30-day living costs of £{monthly_burn:,.2f}/month, your true 3-month safety buffer is £{emergency_target:,.2f}. "
                f"Holding this in a Flexible Cash ISA yields {top_isa_yield:.2f}% AER 100% tax-free, fully FSCS protected up to £85,000, with instant withdrawals."
            ),
            "steps": [
                "Open a Trading 212 Flexible Cash ISA (4.87% AER, instant withdrawals)",
                f"Fund with your £{emergency_target:,.2f} emergency reserve",
                "Because it is fully flexible, any money withdrawn can be replaced in the same tax year without consuming your £20k ISA allowance."
            ]
        })

        # Rec 4: Idle Cash in Wise standard balances
        if idle_cash > 200:
            annual_wise_gain = round(idle_cash * (UKMarketRates.WISE_INTEREST_GBP_YIELD), 2)
            actions.append({
                "priority": "MEDIUM",
                "category": "Instant In-App Win",
                "title": f"Toggle 'Interest' on Wise GBP Balances (+{wise_yield:.2f}% AER)",
                "annual_gain_gbp": annual_wise_gain,
                "summary": (
                    f"Wise lets you switch GBP cash balances to 'Interest' (held in BlackRock's Sterling Liquidity Fund), "
                    f"instantly yielding ~{wise_yield:.2f}% AER without transferring money out."
                ),
                "steps": [
                    "Open Wise app -> Select GBP balance",
                    "Click 'Manage' -> 'Change how you hold your money' -> Select 'Interest'",
                    "Instant liquidity remains available for card spending and transfers."
                ]
            })

        # Rec 5: Subscription Audit
        subscriptions = analytics.get("subscriptions", [])
        if subscriptions:
            total_sub_mo = sum(s["amount"] for s in subscriptions)
            actions.append({
                "priority": "LOW",
                "category": "Subscription & Tax Efficiency",
                "title": f"Audit {len(subscriptions)} Software Subscriptions (£{total_sub_mo:,.2f}/mo)",
                "annual_gain_gbp": 0.0,
                "summary": (
                    "Detected active recurring software subscriptions: "
                    + ", ".join([f"{s['name']} (£{s['amount']:,.2f})" for s in subscriptions])
                    + f". Totaling £{total_sub_mo * 12:,.2f}/year."
                ),
                "steps": [
                    "Verify you do not have overlapping AI subscriptions (e.g. Claude Pro + ChatGPT Plus).",
                    "If used for consulting, freelance, or business work, ensure you claim this as an allowable business expense for tax relief."
                ]
            })

        return actions
