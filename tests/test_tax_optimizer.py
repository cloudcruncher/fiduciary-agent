from fiduciary.analysis.tax_optimizer import UKTaxOptimizer


def test_tax_bands():
    assert UKTaxOptimizer.get_tax_band(10000.0)["marginal_rate"] == 0.0
    assert UKTaxOptimizer.get_tax_band(35000.0)["marginal_rate"] == 0.20
    assert UKTaxOptimizer.get_tax_band(75000.0)["marginal_rate"] == 0.40
    assert UKTaxOptimizer.get_tax_band(110000.0)["marginal_rate"] == 0.60
    assert UKTaxOptimizer.get_tax_band(150000.0)["marginal_rate"] == 0.45

def test_60_percent_trap_audit():
    # Below 100k
    res_under = UKTaxOptimizer.audit_60_percent_trap(85000.0)
    assert res_under["is_affected"] is False
    assert res_under["tax_drag_gbp"] == 0.0

    # In 60% trap (£115,000)
    res_trap = UKTaxOptimizer.audit_60_percent_trap(115000.0)
    assert res_trap["is_affected"] is True
    assert res_trap["excess_above_100k"] == 15000.0
    assert res_trap["lost_personal_allowance"] == 7500.0
    assert res_trap["tax_drag_gbp"] == 9000.0
    assert res_trap["recommended_pension_sacrifice"] == 15000.0

def test_sipp_tax_relief():
    # Basic rate (20%)
    res_basic = UKTaxOptimizer.calculate_sipp_tax_relief(40000.0, 1000.0)
    assert res_basic["upfront_cash_paid"] == 800.0
    assert res_basic["basic_relief_at_source"] == 200.0
    assert res_basic["higher_relief_to_reclaim"] == 0.0
    assert res_basic["effective_net_cost"] == 800.0

    # Higher rate (40%)
    res_higher = UKTaxOptimizer.calculate_sipp_tax_relief(70000.0, 1000.0)
    assert res_higher["upfront_cash_paid"] == 800.0
    assert res_higher["basic_relief_at_source"] == 200.0
    assert res_higher["higher_relief_to_reclaim"] == 200.0
    assert res_higher["effective_net_cost"] == 600.0
    assert res_higher["effective_roi_instant"] == 66.7

    # 60% Trap
    res_60 = UKTaxOptimizer.calculate_sipp_tax_relief(115000.0, 1000.0)
    assert res_60["effective_net_cost"] == 400.0
    assert res_60["effective_roi_instant"] == 150.0

def test_psa_drag():
    # Higher rate with £20k cash earning 5% = £1,000 interest (PSA is £500)
    res = UKTaxOptimizer.calculate_psa_drag(cash_balance=20000.0, interest_rate=0.05, gross_income=70000.0)
    assert res["annual_gross_interest"] == 1000.0
    assert res["personal_savings_allowance"] == 500.0
    assert res["taxable_interest"] == 500.0
    assert res["tax_drag_gbp"] == 200.0  # 40% on £500
