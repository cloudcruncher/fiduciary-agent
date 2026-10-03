from fiduciary.agent.automation import SmartAutomationEngine


def test_cancellation_letter():
    engine = SmartAutomationEngine()
    letter = engine.generate_cancellation_letter(
        service_name="Adobe Creative Cloud",
        monthly_cost=49.99,
        account_reference="creative@example.com"
    )
    assert "Notice of Immediate Cancellation" in letter["email_subject"]
    assert "Adobe Creative Cloud" in letter["email_body"]
    assert "£49.99" in letter["email_body"]
    assert "creative@example.com" in letter["email_body"]

def test_sweeping_and_standing_order():
    engine = SmartAutomationEngine()
    sweep = engine.audit_sweeping_potential()
    assert "status" in sweep
    assert "current_liquid_cash" in sweep

    so = engine.generate_standing_order_plan()
    assert so["target_amount"] > 0
    assert len(so["instructions"]) > 0


def test_cli_help_formatting():
    from fiduciary.cli import build_parser
    parser = build_parser()
    help_str = parser.format_help()
    assert "Personal Fiduciary Financial Harness" in help_str
    assert "60% trap audit" in help_str
