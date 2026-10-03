from datetime import datetime
from typing import Any, Dict, Optional

from fiduciary.analysis.profiler import TransactionProfiler


class SmartAutomationEngine:
    """
    Automates fiduciary execution:
    1. Smart Sweeper: Optimizes cash surplus vs monthly operational buffer.
    2. Standing Order Float Architect: Replaces erratic micro-funding.
    3. Subscription Cancellation Assistant: Produces statutory UK cancellation notices.
    """

    def audit_sweeping_potential(self) -> Dict[str, Any]:
        """Calculates exact capital ready to sweep out of 0% accounts into tax-free yield."""
        profiler = TransactionProfiler()
        profile = profiler.profile_finances()

        gbp_cash = profile.get("gbp_balance", 0.0)
        monthly_burn = profile.get("monthly_burn_estimate", 560.0)
        target_operating_float = round(monthly_burn * 1.10, 2)  # Monthly burn + 10% cushion

        excess_cash = max(0.0, gbp_cash - target_operating_float)
        shortfall = max(0.0, target_operating_float - gbp_cash)

        # Destination recommendations
        best_destinations = [
            {
                "provider": "Trading 212",
                "product": "Flexible Cash ISA",
                "yield_aer": 4.87,
                "tax_treatment": "100% Tax-Free",
                "liquidity": "Instant access (replace in same tax year)",
                "link": "https://www.trading212.com/isa"
            },
            {
                "provider": "Wise (In-App)",
                "product": "Wise Interest (BlackRock Sterling Fund)",
                "yield_aer": 4.60,
                "tax_treatment": "Taxable after Personal Savings Allowance",
                "liquidity": "Instant (in-app card spendable)",
                "link": "https://wise.com/gb/interest/"
            }
        ]

        if excess_cash > 50.0:
            status = "SWEEP_RECOMMENDED"
            action_memo = (
                f"You have £{excess_cash:,.2f} in excess idle cash above your required operating float "
                f"(£{target_operating_float:,.2f}). Sweeping this into a 4.87% Flexible Cash ISA earns "
                f"+£{excess_cash * 0.0487:,.2f}/yr tax-free with zero lockup."
            )
        elif shortfall > 0:
            status = "FLOAT_DEFICIT"
            action_memo = (
                f"Your liquid cash (£{gbp_cash:,.2f}) is below your safe monthly operating float "
                f"(£{target_operating_float:,.2f}). You face a £{shortfall:,.2f} liquidity deficit before month-end."
            )
        else:
            status = "BALANCED"
            action_memo = "Your current account is precisely balanced with your required monthly operating float."

        return {
            "current_liquid_cash": gbp_cash,
            "monthly_burn_rate": monthly_burn,
            "target_operating_float": target_operating_float,
            "excess_cash_to_sweep": round(excess_cash, 2),
            "liquidity_deficit": round(shortfall, 2),
            "status": status,
            "action_memo": action_memo,
            "recommended_destinations": best_destinations
        }

    def generate_standing_order_plan(self) -> Dict[str, Any]:
        """Produces automated standing order rules to end manual £100 micro top-ups."""
        profiler = TransactionProfiler()
        profile = profiler.profile_finances()
        monthly_burn = profile.get("monthly_burn_estimate", 560.0)
        float_target = round(monthly_burn * 1.15, -1)  # Rounded to nearest £10 with buffer

        funding_sources = profile.get("transaction_30d_summary", {}).get("funding_sources", [])
        primary_source = funding_sources[0]["source"] if funding_sources else "Primary Bank Account"

        return {
            "primary_source": primary_source,
            "target_amount": float_target,
            "frequency": "Monthly on the 1st",
            "reference": "OPERATING FLOAT",
            "rationale": (
                f"Setting an automated Standing Order of £{float_target:,.2f} on the 1st of every month from "
                f"'{primary_source}' replaces multiple reactive micro top-ups with predictable, calm cash flow."
            ),
            "instructions": [
                f"Log into '{primary_source}' online or mobile app.",
                "Select 'Pay & Transfer' -> 'Set up Standing Order'.",
                f"Set amount to £{float_target:,.2f}.",
                "Set first payment date to the 1st of next month, repeating monthly.",
                "Set payment reference to: FLOAT"
            ]
        }

    def generate_cancellation_letter(self, service_name: str, monthly_cost: float, account_reference: Optional[str] = None) -> Dict[str, Any]:
        """Generates formal statutory UK Consumer Rights contract cancellation notice."""
        today = datetime.now().strftime("%d %B %Y")
        ref_line = f"Account / Email Reference: {account_reference}" if account_reference else "Account Reference: [Your Account Email / Username]"

        email_subject = f"Notice of Immediate Cancellation & Direct Debit Revocation - {service_name}"
        email_body = f"""Dear {service_name} Customer Support / Billing Team,

Date: {today}
Subject: {email_subject}
{ref_line}

I am writing to provide formal notice of cancellation for my subscription / recurring billing with {service_name} (£{monthly_cost:.2f}/month), effective immediately.

In accordance with UK Consumer Contracts Regulations and standard terms of service:
1. Please terminate all recurring billing and active subscriptions associated with my account.
2. Revoke any recurring card payment authorizations or continuous payment authorities (CPA).
3. Confirm in writing via reply to this email that no further charges will be levied.

If any final invoice or pro-rata balance is outstanding, please provide an itemized statement.

Thank you for your prompt confirmation.

Yours sincerely,
[Your Full Name]
"""
        return {
            "service_name": service_name,
            "monthly_cost": monthly_cost,
            "email_subject": email_subject,
            "email_body": email_body,
            "advice": "Send this to support or paste into the provider's cancellation contact form. Also cancel any associated continuous payment authority in your banking app if possible."
        }
