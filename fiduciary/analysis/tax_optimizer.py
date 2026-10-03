from typing import Any, Dict


class UKTaxOptimizer:
    """
    UK Wealth & Tax Optimization Engine.
    Models marginal income tax bands, the notorious 60% tax trap,
    pension tax relief, Personal Savings Allowance (PSA), Capital Gains exemption,
    and High Income Child Benefit Charge (HICBC).
    """

    # 2025/2026 UK Tax Thresholds (Standard England/Wales/NI)
    PERSONAL_ALLOWANCE = 12570.0
    BASIC_RATE_LIMIT = 50270.0
    HIGHER_RATE_LIMIT = 125140.0

    # Allowances
    ANNUAL_ISA_ALLOWANCE = 20000.0
    LISA_ANNUAL_LIMIT = 4000.0
    LISA_BONUS_RATE = 0.25  # 25% government top-up
    PENSION_ANNUAL_ALLOWANCE = 60000.0
    CGT_ANNUAL_EXEMPTION = 3000.0

    # HICBC Thresholds
    HICBC_START = 60000.0
    HICBC_END = 80000.0

    @classmethod
    def get_tax_band(cls, gross_income: float) -> Dict[str, Any]:
        """Returns tax band and marginal income tax rate."""
        if gross_income > cls.HIGHER_RATE_LIMIT:
            return {
                "band_name": "Additional Rate (45%)",
                "marginal_rate": 0.45,
                "psa_limit": 0.0,
                "in_60_percent_trap": False
            }
        elif gross_income > 100000.0:
            return {
                "band_name": "60% Personal Allowance Taper Trap",
                "marginal_rate": 0.60,
                "psa_limit": 500.0,
                "in_60_percent_trap": True
            }
        elif gross_income > cls.BASIC_RATE_LIMIT:
            return {
                "band_name": "Higher Rate (40%)",
                "marginal_rate": 0.40,
                "psa_limit": 500.0,
                "in_60_percent_trap": False
            }
        elif gross_income > cls.PERSONAL_ALLOWANCE:
            return {
                "band_name": "Basic Rate (20%)",
                "marginal_rate": 0.20,
                "psa_limit": 1000.0,
                "in_60_percent_trap": False
            }
        else:
            return {
                "band_name": "Personal Allowance (0%)",
                "marginal_rate": 0.0,
                "psa_limit": 1000.0,
                "in_60_percent_trap": False
            }

    @classmethod
    def calculate_sipp_tax_relief(cls, gross_income: float, contribution: float) -> Dict[str, Any]:
        """
        Calculates immediate net cost and tax relief on pension contributions.
        Basic rate relief (20%) added at source into SIPP,
        higher/additional rate reclaimed via self-assessment.
        """
        tax_info = cls.get_tax_band(gross_income)
        marginal_rate = tax_info["marginal_rate"]

        # Basic rate relief (20% added automatically)
        net_paid = contribution * 0.80
        basic_relief = contribution * 0.20

        # Additional relief to claim back
        higher_relief = 0.0
        if marginal_rate == 0.60:
            # 60% trap: basic 20% in pension + 40% tax refund in cash
            higher_relief = contribution * 0.40
        elif marginal_rate == 0.40:
            higher_relief = contribution * 0.20
        elif marginal_rate == 0.45:
            higher_relief = contribution * 0.25

        total_tax_saving = basic_relief + higher_relief
        effective_cost = net_paid - higher_relief

        return {
            "gross_contribution": round(contribution, 2),
            "upfront_cash_paid": round(net_paid, 2),
            "basic_relief_at_source": round(basic_relief, 2),
            "higher_relief_to_reclaim": round(higher_relief, 2),
            "total_government_topup_and_relief": round(total_tax_saving, 2),
            "effective_net_cost": round(effective_cost, 2),
            "effective_roi_instant": round((total_tax_saving / max(1.0, effective_cost)) * 100, 1)
        }

    @classmethod
    def audit_60_percent_trap(cls, gross_income: float) -> Dict[str, Any]:
        """
        Audits exposure to the £100,000 - £125,140 personal allowance tapering cliff.
        """
        if gross_income <= 100000.0:
            return {
                "is_affected": False,
                "excess_above_100k": 0.0,
                "tax_drag_gbp": 0.0,
                "recommended_pension_sacrifice": 0.0,
                "message": "Income is below £100k; Personal Allowance is fully intact (£12,570)."
            }

        excess = min(gross_income - 100000.0, 25140.0)
        # Lost personal allowance = £1 for every £2
        lost_allowance = excess / 2.0
        # Tax drag: 40% on excess + 20% on lost allowance = 60%
        tax_drag = excess * 0.60

        return {
            "is_affected": True,
            "gross_income": gross_income,
            "excess_above_100k": round(excess, 2),
            "lost_personal_allowance": round(lost_allowance, 2),
            "tax_drag_gbp": round(tax_drag, 2),
            "recommended_pension_sacrifice": round(excess, 2),
            "net_cash_saved_via_sacrifice": round(tax_drag, 2),
            "message": (
                f"⚠️ £{excess:,.2f} of your income sits in the 60% tax trap. "
                f"Sacrificing £{excess:,.2f} into your pension or SIPP restores £{lost_allowance:,.2f} "
                f"of tax-free personal allowance and saves £{tax_drag:,.2f} in pure tax."
            )
        }

    @classmethod
    def calculate_psa_drag(cls, cash_balance: float, interest_rate: float, gross_income: float) -> Dict[str, Any]:
        """
        Computes tax drag on interest when personal savings allowance is breached.
        """
        tax_info = cls.get_tax_band(gross_income)
        psa = tax_info["psa_limit"]
        marginal_rate = tax_info["marginal_rate"]

        annual_interest = cash_balance * interest_rate
        taxable_interest = max(0.0, annual_interest - psa)
        tax_drag = taxable_interest * (marginal_rate if marginal_rate > 0 else 0.20)
        net_interest = annual_interest - tax_drag

        return {
            "cash_balance": round(cash_balance, 2),
            "interest_rate_pct": round(interest_rate * 100, 2),
            "annual_gross_interest": round(annual_interest, 2),
            "personal_savings_allowance": psa,
            "taxable_interest": round(taxable_interest, 2),
            "tax_drag_gbp": round(tax_drag, 2),
            "net_interest_gbp": round(net_interest, 2),
            "cash_isa_advantage_gbp": round(tax_drag, 2),
            "recommendation": (
                f"Move £{min(cash_balance, cls.ANNUAL_ISA_ALLOWANCE):,.2f} into a Flexible Cash ISA to protect £{tax_drag:,.2f}/yr from HMRC tax drag."
                if tax_drag > 20.0 else "Interest is currently sheltered within your Personal Savings Allowance."
            )
        }

    @classmethod
    def full_tax_wealth_audit(cls, gross_income: float, liquid_cash: float, current_savings_rate: float = 0.0485) -> Dict[str, Any]:
        """Runs comprehensive UK tax and wealth optimization analysis."""
        band = cls.get_tax_band(gross_income)
        sipp_1k = cls.calculate_sipp_tax_relief(gross_income, 1000.0)
        trap_60k = cls.audit_60_percent_trap(gross_income)
        psa_drag = cls.calculate_psa_drag(liquid_cash, current_savings_rate, gross_income)

        return {
            "gross_income": gross_income,
            "tax_band": band["band_name"],
            "marginal_rate_pct": int(band["marginal_rate"] * 100),
            "psa_limit_gbp": band["psa_limit"],
            "sipp_relief_example": sipp_1k,
            "trap_60_percent": trap_60k,
            "psa_cash_drag": psa_drag,
            "annual_isa_allowance": cls.ANNUAL_ISA_ALLOWANCE,
            "pension_annual_allowance": cls.PENSION_ANNUAL_ALLOWANCE,
            "cgt_exemption": cls.CGT_ANNUAL_EXEMPTION
        }
