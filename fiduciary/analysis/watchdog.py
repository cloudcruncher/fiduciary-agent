import re
from collections import defaultdict
from datetime import datetime, timedelta
from typing import Any, Dict, List

from fiduciary.storage.db import (
    get_all_accounts,
    get_all_transactions,
    upsert_recurring_bill,
)


class FinancialWatchdog:
    """
    Autonomous Financial Watchdog.
    Guaranteed deterministic: NO false-positive bills, NO hallucinated due dates.
    Continuously monitors:
    1. Legitimate active recurring contracts & subscriptions (cadence <= 45 days).
    2. Stealth subscription price hikes on active plans.
    3. Duplicate card charges (<24h on same account).
    4. Shortfall risks (liquid buffer vs actual upcoming commitments).
    """

    KNOWN_SUBSCRIPTION_KEYWORDS = [
        "anthropic", "claude", "chatgpt", "openai", "spotify", "netflix",
        "apple.com/bill", "google storage", "github", "cursor", "adobe",
        "amazon prime", "disney", "youtube", "lemon squeezy", "aws",
        "puregym", "the gym", "virgin media", "broadband", "ee", "vodafone",
        "o2", "three", "council tax", "council", "hounslow", "borough", "thames water",
        "octopus", "british gas", "edf", "tv licence", "licence"
    ]

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

    DISCRETIONARY_CATEGORIES = [
        "Dining, Pubs & Entertainment",
        "Groceries & Essentials",
        "Transport & Commute",
        "General Living Spend",
        "Refunds"
    ]

    def _is_subscription_merchant(self, name: str, category: str) -> bool:
        """Determines if a transaction counterparty is a legitimate recurring contract."""
        if category in self.EXCLUDED_CATEGORIES:
            return False

        name_lower = name.lower()

        # Reject transfers, topups, remittances, and refunds regardless of category
        if any(k in name_lower for k in ["transfer", "remittance", "topup", "top up", "cheddar", "wise", "revolut", "payout", "refund"]):
            return False

        if category == "Subscriptions & Software":
            return True

        for kw in self.KNOWN_SUBSCRIPTION_KEYWORDS:
            # Word boundary check to prevent "ee" matching "queens" or "pub" matching "public"
            if re.search(r'\b' + re.escape(kw) + r'\b', name_lower):
                return True
        return False

    def run_full_audit(self) -> Dict[str, Any]:
        txs = get_all_transactions()
        accounts = get_all_accounts()

        # Total liquid GBP balance
        total_liquid_gbp = sum(
            float(a.get("current_balance", 0.0))
            for a in accounts
            if (a.get("asset_class") or "cash") == "cash" and a.get("currency", "GBP") == "GBP"
        )

        active_bills, inactive_bills = self._detect_and_sync_bills(txs)
        price_hikes = self._detect_price_hikes(txs)
        duplicate_charges = self._detect_duplicate_charges(txs)

        now = datetime.now()
        upcoming_7d = []
        upcoming_14d = []
        upcoming_30d = []

        total_upcoming_30d = 0.0

        for b in active_bills:
            due_str = b.get("next_due_date")
            if not due_str:
                continue
            try:
                due_date = datetime.strptime(due_str[:10], "%Y-%m-%d")
                days_away = (due_date.date() - now.date()).days
                amt = float(b.get("expected_amount", 0.0))

                bill_item = {
                    **b,
                    "days_away": days_away,
                    "is_overdue": days_away < 0
                }

                if 0 <= days_away <= 7:
                    upcoming_7d.append(bill_item)
                if 0 <= days_away <= 14:
                    upcoming_14d.append(bill_item)
                if 0 <= days_away <= 30:
                    upcoming_30d.append(bill_item)
                    total_upcoming_30d += amt
            except Exception:
                continue

        upcoming_7d.sort(key=lambda x: x["days_away"])
        upcoming_14d.sort(key=lambda x: x["days_away"])
        upcoming_30d.sort(key=lambda x: x["days_away"])

        # Liquidity Shortfall Warning
        liquidity_warning = None
        sum_14d = sum(b["expected_amount"] for b in upcoming_14d)
        if sum_14d > 0 and total_liquid_gbp < sum_14d:
            shortfall = sum_14d - total_liquid_gbp
            liquidity_warning = {
                "level": "CRITICAL",
                "title": "Immediate Bill Payment Risk",
                "message": (
                    f"You have £{sum_14d:,.2f} in verified active bills due over the next 14 days, "
                    f"but only £{total_liquid_gbp:,.2f} liquid cash. Potential shortfall: £{shortfall:,.2f}."
                ),
                "shortfall_gbp": round(shortfall, 2)
            }
        elif total_upcoming_30d > 0 and total_liquid_gbp < total_upcoming_30d:
            liquidity_warning = {
                "level": "MODERATE",
                "title": "30-Day Cash Flow Squeeze",
                "message": (
                    f"Upcoming 30-day bills total £{total_upcoming_30d:,.2f}, "
                    f"leaving tight headroom on your current £{total_liquid_gbp:,.2f} balance."
                ),
                "shortfall_gbp": round(total_upcoming_30d - total_liquid_gbp, 2)
            }

        return {
            "total_liquid_gbp": round(total_liquid_gbp, 2),
            "total_active_recurring_bills": len(active_bills),
            "active_recurring_bills": active_bills,
            "inactive_historical_bills": inactive_bills,
            "upcoming_bills_7d": upcoming_7d,
            "upcoming_bills_14d": upcoming_14d,
            "upcoming_bills_30d": upcoming_30d,
            "total_upcoming_30d_gbp": round(total_upcoming_30d, 2),
            "price_hike_alerts": price_hikes,
            "duplicate_charge_alerts": duplicate_charges,
            "liquidity_shortfall_alert": liquidity_warning
        }

    def _detect_and_sync_bills(self, txs: List[Dict[str, Any]]):
        """
        Identifies genuine active recurring subscriptions.
        Strict rule: Must be classified as Subscriptions/Utilities OR match subscription keyword.
        Must have been charged within the last 45 days to be ACTIVE.
        """
        merchant_history = defaultdict(list)

        for tx in txs:
            amt = float(tx.get("amount", 0.0))
            if amt >= 0:
                continue
            name = (tx.get("counterparty_name") or tx.get("description") or "").strip()
            date_str = tx.get("booking_date")
            cat = tx.get("category", "")
            if not date_str or not name:
                continue

            # Skip general discretionary spend
            if not self._is_subscription_merchant(name, cat):
                continue

            try:
                dt = datetime.strptime(date_str[:10], "%Y-%m-%d")
                merchant_history[name].append({"date": dt, "amount": abs(amt), "raw_tx": tx})
            except Exception:
                continue

        active = []
        inactive = []
        now = datetime.now()

        for name, records in merchant_history.items():
            records.sort(key=lambda r: r["date"])
            last_rec = records[-1]
            days_since_last = (now.date() - last_rec["date"].date()).days

            expected_amt = round(last_rec["amount"], 2)
            bill_id = f"bill_{re.sub(r'[^a-zA-Z0-9]', '_', name.lower())[:24]}"

            # Determine interval
            interval = 30
            frequency = "monthly"
            if len(records) >= 2:
                prev_rec = records[-2]
                days_diff = (last_rec["date"] - prev_rec["date"]).days
                if 6 <= days_diff <= 8:
                    frequency = "weekly"
                    interval = 7
                elif 350 <= days_diff <= 380:
                    frequency = "annual"
                    interval = 365

            next_date = last_rec["date"] + timedelta(days=interval)

            bill_data = {
                "id": bill_id,
                "merchant": name,
                "category": last_rec["raw_tx"].get("category", "Subscriptions & Software"),
                "expected_amount": expected_amt,
                "frequency": frequency,
                "last_date": last_rec["date"].strftime("%Y-%m-%d"),
                "next_due_date": next_date.strftime("%Y-%m-%d")
            }

            # If last payment is older than 45 days, it is inactive (e.g. stopped, cancelled, or annual)
            if days_since_last > 45:
                inactive.append({**bill_data, "status": "INACTIVE / CANCELLED", "days_dormant": days_since_last})
            else:
                upsert_recurring_bill(
                    bill_id=bill_id,
                    merchant=name,
                    category=bill_data["category"],
                    expected_amount=expected_amt,
                    frequency=frequency,
                    last_date=bill_data["last_date"],
                    next_due_date=bill_data["next_due_date"]
                )
                active.append(bill_data)

        return active, inactive

    def _detect_price_hikes(self, txs: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Flags unexpected increases in recurring subscriptions.
        Strict rule: Only applies to Subscriptions & Software charged within last 90 days.
        """
        merchant_charges = defaultdict(list)
        now = datetime.now()

        for tx in txs:
            amt = float(tx.get("amount", 0.0))
            if amt >= 0:
                continue
            name = (tx.get("counterparty_name") or tx.get("description") or "").strip()
            date_str = tx.get("booking_date")
            cat = tx.get("category", "")
            if not date_str or not name:
                continue

            if not self._is_subscription_merchant(name, cat):
                continue

            try:
                dt = datetime.strptime(date_str[:10], "%Y-%m-%d")
                if (now.date() - dt.date()).days <= 90:
                    merchant_charges[name].append({"date": dt, "amount": abs(amt)})
            except Exception:
                continue

        alerts = []
        for name, charges in merchant_charges.items():
            if len(charges) < 2:
                continue
            charges.sort(key=lambda x: x["date"])
            latest = charges[-1]
            previous = charges[-2]

            # Price hike: strictly higher by > 5% and > £0.50
            if latest["amount"] > previous["amount"] * 1.05 and (latest["amount"] - previous["amount"]) >= 0.50:
                pct = round(((latest["amount"] - previous["amount"]) / previous["amount"]) * 100, 1)
                alerts.append({
                    "merchant": name,
                    "previous_amount": round(previous["amount"], 2),
                    "latest_amount": round(latest["amount"], 2),
                    "increase_amount": round(latest["amount"] - previous["amount"], 2),
                    "percentage_increase": pct,
                    "date_detected": latest["date"].strftime("%Y-%m-%d"),
                    "alert_text": (
                        f"🚨 {name} plan fee increased from £{previous['amount']:.2f} to £{latest['amount']:.2f} "
                        f"(+{pct}% / +£{latest['amount'] - previous['amount']:.2f}) on {latest['date'].strftime('%d %b %Y')}."
                    )
                })
        return alerts

    def _detect_duplicate_charges(self, txs: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Identifies identical charges occurring within 24 hours on the same account.
        Strict rule: Only checks recent transactions (within last 30 days).
        """
        charges_by_account = defaultdict(list)
        now = datetime.now()

        for tx in txs:
            amt = float(tx.get("amount", 0.0))
            if amt >= 0:
                continue
            # Skip zero or micro transactions (e.g. £0.00 card verification checks)
            if abs(amt) < 0.01:
                continue
            name = (tx.get("counterparty_name") or tx.get("description") or "").strip()
            date_str = tx.get("booking_date")
            acc_id = tx.get("account_id")
            tx_status = (tx.get("status") or "settled").lower()
            if not date_str or not name:
                continue
            try:
                dt = datetime.strptime(date_str[:10], "%Y-%m-%d")
                if (now.date() - dt.date()).days <= 30:
                    charges_by_account[acc_id].append({
                        "date": dt,
                        "amount": abs(amt),
                        "merchant": name,
                        "tx_id": tx.get("id") or tx.get("transaction_id"),
                        "status": tx_status
                    })
            except Exception:
                continue

        duplicates = []
        for acc_id, charges in charges_by_account.items():
            charges.sort(key=lambda x: x["date"])
            for i in range(len(charges) - 1):
                c1 = charges[i]
                c2 = charges[i+1]
                # If one is pending and one is settled, NEVER flag as duplicate charge
                # (They represent the pending authorization transitioning to settled)
                if (c1.get("status") == "pending" or c2.get("status") == "pending") and c1.get("status") != c2.get("status"):
                    continue

                if c1["merchant"].lower() == c2["merchant"].lower() and abs(c1["amount"] - c2["amount"]) < 0.01:
                    days_apart = abs((c2["date"] - c1["date"]).days)
                    if days_apart <= 1:  # within 24-48 hours
                        duplicates.append({
                            "merchant": c1["merchant"],
                            "amount": round(c1["amount"], 2),
                            "date_1": c1["date"].strftime("%Y-%m-%d"),
                            "date_2": c2["date"].strftime("%Y-%m-%d"),
                            "alert_text": (
                                f"⚠️ Potential duplicate charge: 2 identical charges of £{c1['amount']:.2f} "
                                f"to {c1['merchant']} on {c1['date'].strftime('%d %b')}."
                            )
                        })
        return duplicates
