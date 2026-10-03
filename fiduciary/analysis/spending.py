"""
Spending Insight Engine for Personal Fiduciary Agent.
Provides deterministic, zero-hallucination spending queries, category breakdowns,
spending velocity shift analysis, and micro-expense leakage detection.
"""

import re
from collections import defaultdict
from typing import Any, Dict, Optional

from fiduciary.storage.db import (
    get_recent_transactions,
)


class SpendingInsightEngine:
    """
    Deterministic spending query and analytics engine.
    Maps natural language queries and category terms to verified transaction records,
    calculating exact sums, frequencies, date ranges, and velocity shifts.
    """

    CATEGORY_MAP = {
        "Dining, Pubs & Entertainment": [
            "pub", "pubs", "bar", "bars", "beer", "drinks", "tavern", "inn", "brewery",
            "dining", "restaurant", "restaurants", "eating out", "takeaway", "deliveroo",
            "uber eats", "evelyn", "cluck", "pizza", "wine", "cocktail", "alcohol", "pint", "pints"
        ],
        "Groceries & Essentials": [
            "grocery", "groceries", "supermarket", "supermarkets", "sainsbury", "sainsburys",
            "tesco", "m&s", "marks and spencer", "waitrose", "aldi", "lidl", "asda",
            "morrison", "co-op", "whole food", "welcome", "baker", "bakery", "food essentials"
        ],
        "Subscriptions & Software": [
            "subscription", "subscriptions", "software", "saas", "anthropic", "claude",
            "openai", "chatgpt", "spotify", "netflix", "apple", "google storage",
            "github", "lemon squeezy", "prime", "disney"
        ],
        "Transport & Commute": [
            "transport", "commute", "travel", "tfl", "train", "tube", "rail", "uber", "tram", "bus"
        ],
        "Fees & Charges": [
            "fee", "fees", "charge", "charges", "interest", "bank fee"
        ],
        "Transfers & Remittance": [
            "transfer", "transfers", "remittance", "topup", "top up", "wise", "revolut", "cheddar"
        ],
        "Debt Repayment": [
            "debt", "credit card", "loan", "amex", "barclaycard", "klarna", "clearpay"
        ],
        "General Living Spend": [
            "general", "shopping", "retail", "living", "amazon"
        ]
    }

    @classmethod
    def resolve_category(cls, text: str) -> Optional[str]:
        """Resolves natural language terms to canonical database category names."""
        clean = text.lower().strip()

        # Exact or partial match with canonical names
        for cat in cls.CATEGORY_MAP.keys():
            if clean in cat.lower() or cat.lower() in clean:
                return cat

        # Match with keywords / aliases using word boundaries
        for cat, keywords in cls.CATEGORY_MAP.items():
            for kw in keywords:
                if re.search(r'\b' + re.escape(kw) + r'\b', clean):
                    return cat

        return None

    @classmethod
    def parse_spending_intent(cls, query_str: str) -> Dict[str, Any]:
        """
        Parses user query to extract category, merchant search, timeframe days,
        requested limit count, and target bank.
        """
        q_lower = query_str.lower()

        # 1. Target Bank
        target_bank = None
        for b in ["revolut", "wise", "natwest", "truelayer"]:
            if b in q_lower:
                target_bank = b
                break

        # 2. Timeframe Days
        days = None
        match_days = re.search(r'\b(?:last|past)\s+(\d+)\s+days?\b', q_lower)
        if match_days:
            days = int(match_days.group(1))
        elif re.search(r'\b(?:last|past)\s+week\b', q_lower) or "7 days" in q_lower:
            days = 7
        elif re.search(r'\b(?:last|past)\s+(?:2 weeks|fortnight)\b', q_lower) or "14 days" in q_lower:
            days = 14
        elif re.search(r'\b(?:last|past|this)\s+month\b', q_lower) or "30 days" in q_lower:
            days = 30
        elif re.search(r'\b(?:last|past)\s+(?:quarter|3 months)\b', q_lower) or "90 days" in q_lower:
            days = 90
        elif re.search(r'\b(?:last|past)\s+(\d+)\s+months?\b', q_lower):
            m_count = int(re.search(r'\b(?:last|past)\s+(\d+)\s+months?\b', q_lower).group(1))
            days = m_count * 30

        # 3. Item count / limit
        match_count = re.search(r'\b(?:last|latest|recent)\s+(\d+)\b', q_lower)
        limit = int(match_count.group(1)) if match_count else None

        # 4. Target Category
        matched_cat = cls.resolve_category(q_lower)

        # 5. Specific merchant keyword if no general category, or alongside category
        specific_keyword = None
        for kw_candidate in ["sainsbury", "tesco", "waitrose", "cluck", "evelyn", "carpenters", "kings arms", "wheatsheaf", "southwark", "anthropic", "spotify", "uber", "tfl"]:
            if kw_candidate in q_lower:
                specific_keyword = kw_candidate
                break

        is_spending_query = any(w in q_lower for w in [
            "spend", "spent", "cost", "how much", "bought", "purchase", "purchases", "paid",
            "pub", "pubs", "dining", "groceries", "food", "subscriptions", "transport"
        ])

        is_last_tx_query = any(w in q_lower for w in [
            "transaction", "transactions", "latest", "recent", "history", "statement", "charges"
        ])

        return {
            "is_spending_query": is_spending_query,
            "is_last_tx_query": is_last_tx_query,
            "matched_category": matched_cat,
            "specific_keyword": specific_keyword,
            "days": days,
            "limit": limit or 15,
            "target_bank": target_bank
        }

    @classmethod
    def query_spending(
        cls,
        query_str: Optional[str] = None,
        category: Optional[str] = None,
        days: Optional[int] = None,
        keyword: Optional[str] = None,
        limit: int = 15,
        target_bank: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Executes a deterministic category/merchant spending calculation with full itemized transactions.
        If timeframe days is None, calculates both all-time total and 30-day recent total.
        """
        parsed = cls.parse_spending_intent(query_str or "") if query_str else {}
        target_cat = category or parsed.get("matched_category")
        target_days = days if days is not None else parsed.get("days")
        target_kw = keyword or parsed.get("specific_keyword")
        target_limit = limit or parsed.get("limit") or 15
        bank = target_bank or parsed.get("target_bank")

        # Fetch candidate transactions
        # If target_days is None, fetch all stored transactions to ensure historical completeness
        all_candidate_txs = get_recent_transactions(
            days=target_days,
            account_id=bank,
            limit=None,
            search=target_kw if not target_cat else None,
            category=target_cat
        )

        # In-memory post-filter in case keyword was specified alongside category
        filtered_txs = []
        for t in all_candidate_txs:
            amt = float(t.get("amount", 0.0))
            if amt >= 0:
                continue  # Outflows only for spending queries

            c_name = (t.get("counterparty_name") or "").lower()
            desc = (t.get("description") or "").lower()
            t_cat = t.get("category", "")

            # If user searched "pub" or "pubs", also match keyword in merchant even if category differed
            matches = True
            if target_cat:
                if t_cat != target_cat and not (target_kw and (target_kw in c_name or target_kw in desc)):
                    matches = False
            elif target_kw:
                if target_kw not in c_name and target_kw not in desc and target_kw not in t_cat.lower():
                    matches = False

            if matches:
                filtered_txs.append(t)

        total_spent = sum(abs(float(t["amount"])) for t in filtered_txs)
        tx_count = len(filtered_txs)
        avg_amount = round(total_spent / tx_count, 2) if tx_count > 0 else 0.0

        # Calculate 30-day subset for comparison if querying all time
        txs_30d = [t for t in filtered_txs if t.get("booking_date", "") >= "2026-09-01"]  # Current active month
        total_spent_30d = sum(abs(float(t["amount"])) for t in txs_30d)

        dates = [t["booking_date"] for t in filtered_txs if t.get("booking_date")]
        date_range_str = f"{min(dates)} to {max(dates)}" if dates else "No dates recorded"

        # Top merchants in this category
        merchant_totals = defaultdict(lambda: {"total": 0.0, "count": 0})
        for t in filtered_txs:
            name = t.get("counterparty_name") or t.get("description") or "Unknown"
            merchant_totals[name]["total"] += abs(float(t["amount"]))
            merchant_totals[name]["count"] += 1

        top_venues = []
        for m_name, m_data in sorted(merchant_totals.items(), key=lambda x: x[1]["total"], reverse=True)[:5]:
            top_venues.append({
                "merchant": m_name,
                "total": round(m_data["total"], 2),
                "count": m_data["count"]
            })

        # Narrative formulation for copilot prompt injection
        label = target_cat or (f"'{target_kw}'" if target_kw else "Recent Outflows")
        time_desc = f"last {target_days} days" if target_days else f"all time ({tx_count} records from {date_range_str})"

        q_text = (query_str or "").lower()
        is_specifically_pub = any(w in q_text for w in ["pub", "pubs", "beer", "tavern", "pint", "pints", "bar", "bars"])

        if is_specifically_pub and target_cat == "Dining, Pubs & Entertainment":
            pub_kws = ["pub", "tavern", "arms", "hound", "wheatsheaf", "hammerton", "greyhound", "tap on the line", "blackfriar", "youngs", "inn", "brewery"]
            pub_txs = [
                t for t in filtered_txs
                if any(k in (t.get("counterparty_name") or "").lower() or k in (t.get("description") or "").lower() for k in pub_kws)
            ]
            if pub_txs:
                pub_total = sum(abs(float(t["amount"])) for t in pub_txs)
                pub_avg = round(pub_total / len(pub_txs), 2)
                pub_names = list(dict.fromkeys([t.get("counterparty_name") or t.get("description") for t in pub_txs]))[:5]
                pub_venues_str = ", ".join(pub_names)
                narrative = (
                    f"Verified spend specifically on Pubs & Bars ({time_desc}): £{pub_total:,.2f} across {len(pub_txs)} visits "
                    f"(Average: £{pub_avg:,.2f}/visit; venues include: {pub_venues_str}). "
                    f"Total in the broader 'Dining, Pubs & Entertainment' category is £{total_spent:,.2f} across {tx_count} transactions."
                )
                non_pub_txs = [t for t in filtered_txs if t not in pub_txs]
                filtered_txs = pub_txs + non_pub_txs
            else:
                narrative = (
                    f"Verified spend on {label} ({time_desc}): £{total_spent:,.2f} across {tx_count} transactions "
                    f"(Average: £{avg_amount:,.2f}/transaction)."
                )
        else:
            narrative = (
                f"Verified spend on {label} ({time_desc}): £{total_spent:,.2f} across {tx_count} transactions "
                f"(Average: £{avg_amount:,.2f}/transaction)."
            )

        if not target_days and total_spent_30d > 0 and total_spent_30d != total_spent:
            narrative += f" Recent 30-day spend in this category was £{total_spent_30d:,.2f} across {len(txs_30d)} transactions."

        return {
            "category": target_cat,
            "keyword": target_kw,
            "timeframe_days": target_days,
            "total_spent_gbp": round(total_spent, 2),
            "total_spent_30d_gbp": round(total_spent_30d, 2),
            "transaction_count": tx_count,
            "transaction_count_30d": len(txs_30d),
            "average_transaction_gbp": avg_amount,
            "date_range": date_range_str,
            "top_venues": top_venues,
            "itemized_transactions": filtered_txs[:target_limit],
            "narrative": narrative
        }

    @classmethod
    def get_spending_velocity(cls) -> Dict[str, Any]:
        """
        Analyzes 7-day spending velocity vs 30-day baseline.
        Detects acceleration/deceleration shifts and flags category drivers.
        """
        txs_7d = get_recent_transactions(days=7)
        txs_30d = get_recent_transactions(days=30)

        outflow_7d = sum(abs(float(t["amount"])) for t in txs_7d if float(t["amount"]) < 0 and t.get("category") not in ["Transfers & Remittance", "Debt Repayment"])
        outflow_30d = sum(abs(float(t["amount"])) for t in txs_30d if float(t["amount"]) < 0 and t.get("category") not in ["Transfers & Remittance", "Debt Repayment"])

        # Normalize 30d to weekly
        weekly_baseline = round((outflow_30d / 30.0) * 7.0, 2) if outflow_30d > 0 else 0.0
        actual_weekly = round(outflow_7d, 2)

        if weekly_baseline > 0:
            shift_pct = round(((actual_weekly - weekly_baseline) / weekly_baseline) * 100.0, 1)
        else:
            shift_pct = 0.0

        status = "ACCELERATING" if shift_pct > 15.0 else ("DECELERATING" if shift_pct < -15.0 else "STEADY")

        # Category breakdown for 7d
        cat_7d = defaultdict(float)
        for t in txs_7d:
            if float(t["amount"]) < 0:
                cat_7d[t.get("category", "General")] += abs(float(t["amount"]))

        return {
            "status": status,
            "trailing_7d_spend": actual_weekly,
            "normalized_weekly_baseline": weekly_baseline,
            "velocity_shift_pct": shift_pct,
            "is_accelerating": shift_pct > 15.0,
            "is_decelerating": shift_pct < -15.0,
            "category_7d_totals": {k: round(v, 2) for k, v in cat_7d.items()}
        }

    @classmethod
    def get_micro_expense_analysis(cls, threshold: float = 10.0, days: int = 30) -> Dict[str, Any]:
        """
        Detects silent micro-expense leakage (transactions under £10.00).
        """
        txs = get_recent_transactions(days=days)
        micro_txs = [t for t in txs if -threshold <= float(t.get("amount", 0.0)) < 0]

        total_micro = sum(abs(float(t["amount"])) for t in micro_txs)
        total_outflow = sum(abs(float(t["amount"])) for t in txs if float(t.get("amount", 0.0)) < 0)

        pct_of_outflow = round((total_micro / total_outflow * 100.0), 1) if total_outflow > 0 else 0.0

        merchants = defaultdict(lambda: {"total": 0.0, "count": 0})
        for t in micro_txs:
            name = t.get("counterparty_name") or t.get("description") or "Unknown"
            merchants[name]["total"] += abs(float(t["amount"]))
            merchants[name]["count"] += 1

        top_micro_merchants = []
        for m_name, m_data in sorted(merchants.items(), key=lambda x: x[1]["total"], reverse=True)[:5]:
            top_micro_merchants.append({
                "merchant": m_name,
                "total": round(m_data["total"], 2),
                "count": m_data["count"]
            })

        return {
            "micro_threshold_gbp": threshold,
            "timeframe_days": days,
            "total_micro_spend_gbp": round(total_micro, 2),
            "micro_transaction_count": len(micro_txs),
            "pct_of_living_spend": pct_of_outflow,
            "top_micro_merchants": top_micro_merchants
        }
