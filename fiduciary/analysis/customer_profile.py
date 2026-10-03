"""
Customer Profile & Insight-to-Action Playbook Engine.
Synthesizes verified transaction patterns, runway metrics, cash drag,
and watchdog audits into an Intelligent Customer Financial Profile ('Financial DNA')
and rank-ordered fiduciary action cards.
"""

from typing import Any, Dict

from fiduciary.analysis.market_rates import UKMarketRates
from fiduciary.analysis.profiler import TransactionProfiler
from fiduciary.analysis.spending import SpendingInsightEngine
from fiduciary.analysis.watchdog import FinancialWatchdog
from fiduciary.storage.db import get_transaction_analytics


class CustomerProfileEngine:
    """
    Synthesizes financial records into:
    - Financial Health Score (0 to 100)
    - Financial Archetype ('Financial DNA')
    - 50/30/20 Budget Rule Allocation
    - Cognitive Friction Index
    - Prioritized Insight-to-Action Playbook Cards
    """

    @classmethod
    def generate_profile(cls) -> Dict[str, Any]:
        profiler = TransactionProfiler()
        profile = profiler.profile_finances()
        watchdog = FinancialWatchdog()
        wd_report = watchdog.run_full_audit()
        analytics_30d = get_transaction_analytics(days=30)
        spending_velocity = SpendingInsightEngine.get_spending_velocity()
        micro_expenses = SpendingInsightEngine.get_micro_expense_analysis(threshold=10.0, days=30)

        gbp_balance = profile.get("gbp_balance", 0.0)
        runway_days = profile.get("liquid_runway_days", 0.0)
        monthly_burn = profile.get("monthly_burn_estimate", 750.0)
        idle_cash = profile.get("idle_cash", 0.0)

        # 1. 50/30/20 Budget Breakdown
        categories = analytics_30d.get("categories", {})

        needs_total = 0.0
        wants_total = 0.0
        for cat_name, c_data in categories.items():
            tot = c_data.get("total", 0.0)
            if cat_name in ["Groceries & Essentials", "Transport & Commute", "Fees & Charges"]:
                needs_total += tot
            elif cat_name in ["Dining, Pubs & Entertainment", "General Living Spend", "Subscriptions & Software"]:
                wants_total += tot
            # Transfers/Remittances are capital movements, excluded from living 50/30/20

        total_living = max(1.0, needs_total + wants_total)
        needs_pct = round((needs_total / total_living) * 100.0, 1)
        wants_pct = round((wants_total / total_living) * 100.0, 1)

        # 2. Financial Health Score (0 to 100)
        # Component A: Runway & Emergency Buffer (30 pts)
        runway_score = round(30.0 * min(1.0, runway_days / 90.0), 1)

        # Component B: Cash Drag & Yield Efficiency (25 pts)
        # Deduct if large cash balance is sitting idle in 0% current accounts
        if gbp_balance > 0:
            drag_ratio = idle_cash / gbp_balance
            drag_score = round(25.0 * max(0.0, 1.0 - (drag_ratio * 0.7)), 1)
        else:
            drag_score = 15.0

        # Component C: Budget Balance 50/30/20 (25 pts)
        # Standard: 50% Needs, 30% Wants. If wants > 45%, penalize.
        if wants_pct <= 35.0:
            budget_score = 25.0
        elif wants_pct <= 50.0:
            budget_score = 20.0
        elif wants_pct <= 65.0:
            budget_score = 15.0
        else:
            budget_score = 10.0

        # Component D: Commitment Hygiene (20 pts)
        hygiene_score = 20.0
        hikes = wd_report.get("price_hike_alerts", [])
        dups = wd_report.get("duplicate_charge_alerts", [])
        hygiene_score -= len(hikes) * 4.0
        hygiene_score -= len(dups) * 5.0
        hygiene_score = max(5.0, round(hygiene_score, 1))

        total_health_score = round(runway_score + drag_score + budget_score + hygiene_score, 1)

        if total_health_score >= 85:
            grade = "A (Excellent)"
        elif total_health_score >= 70:
            grade = "B (Strong)"
        elif total_health_score >= 55:
            grade = "C (Fair)"
        else:
            grade = "D (Action Required)"

        # 3. Financial Archetype / DNA
        funding_sources = analytics_30d.get("funding_sources", [])
        topup_count = sum(f["count"] for f in funding_sources) if funding_sources else 0

        if runway_days > 180 and topup_count >= 3:
            archetype = "Buffer Builder with High Cognitive Friction"
            archetype_desc = (
                "You maintain an exceptional liquidity runway (>180 days), but manage daily spending via "
                "frequent manual micro top-ups and leave significant idle float in 0% accounts."
            )
            friction_level = "HIGH"
        elif runway_days > 180:
            archetype = "Prudent Capital Accumulator"
            archetype_desc = "Strong runway discipline with consistent liquidity reserves."
            friction_level = "LOW"
        elif wants_pct > 50:
            archetype = "Discretionary Lifestyle Optimizer"
            archetype_desc = "Higher proportion of outflows allocated to dining, entertainment, and flexible services."
            friction_level = "MODERATE"
        else:
            archetype = "Balanced Pragmatist"
            archetype_desc = "Equally balanced between fixed essentials, lifestyle spending, and savings buffer."
            friction_level = "LOW"

        # 4. Action Playbook Cards
        actions = []

        # Action 1: Cash Drag Sweep
        isa_rate = UKMarketRates.TOP_CASH_ISA
        if idle_cash >= 500.0:
            annual_isa_gain = round(idle_cash * isa_rate, 2)
            actions.append({
                "id": "action_sweep_idle_cash",
                "priority": "HIGH",
                "category": "Yield Optimization",
                "title": f"Deploy £{idle_cash:,.2f} Idle Float into 4.87% Flexible ISA",
                "annual_gain_gbp": annual_isa_gain,
                "summary": (
                    f"You have £{idle_cash:,.2f} in 0% current accounts above your 30-day operating buffer. "
                    f"Sweeping this into a Flexible Cash ISA (Trading 212 at {isa_rate*100:.2f}%) yields "
                    f"+£{annual_isa_gain:,.2f}/yr tax-free with same-day liquidity."
                ),
                "action_steps": [
                    f"Open Trading 212 Flexible Cash ISA ({isa_rate*100:.2f}% AER)",
                    f"Transfer £{idle_cash:,.2f} from NatWest / Revolut float",
                    "Maintain £745.50 in current account as working float"
                ]
            })

        # Action 2: Cognitive Friction Elimination
        if topup_count >= 3:
            actions.append({
                "id": "action_standing_order_float",
                "priority": "MEDIUM",
                "category": "Cognitive Automation",
                "title": "Eliminate JIT Top-Up Friction with 1st-of-Month Float",
                "annual_gain_gbp": 0.0,
                "summary": (
                    f"Detected {topup_count} manual micro top-ups this month. Replacing reactive top-ups with a "
                    f"single £{monthly_burn:,.2f} standing order on the 1st of the month saves ~45 minutes of monthly mental friction."
                ),
                "action_steps": [
                    f"Set standing order from main bank to Revolut for £{monthly_burn:,.2f} on 1st of month",
                    "Disable auto-reload push alerts to protect attention"
                ]
            })

        # Action 3: Direct Debit Switch Bounty Arbitrage
        dd_count = profile.get("switch_eligible_direct_debits_count", 0)
        if dd_count >= 2:
            actions.append({
                "id": "action_switch_bounty",
                "priority": "MEDIUM",
                "category": "Bank Switch Bounties",
                "title": "Arbitrage Switch Bounty: Claim £175 Lloyds / £200 NatWest",
                "annual_gain_gbp": 175.0,
                "summary": (
                    f"You have {dd_count} verified active Direct Debits. Using 2 secondary direct debits to switch "
                    "a spare current account unlocks a guaranteed £175 to £200 switch bounty in <10 days."
                ),
                "action_steps": [
                    "Open disposable secondary current account",
                    "Switch 2 small direct debits (e.g. TV Licence / Energy)",
                    "Receive £175–£200 bonus into account"
                ]
            })

        # Action 4: Price Hike & SaaS Hygiene
        if hikes:
            for h in hikes:
                actions.append({
                    "id": f"action_hike_{h['merchant'].lower().replace(' ', '_')}",
                    "priority": "HIGH",
                    "category": "Subscription Hygiene",
                    "title": f"Stealth Price Hike Flagged: {h['merchant']} (+{h['hike_pct']}%)",
                    "annual_gain_gbp": round((h['current_cost'] - h['previous_cost']) * 12, 2),
                    "summary": (
                        f"{h['merchant']} silently increased from £{h['previous_cost']:.2f} to £{h['current_cost']:.2f}. "
                        "1-click generate statutory cancellation notice under the UK Consumer Rights Act 2015."
                    ),
                    "action_steps": [
                        f"Review usage of {h['merchant']}",
                        "Use './f sweep --cancel' to generate legal cancellation notice"
                    ]
                })

        return {
            "health_score": {
                "total": total_health_score,
                "grade": grade,
                "runway_score": runway_score,
                "drag_score": drag_score,
                "budget_score": budget_score,
                "hygiene_score": hygiene_score
            },
            "financial_dna": {
                "archetype": archetype,
                "description": archetype_desc,
                "cognitive_friction_level": friction_level,
                "manual_topup_count_30d": topup_count
            },
            "budget_50_30_20": {
                "needs_total_gbp": round(needs_total, 2),
                "needs_pct": needs_pct,
                "wants_total_gbp": round(wants_total, 2),
                "wants_pct": wants_pct,
                "target_benchmark": "50% Needs / 30% Wants / 20% Savings"
            },
            "spending_velocity": spending_velocity,
            "micro_expenses": micro_expenses,
            "action_cards": actions
        }
