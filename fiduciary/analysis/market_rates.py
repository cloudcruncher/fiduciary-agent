from typing import Any, Dict


class UKMarketRates:
    """
    UK Market Benchmarks and Top-of-Market Savings / Cash ISA Yields.
    Can be dynamically fetched or updated with live market rates.
    """
    BOE_BASE_RATE = 0.0500  # 5.00% Bank of England Base Rate
    TOP_EASY_ACCESS_SAVINGS = 0.0485  # 4.85% AER (e.g. Chip, Trading 212)
    TOP_CASH_ISA = 0.0487  # 4.87% AER (Tax-free yield)
    TOP_REGULAR_SAVER = 0.0700  # 7.00% AER (First Direct / Nationwide)

    # Wise specific: Wise offers "Interest" (BlackRock Money Market Fund) vs "Cash"
    WISE_INTEREST_GBP_YIELD = 0.0460  # ~4.60% variable yield when enabled in Wise app
    WISE_DEFAULT_CASH_YIELD = 0.0000  # Default un-invested cash balance in Wise

    @classmethod
    def get_benchmarks(cls) -> Dict[str, Any]:
        return {
            "boe_base_rate_pct": cls.BOE_BASE_RATE * 100,
            "top_easy_access_pct": cls.TOP_EASY_ACCESS_SAVINGS * 100,
            "top_cash_isa_pct": cls.TOP_CASH_ISA * 100,
            "top_regular_saver_pct": cls.TOP_REGULAR_SAVER * 100,
            "wise_interest_gbp_pct": cls.WISE_INTEREST_GBP_YIELD * 100,
            "annual_isa_allowance_gbp": 20000,
            "personal_savings_allowance_basic_gbp": 1000,
            "personal_savings_allowance_higher_gbp": 500,
        }
