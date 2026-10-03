"""
UK Credit & Underwriter Affordability Engine (FCA MCOB / Bank Underwriting Standard).
Evaluates cash flow affordability, Debt-to-Income (DTI), Uncommitted Monthly Income (UMI),
Buy-Now-Pay-Later (BNPL) exposure, overdraft reliance, and stress-tested mortgage borrowing power.
Also tracks official bureau scores (Experian, Equifax, TransUnion) and executes emergency runway stress tests.
"""

import re
from datetime import datetime, timedelta
from typing import Any, Dict, List

from fiduciary.analysis.profiler import TransactionProfiler
from fiduciary.storage.db import (
    get_all_transactions,
    get_credit_bureau_scores,
    get_transaction_analytics,
)


class CreditAffordabilityEngine:
    """
    Simulates institutional UK mortgage and credit underwriting risk assessments
    using Open Banking cash flow analysis, MCOB affordability guidelines,
    and stress-testing.
    """

    BNPL_KEYWORDS = [
        r"\bklarna\b",
        r"\bclearpay\b",
        r"\bzilch\b",
        r"\blaybuy\b",
        r"\bpaypal pay in 3\b",
        r"\bpaypal credit\b",
        r"\bwonga\b",
        r"\blendable\b",
        r"\bamigo\b",
        r"\bdrafty\b",
        r"\bcreditspring\b",
        r"\bbamboo\b",
        r"\beveryday loans\b",
        r"\b118 118 money\b",
    ]

    BOUNCED_KEYWORDS = [
        r"\bunpaid\b",
        r"\breturned direct debit\b",
        r"\breturned dd\b",
        r"\binsufficient funds\b",
        r"\bbounced\b",
        r"\breturned payment\b",
    ]

    GAMBLING_KEYWORDS = [
        r"\bbet365\b",
        r"\bskybet\b",
        r"\bsky bet\b",
        r"\bpaddy power\b",
        r"\bpaddypower\b",
        r"\bwilliam hill\b",
        r"\bladbrokes\b",
        r"\bbetfair\b",
        r"\bcoral\b",
        r"\bpokerstars\b",
        r"\bnational lottery\b",
        r"\blotto\b",
        r"\bvirgin bet\b",
        r"\b888\b",
        r"\bunibet\b",
    ]

    ATM_KEYWORDS = [
        r"\batm\b",
        r"\bcash withdrawal\b",
        r"\blink atm\b",
        r"\bcash at\b",
    ]

    @classmethod
    def run_full_audit(cls) -> Dict[str, Any]:
        """
        Executes a comprehensive underwriter affordability and borrowing readiness audit.
        """
        profiler = TransactionProfiler()
        profile = profiler.profile_finances()
        analytics_30d = get_transaction_analytics(days=30)
        all_txs = get_all_transactions()
        liquid_cash = profile.get("gbp_balance", 0.0)
        bureau_scores = get_credit_bureau_scores()

        # 1. Income & committed outflows, derived from actual transactions
        monthly_net_income = cls._detect_monthly_income(all_txs, profile)
        estimated_annual_gross = cls._estimate_gross_from_net(monthly_net_income)

        commitments = cls._detect_recurring_commitments(all_txs)
        housing_cost = commitments["housing"]
        utilities_cost = commitments["utilities"]
        committed_debt_spend = commitments["debt"]

        categories = analytics_30d.get("categories", {})
        essentials_spend = sum(
            c.get("total", 0.0) for name, c in categories.items()
            if name in ["Groceries & Essentials", "Transport & Commute", "Fees & Charges"]
        )
        discretionary_spend = sum(
            c.get("total", 0.0) for name, c in categories.items()
            if name in ["Dining, Pubs & Entertainment", "Subscriptions & Software"]
        )
        # Fixed needs = housing + utilities + groceries/transport
        fixed_needs_spend = housing_cost + utilities_cost + essentials_spend

        # Uncommitted Monthly Income (UMI) & Debt-to-Income (DTI)
        # UMI = net income minus housing, utilities, essentials and contractual debt repayments
        total_committed_outflow = fixed_needs_spend + committed_debt_spend
        umi = max(0.0, monthly_net_income - total_committed_outflow)
        umi_pct = round((umi / monthly_net_income) * 100.0, 1)
        dti_pct = round((committed_debt_spend / monthly_net_income) * 100.0, 1)

        # 2. Underwriter Risk Flag Checks
        bnpl_check = cls._check_keywords_in_transactions(all_txs, cls.BNPL_KEYWORDS, days=90)
        bounced_check = cls._check_keywords_in_transactions(all_txs, cls.BOUNCED_KEYWORDS, days=180)
        gambling_check = cls._check_keywords_in_transactions(all_txs, cls.GAMBLING_KEYWORDS, days=30)
        atm_check = cls._check_keywords_in_transactions(all_txs, cls.ATM_KEYWORDS, days=30)

        gambling_spend_30d = gambling_check["total_spend"]
        gambling_pct_income = round((gambling_spend_30d / monthly_net_income) * 100.0, 1)

        atm_spend_30d = atm_check["total_spend"]
        atm_pct_income = round((atm_spend_30d / monthly_net_income) * 100.0, 1)

        # Overdraft Analysis
        overdraft_txs = [
            tx for tx in all_txs
            if any(re.search(pat, f"{tx.get('counterparty_name', '')} {tx.get('description', '')}", re.IGNORECASE)
                   for pat in [r"\boverdraft\b", r"\bunarranged\b"])
        ]
        has_overdraft_fees = len(overdraft_txs) > 0

        # 3. Mortgage Borrowing Capacity (FCA MCOB Standard)
        # Base multiplier: 4.5x gross annual income
        base_mortgage_capacity = round(estimated_annual_gross * 4.5, 2)
        # Stress-testing: deduct committed annual debt * 3.5
        annual_committed_debt = committed_debt_spend * 12.0
        debt_deduction = round(annual_committed_debt * 3.5, 2)
        net_mortgage_capacity = max(0.0, round(base_mortgage_capacity - debt_deduction, 2))

        # Indicative monthly payment at 4.4% 25-yr fixed rate
        indicative_rate = 0.044
        monthly_mortgage_est = cls._calculate_monthly_mortgage(net_mortgage_capacity, rate_annual=indicative_rate, term_years=25)
        # Stress-tested payment at 7.5% (BoE rate + 3% buffer)
        stress_rate = 0.075
        stress_mortgage_est = cls._calculate_monthly_mortgage(net_mortgage_capacity, rate_annual=stress_rate, term_years=25)

        # 4. Fiduciary Borrowing Readiness Score (0 to 100)
        score_breakdown = cls._calculate_readiness_score(
            umi_pct=umi_pct,
            dti_pct=dti_pct,
            bnpl_detected=bnpl_check["detected"],
            bounced_detected=bounced_check["detected"],
            has_overdraft=has_overdraft_fees,
            gambling_pct=gambling_pct_income,
            atm_pct=atm_pct_income,
            electoral_roll=bureau_scores.get("electoral_roll", True),
        )
        total_score = score_breakdown["total_score"]
        tier = score_breakdown["tier"]

        # 5. Financial Stress & Emergency Runway Tester
        monthly_total_burn = max(500.0, fixed_needs_spend + discretionary_spend + committed_debt_spend)
        comfortable_runway_months = round(liquid_cash / monthly_total_burn, 1)
        # Survival runway: cutting all discretionary spend to bare bones
        survival_monthly_burn = max(300.0, fixed_needs_spend + committed_debt_spend)
        survival_runway_months = round(liquid_cash / survival_monthly_burn, 1)

        # Stress Scenarios
        stress_scenarios = [
            {
                "name": "Income Interruption (Zero Income)",
                "description": "Sudden loss of primary salary. How long cash reserves sustain your household.",
                "comfortable_months": comfortable_runway_months,
                "survival_months": survival_runway_months,
                "status": "Resilient (6+ months)" if survival_runway_months >= 6.0 else "Vulnerable (<6 months)",
            },
            {
                "name": "Emergency Capital Shock (£1,500 surprise repair)",
                "description": "Immediate unexpected boiler, dental, or vehicle emergency repair.",
                "remaining_cash": max(0.0, round(liquid_cash - 1500.0, 2)),
                "remaining_runway_months": round(max(0.0, liquid_cash - 1500.0) / survival_monthly_burn, 1),
                "absorbed_comfortably": liquid_cash >= 3000.0,
            },
            {
                "name": "Interest Rate / Housing Shock (+£250/mo increase)",
                "description": "Mortgage renewal or rent spike adding +£250/month to fixed commitments.",
                "new_umi": max(0.0, round(umi - 250.0, 2)),
                "new_dti_pct": round(((committed_debt_spend + 250.0) / monthly_net_income) * 100.0, 1),
                "is_affordable": (umi - 250.0) >= 300.0,
            },
        ]

        # Inflation Erosion Drag
        cpi_inflation_rate = 0.032  # 3.2% UK CPI benchmark
        weighted_cash_yield = 0.015  # estimated blend on current accounts
        annual_inflation_drag_gbp = round(liquid_cash * (cpi_inflation_rate - weighted_cash_yield), 2)
        top_cash_isa_yield = 0.0487  # 4.87% Easy Access Flexible ISA
        real_isa_gain_gbp = round(liquid_cash * (top_cash_isa_yield - weighted_cash_yield), 2)

        # 6. Actionable Underwriter Playbook
        action_plan = cls._generate_action_plan(
            score=total_score,
            bnpl_detected=bnpl_check["detected"],
            bounced_detected=bounced_check["detected"],
            has_overdraft=has_overdraft_fees,
            gambling_pct=gambling_pct_income,
            electoral_roll=bureau_scores.get("electoral_roll", True),
            dti_pct=dti_pct,
        )

        return {
            "timestamp": datetime.now().isoformat(),
            "borrowing_readiness_score": total_score,
            "underwriter_tier": tier["title"],
            "tier_description": tier["description"],
            "tier_badge_color": tier["color"],
            "score_breakdown": score_breakdown["components"],
            "cash_flow_affordability": {
                "monthly_net_income": round(monthly_net_income, 2),
                "estimated_annual_gross": round(estimated_annual_gross, 2),
                "monthly_fixed_needs": round(fixed_needs_spend, 2),
                "monthly_committed_debt": round(committed_debt_spend, 2),
                "uncommitted_monthly_income_umi": round(umi, 2),
                "umi_surplus_pct": umi_pct,
                "contractual_dti_pct": dti_pct,
            },
            "underwriter_risk_flags": {
                "bnpl_detected": bnpl_check["detected"],
                "bnpl_summary": bnpl_check["summary"],
                "bnpl_merchants": bnpl_check["merchants"],
                "bnpl_total_spend": bnpl_check["total_spend"],
                "bounced_direct_debits_detected": bounced_check["detected"],
                "bounced_count": bounced_check["count"],
                "overdraft_reliance": has_overdraft_fees,
                "gambling_spend_30d": round(gambling_spend_30d, 2),
                "gambling_pct_of_income": gambling_pct_income,
                "gambling_risk": "Low / Safe (<1%)" if gambling_pct_income < 1.0 else ("Elevated (1-3%)" if gambling_pct_income <= 3.0 else "High / Alert (>3%)"),
                "atm_cash_withdrawals_30d": round(atm_spend_30d, 2),
                "atm_pct_of_income": atm_pct_income,
                "electoral_roll_verified": bureau_scores.get("electoral_roll", True),
            },
            "mortgage_borrowing_capacity": {
                "standard_multiplier": 4.5,
                "gross_income_baseline": round(base_mortgage_capacity, 2),
                "debt_commitment_deduction": debt_deduction,
                "net_maximum_borrowing_capacity": net_mortgage_capacity,
                "indicative_rate_pct": round(indicative_rate * 100, 2),
                "indicative_monthly_repayment": monthly_mortgage_est,
                "stress_tested_rate_pct": round(stress_rate * 100, 2),
                "stress_tested_monthly_repayment": stress_mortgage_est,
            },
            "emergency_runway_and_stress": {
                "liquid_cash_gbp": round(liquid_cash, 2),
                "comfortable_runway_months": comfortable_runway_months,
                "survival_runway_months": survival_runway_months,
                "scenarios": stress_scenarios,
                "inflation_erosion": {
                    "cpi_rate_pct": round(cpi_inflation_rate * 100, 1),
                    "annual_purchasing_power_loss_gbp": annual_inflation_drag_gbp,
                    "cash_isa_recovery_gain_gbp": real_isa_gain_gbp,
                },
            },
            "bureau_scores": bureau_scores,
            "action_playbook": action_plan,
        }

    HOUSING_PATTERNS = [r"\brent\b", r"\blettings\b", r"\bmortgage\b", r"\bletting\b"]
    UTILITY_PATTERNS = [
        r"\bcouncil tax\b", r"\bbritish gas\b", r"\bthames water\b",
        r"\bwater\b", r"\bbt group\b", r"\bvirgin media\b", r"\boctopus\b", r"\bedf\b",
        r"\be\.?on\b", r"\bsky\b", r"\bgiffgaff\b", r"\bvodafone\b", r"\bee limited\b", r"\bo2\b",
        r"\btv licen[cs]e\b", r"\bbroadband\b", r"\bdual fuel\b", r"\butilit",
    ]
    DEBT_PATTERNS = BNPL_KEYWORDS + [
        r"\bloan\b", r"\bfinance\b", r"\bcredit card\b", r"\bbarclaycard\b", r"\bmbna\b",
        r"\bcapital one\b", r"\bnewday\b", r"\bvanquis\b", r"\bstudent loans? co\b", r"\bslc\b",
    ]
    INCOME_PATTERNS = [r"\bpayroll\b", r"\bsalary\b", r"\bwages?\b", r"\bnet pay\b"]

    @classmethod
    def _matches(cls, text: str, patterns: List[str]) -> bool:
        return any(re.search(p, text, re.IGNORECASE) for p in patterns)

    @classmethod
    def _detect_monthly_income(cls, txs: List[Dict[str, Any]], profile: Dict[str, Any]) -> float:
        """Average monthly net payroll over the last 90 days; falls back to the profiler's salary signal."""
        cutoff = (datetime.now() - timedelta(days=90)).strftime("%Y-%m-%d")
        pay = [
            float(t["amount"]) for t in txs
            if float(t.get("amount", 0.0)) > 0
            and (t.get("booking_date") or "") >= cutoff
            and cls._matches(f"{t.get('counterparty_name', '')} {t.get('description', '')}", cls.INCOME_PATTERNS)
        ]
        if pay:
            return round(sum(pay) / len(pay), 2)
        signal = profile.get("inferred_tax_profile", {}).get("monthly_net_salary_signal", 0.0)
        return max(100.0, float(signal))

    @classmethod
    def _detect_recurring_commitments(cls, txs: List[Dict[str, Any]]) -> Dict[str, float]:
        """
        Finds contractual monthly outflows (merchant seen >=2 times in 90 days) and buckets
        them into housing, utilities and debt repayments using their most recent amount.
        """
        cutoff = (datetime.now() - timedelta(days=90)).strftime("%Y-%m-%d")
        by_merchant: Dict[str, List[Dict[str, Any]]] = {}
        for t in txs:
            if float(t.get("amount", 0.0)) >= 0 or (t.get("booking_date") or "") < cutoff:
                continue
            key = (t.get("counterparty_name") or t.get("description") or "").strip().lower()
            by_merchant.setdefault(key, []).append(t)

        totals = {"housing": 0.0, "utilities": 0.0, "debt": 0.0}
        for items in by_merchant.values():
            if len(items) < 2:
                continue
            latest = max(items, key=lambda x: x.get("booking_date") or "")
            text = f"{latest.get('counterparty_name', '')} {latest.get('description', '')}"
            amount = abs(float(latest["amount"]))
            if cls._matches(text, cls.DEBT_PATTERNS):
                totals["debt"] += amount
            elif cls._matches(text, cls.HOUSING_PATTERNS):
                totals["housing"] += amount
            elif cls._matches(text, cls.UTILITY_PATTERNS):
                totals["utilities"] += amount
        return {k: round(v, 2) for k, v in totals.items()}

    @classmethod
    def _check_keywords_in_transactions(cls, txs: List[Dict[str, Any]], pattern_list: List[str], days: int = 90) -> Dict[str, Any]:
        """Scans recent transactions for underwriting keywords."""
        cutoff_date = (datetime.now() - timedelta(days=days)).strftime("%Y-%m-%d")
        matched_txs = []
        merchants_seen = set()
        total_spend = 0.0

        for tx in txs:
            b_date = tx.get("booking_date", "")
            if b_date and b_date < cutoff_date:
                continue

            text = f"{tx.get('counterparty_name', '')} {tx.get('description', '')}".strip()
            for pat in pattern_list:
                if re.search(pat, text, re.IGNORECASE):
                    matched_txs.append(tx)
                    cp = tx.get("counterparty_name") or text
                    merchants_seen.add(cp)
                    total_spend += abs(float(tx.get("amount", 0.0)))
                    break

        detected = len(matched_txs) > 0
        summary = (
            f"Detected {len(matched_txs)} transactions across {len(merchants_seen)} merchants (£{total_spend:,.2f})"
            if detected
            else "Clean: 0 matching transactions detected"
        )
        return {
            "detected": detected,
            "count": len(matched_txs),
            "total_spend": round(total_spend, 2),
            "merchants": sorted(list(merchants_seen)),
            "summary": summary,
        }

    @classmethod
    def _estimate_gross_from_net(cls, net_monthly: float) -> float:
        """
        Reverse engineers approximate UK gross annual salary from net monthly pay
        assuming standard 2026/27 personal allowance (£12,570), 20% basic tax, 40% higher tax,
        and employee Class 1 National Insurance (8% / 2%).
        """
        annual_net = net_monthly * 12.0
        # If net annual is under £12,570, gross ~= net
        if annual_net <= 12570:
            return annual_net

        # Basic rate band: £12,571 to £50,270 (20% Income Tax + 8% NI = 28% total deductions -> 72% net)
        max_basic_net = 12570 + (37700 * 0.72)  # £39,714 net
        if annual_net <= max_basic_net:
            taxable_net = annual_net - 12570
            gross = 12570 + (taxable_net / 0.72)
            return round(gross, 2)

        # Higher rate band: £50,271 to £125,140 (40% Income Tax + 2% NI = 42% total deductions -> 58% net)
        higher_net = annual_net - max_basic_net
        gross = 50270 + (higher_net / 0.58)
        return round(gross, 2)

    @classmethod
    def _calculate_monthly_mortgage(cls, principal: float, rate_annual: float, term_years: int = 25) -> float:
        """Calculates standard monthly mortgage repayment using amortization formula."""
        if principal <= 0:
            return 0.0
        monthly_rate = rate_annual / 12.0
        n_months = term_years * 12
        payment = principal * (monthly_rate * (1 + monthly_rate) ** n_months) / (((1 + monthly_rate) ** n_months) - 1)
        return round(payment, 2)

    @classmethod
    def _calculate_readiness_score(
        cls,
        umi_pct: float,
        dti_pct: float,
        bnpl_detected: bool,
        bounced_detected: bool,
        has_overdraft: bool,
        gambling_pct: float,
        atm_pct: float,
        electoral_roll: bool,
    ) -> Dict[str, Any]:
        """
        Calculates 4 pillars of underwriter borrowing readiness (25 pts each = 100 max).
        """
        # Pillar 1: Cash Flow & UMI Buffer (25 pts)
        if umi_pct >= 35.0:
            p1 = 25
        elif umi_pct >= 25.0:
            p1 = 20
        elif umi_pct >= 15.0:
            p1 = 15
        elif umi_pct >= 5.0:
            p1 = 8
        else:
            p1 = 0

        # Pillar 2: Leverage & Debt-to-Income (25 pts)
        if dti_pct < 10.0:
            p2 = 25
        elif dti_pct < 20.0:
            p2 = 20
        elif dti_pct < 30.0:
            p2 = 14
        elif dti_pct < 40.0:
            p2 = 6
        else:
            p2 = 0

        # Pillar 3: Credit Hygiene (BNPL, Overdraft, Bounced DDs) (25 pts)
        p3 = 25
        if bnpl_detected:
            p3 -= 8  # Underwriters heavily penalize active BNPL
        if bounced_detected:
            p3 -= 12  # Returned DD is a critical underwriter red flag
        if has_overdraft:
            p3 -= 6
        p3 = max(0, p3)

        # Pillar 4: Account Conduct & Verification (25 pts)
        p4 = 25
        if not electoral_roll:
            p4 -= 8  # Electoral Roll is a primary verification requirement
        if gambling_pct > 3.0:
            p4 -= 10
        elif gambling_pct > 1.0:
            p4 -= 4
        if atm_pct > 15.0:
            p4 -= 5
        p4 = max(0, p4)

        total = p1 + p2 + p3 + p4
        if bnpl_detected or bounced_detected:
            # Active BNPL / returned items disqualify the Tier 1 prime band
            total = min(total, 84)

        if total >= 85:
            tier = {
                "title": "Tier 1: Prime Institutional (Gold Standard)",
                "description": "Exceptional underwriting profile. Minimal leverage, strong cash-flow surplus, clean credit hygiene. Eligible for the most competitive mortgage rates and high-credit limit facilities.",
                "color": "emerald",
            }
        elif total >= 70:
            tier = {
                "title": "Tier 2: Strong Mainstream Approval",
                "description": "Solid credit profile. High probability of approval with standard high-street lenders (Barclays, NatWest, Santander). Minor optimizations available.",
                "color": "blue",
            }
        elif total >= 50:
            tier = {
                "title": "Tier 3: Conditional / Underwriter Review",
                "description": "Moderate risk factors detected (e.g. active BNPL or elevated debt service). An automated mortgage underwriter may request manual wage slips or debt clearance.",
                "color": "yellow",
            }
        else:
            tier = {
                "title": "Tier 4: High Underwriting Risk",
                "description": "Subprime or distressed indicators detected (overdraft dependency, returned items, or high leverage). Significant risk of automated credit rejection.",
                "color": "rose",
            }

        return {
            "total_score": total,
            "tier": tier,
            "components": {
                "cash_flow_umi": {"score": p1, "max": 25, "metric": f"{umi_pct}% surplus UMI"},
                "leverage_dti": {"score": p2, "max": 25, "metric": f"{dti_pct}% DTI ratio"},
                "credit_hygiene": {"score": p3, "max": 25, "metric": "BNPL, Overdraft & DD history"},
                "account_conduct": {"score": p4, "max": 25, "metric": "Electoral roll & low-risk spending"},
            },
        }

    @classmethod
    def _generate_action_plan(
        cls,
        score: int,
        bnpl_detected: bool,
        bounced_detected: bool,
        has_overdraft: bool,
        gambling_pct: float,
        electoral_roll: bool,
        dti_pct: float,
    ) -> List[Dict[str, str]]:
        """Generates prioritized fiduciary action cards to maximize borrowing power."""
        cards = []

        if not electoral_roll:
            cards.append({
                "priority": "HIGH",
                "title": "Register on the UK Electoral Roll",
                "action": "Ensure you are registered to vote at your current residential address. This is the single fastest way to boost credit scores (+30–50 pts) as it instantly satisfies CRA identity verification.",
            })

        if bnpl_detected:
            cards.append({
                "priority": "HIGH",
                "title": "Institute a 90-Day BNPL Cooling-Off Period",
                "action": "Cease all Klarna, Clearpay, and PayPal Pay in 3 purchases. Mortgage underwriters frequently view active BNPL as a sign of micro-cash-flow distress.",
            })

        if bounced_detected:
            cards.append({
                "priority": "CRITICAL",
                "title": "Zero Bounced Direct Debits Policy",
                "action": "Maintain an automated cash cushion (£500+) in your current account to prevent returned direct debits, which can trigger automatic underwriter declines.",
            })

        if has_overdraft:
            cards.append({
                "priority": "MEDIUM",
                "title": "Eliminate Overdraft Dip Zone",
                "action": "Switch to an automated Standing Order sweep that transfers reserve funds back into your current account before balance reaches £0.",
            })

        if gambling_pct > 2.0:
            cards.append({
                "priority": "HIGH",
                "title": "Curtail Speculative Outflows (<1% of Net Income)",
                "action": "Keep gambling and lottery spend strictly under 1% of net income. Many UK lenders flag any sustained gambling over 3% as high-risk behavior.",
            })

        if dti_pct > 25.0:
            cards.append({
                "priority": "MEDIUM",
                "title": "Target Unsecured Debt Amortisation",
                "action": f"Current DTI is {dti_pct}%. Paying down personal loans or credit card balances below 20% DTI can increase your maximum mortgage borrowing capacity by £20,000–£50,000.",
            })

        if not cards:
            cards.append({
                "priority": "LOW",
                "title": "Maintain Pristine Account Conduct",
                "action": "Your underwriting profile is in the top tier. Keep credit card utilization below 25% on statement closing dates to lock in optimal mortgage rates.",
            })

        return cards
