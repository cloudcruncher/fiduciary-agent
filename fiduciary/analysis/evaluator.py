from typing import Any, Dict

from fiduciary.analysis.market_rates import UKMarketRates
from fiduciary.storage.db import get_all_accounts, get_net_worth_breakdown, get_transaction_analytics


class FinancialEvaluator:
    def __init__(self):
        self.market = UKMarketRates()

    def evaluate_financial_state(self) -> Dict[str, Any]:
        accounts = get_all_accounts()
        analytics_30d = get_transaction_analytics(days=30)
        net_worth_data = get_net_worth_breakdown()

        # 1. Tally balances by currency
        balances_by_currency: Dict[str, float] = {}
        for acc in accounts:
            curr = acc.get("currency", "GBP")
            bal = float(acc.get("current_balance", 0.0))
            balances_by_currency[curr] = balances_by_currency.get(curr, 0.0) + bal

        gbp_balance = balances_by_currency.get("GBP", 0.0)

        # 2. 30-Day Normalized Burn Rate & Daily Burn
        monthly_burn = analytics_30d.get("normalized_monthly_burn", 0.0)
        daily_burn = analytics_30d.get("daily_burn_rate", 0.0)
        if monthly_burn <= 50.0:
            monthly_burn = 1500.0
            daily_burn = 50.0

        liquid_runway_days = round(gbp_balance / daily_burn, 1) if daily_burn > 0 else 999.0
        recommended_emergency_buffer = round(monthly_burn * 3, 2)
        operating_cash_target = round(monthly_burn, 2)
        idle_cash = max(0.0, gbp_balance - operating_cash_target)

        # 3. Interest Drag & Opportunity Calculations
        top_yield = UKMarketRates.TOP_EASY_ACCESS_SAVINGS
        isa_yield = UKMarketRates.TOP_CASH_ISA
        wise_asset_yield = UKMarketRates.WISE_INTEREST_GBP_YIELD

        annual_loss_vs_top_savings = round(idle_cash * top_yield, 2)
        annual_loss_vs_cash_isa = round(idle_cash * isa_yield, 2)
        annual_gain_if_wise_interest = round(idle_cash * wise_asset_yield, 2)

        return {
            "total_accounts": len(accounts),
            "balances_by_currency": balances_by_currency,
            "gbp_total_balance": round(gbp_balance, 2),
            "estimated_monthly_burn": round(monthly_burn, 2),
            "daily_burn_rate": round(daily_burn, 2),
            "liquid_runway_days": liquid_runway_days,
            "recommended_emergency_buffer": recommended_emergency_buffer,
            "operating_cash_target": operating_cash_target,
            "idle_cash_gbp": round(idle_cash, 2),
            "annual_cash_drag_vs_top_savings_gbp": annual_loss_vs_top_savings,
            "annual_tax_free_gain_vs_isa_gbp": annual_loss_vs_cash_isa,
            "annual_gain_via_wise_interest_gbp": annual_gain_if_wise_interest,
            "accounts_detail": accounts,
            "transaction_analytics": analytics_30d,
            "net_worth": net_worth_data
        }
