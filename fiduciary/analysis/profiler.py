import re
from collections import defaultdict
from typing import Any, Dict

from fiduciary.storage.db import (
    get_all_accounts,
    get_recent_transactions,
    get_transaction_analytics,
)


class TransactionProfiler:
    """
    Analyzes read-only daily banking transactions to deduce:
    - 30-day granular spending, inflows, and net burn
    - Exact liquid runway in days based on current balances
    - Inflow / funding patterns (e.g. salary vs manual micro top-ups)
    - Inferred UK income tax bracket & Personal Savings Allowance
    - Fixed commitments (Direct Debits, Subscriptions)
    - Re-switchable Direct Debits (for bank switch bonuses)
    - Debit card cashback opportunities (Chase UK 1%)
    - Debt detection (credit card / loan interest bleed)
    """

    KNOWN_DEBT_KEYWORDS = ["barclaycard", "amex", "american express", "capital one", "mbna", "loan", "klarna", "clearpay"]
    KNOWN_BILLS_KEYWORDS = ["council tax", "energy", "british gas", "octopus", "edf", "water", "thames water", "broadband", "virgin media", "bt", "ee", "vodafone", "spotify", "netflix", "gym", "anthropic", "claude"]

    def profile_finances(self) -> Dict[str, Any]:
        accounts = get_all_accounts()
        tx_stats_30d = get_transaction_analytics(days=30)
        recent_90d = get_recent_transactions(days=90)

        # 1. Total Capital by Currency
        currency_totals = defaultdict(float)
        for acc in accounts:
            curr = acc.get("currency", "GBP")
            currency_totals[curr] += float(acc.get("current_balance", 0.0))

        gbp_balance = currency_totals.get("GBP", 0.0)

        # 2. Burn Rate & Runway Analysis
        daily_burn = tx_stats_30d.get("daily_burn_rate", 0.0)
        monthly_burn = tx_stats_30d.get("normalized_monthly_burn", 0.0)
        if monthly_burn <= 50.0:
            # Fallback to realistic UK living cost baseline if no recent spend
            monthly_burn = 1500.0
            daily_burn = 50.0

        liquid_runway_days = round(gbp_balance / daily_burn, 1) if daily_burn > 0 else 999.0
        three_month_emergency_buffer = round(monthly_burn * 3, 2)
        six_month_emergency_buffer = round(monthly_burn * 6, 2)
        idle_cash = max(0.0, gbp_balance - monthly_burn)

        # 3. Direct Debits & Debt Signals (from 90-day transactions)
        counterparty_frequency = defaultdict(int)
        counterparty_amounts = defaultdict(list)
        debt_signals = []
        recurring_direct_debits = []
        counterparty_categories = {}

        for tx in recent_90d:
            amt = float(tx.get("amount", 0.0))
            name = (tx.get("counterparty_name", "") or tx.get("description", "")).lower()
            cat = tx.get("category", "")
            if name:
                counterparty_categories[name] = cat

            if amt < 0:
                counterparty_frequency[name] += 1
                counterparty_amounts[name].append(abs(amt))

                if any(re.search(r'\b' + re.escape(k) + r'\b', name) for k in self.KNOWN_DEBT_KEYWORDS):
                    debt_signals.append({
                        "name": tx.get("counterparty_name") or tx.get("description"),
                        "amount": abs(amt),
                        "date": tx.get("booking_date")
                    })

        EXCLUDED_CATEGORIES = [
            "Transfers & Remittance",
            "Debt Repayment",
            "Fees & Charges",
            "Income & Top-ups",
            "Income / Inflows",
            "Refunds",
            "Dining, Pubs & Entertainment",
            "Groceries & Essentials",
            "Transport & Commute",
        ]

        for name, count in counterparty_frequency.items():
            cat = counterparty_categories.get(name, "")
            if cat in EXCLUDED_CATEGORIES:
                continue
            if any(k in name for k in ["transfer", "remittance", "topup", "top up", "cheddar", "wise", "revolut"]):
                continue

            matches_keyword = any(re.search(r'\b' + re.escape(k) + r'\b', name) for k in self.KNOWN_BILLS_KEYWORDS)
            if count >= 1 and (matches_keyword or cat == "Subscriptions & Software"):
                avg_amt = sum(counterparty_amounts[name]) / len(counterparty_amounts[name])
                recurring_direct_debits.append({
                    "merchant": name.title(),
                    "frequency": count,
                    "avg_amount": round(avg_amt, 2)
                })

        # 4. Income & Tax Bracket Inference
        salary_estimate_monthly = 0.0
        for tx in recent_90d:
            amt = float(tx.get("amount", 0.0))
            if amt > 1000.0:
                salary_estimate_monthly = max(salary_estimate_monthly, amt)

        # Inbound funding pattern
        funding_sources = tx_stats_30d.get("funding_sources", [])
        if funding_sources:
            total_topups = sum(f["total"] for f in funding_sources)
            count_topups = sum(f["count"] for f in funding_sources)
            primary_source = funding_sources[0]["source"]
            funding_behavior = (
                f"Just-in-time micro-funding: {count_topups} manual top-ups totaling £{total_topups:,.2f} "
                f"from '{primary_source}' to fund discretionary card spending."
            )
        elif salary_estimate_monthly > 0:
            funding_behavior = f"Regular payroll detected (~£{salary_estimate_monthly:,.2f}/mo)."
        else:
            funding_behavior = "Variable / irregular account inflows."

        # Tax Bracket
        if salary_estimate_monthly > 6500:
            tax_band = "Additional Rate (45%)"
            personal_savings_allowance = 0
            tax_rate = 0.45
        elif salary_estimate_monthly > 3500:
            tax_band = "Higher Rate (40%)"
            personal_savings_allowance = 500
            tax_rate = 0.40
        else:
            tax_band = "Basic Rate (20%)"
            personal_savings_allowance = 1000
            tax_rate = 0.20

        # 5. Cashback Opportunity (1% on Card Spend via Chase UK)
        card_spend_30d = tx_stats_30d.get("card_spend_total", 0.0)
        annual_cashback_potential = round(card_spend_30d * 12 * 0.01, 2)

        return {
            "total_accounts": len(accounts),
            "currency_balances": dict(currency_totals),
            "gbp_balance": round(gbp_balance, 2),
            "daily_burn_rate": daily_burn,
            "liquid_runway_days": liquid_runway_days,
            "monthly_burn_estimate": monthly_burn,
            "emergency_buffer_target": three_month_emergency_buffer,
            "six_month_buffer_target": six_month_emergency_buffer,
            "idle_cash": round(idle_cash, 2),
            "funding_behavior": funding_behavior,
            "annual_cashback_potential": annual_cashback_potential,
            "transaction_30d_summary": tx_stats_30d,
            "inferred_tax_profile": {
                "tax_band": tax_band,
                "marginal_tax_rate": tax_rate,
                "personal_savings_allowance_gbp": personal_savings_allowance,
                "monthly_net_salary_signal": round(salary_estimate_monthly, 2)
            },
            "recurring_direct_debits": recurring_direct_debits,
            "switch_eligible_direct_debits_count": len(recurring_direct_debits),
            "debt_signals": debt_signals
        }
