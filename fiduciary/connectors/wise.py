import os
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

import requests

from fiduciary.config import WISE_API_TOKEN
from fiduciary.storage.db import (
    insert_transactions,
    upsert_account,
    upsert_institution,
)

WISE_API_BASE = "https://api.wise.com"

class WiseClient:
    def __init__(self, api_token: Optional[str] = None):
        self.api_token = api_token or os.getenv("WISE_API_TOKEN") or WISE_API_TOKEN
        if not self.api_token:
            raise ValueError(
                "Wise API token not found! Please set WISE_API_TOKEN in your .env or environment."
            )

    def _headers(self) -> Dict[str, str]:
        return {
            "Authorization": f"Bearer {self.api_token}",
            "Content-Type": "application/json",
        }

    def get_profiles(self) -> List[Dict[str, Any]]:
        """Fetch user profiles (Personal and/or Business)."""
        url = f"{WISE_API_BASE}/v1/profiles"
        resp = requests.get(url, headers=self._headers())
        resp.raise_for_status()
        return resp.json()

    def get_personal_profile_id(self) -> int:
        """Find the primary personal profile ID."""
        profiles = self.get_profiles()
        for p in profiles:
            if p.get("type") == "personal":
                return p["id"]
        if profiles:
            return profiles[0]["id"]
        raise ValueError("No Wise profile found for this token.")

    def get_balances(self, profile_id: int) -> List[Dict[str, Any]]:
        """Fetch all currency balances and jars/pots."""
        url = f"{WISE_API_BASE}/v4/profiles/{profile_id}/balances?types=STANDARD,SAVINGS"
        resp = requests.get(url, headers=self._headers())
        resp.raise_for_status()
        return resp.json()

    def get_statement(
        self, profile_id: int, balance_id: int, currency: str, days: int = 90
    ) -> Dict[str, Any]:
        """Fetch recent transaction statement for a balance."""
        now = datetime.utcnow()
        start = now - timedelta(days=days)
        url = f"{WISE_API_BASE}/v1/profiles/{profile_id}/balance-statements/{balance_id}/statement.json"
        params = {
            "currency": currency,
            "intervalStart": start.strftime("%Y-%m-%dT00:00:00.000Z"),
            "intervalEnd": now.strftime("%Y-%m-%dT23:59:59.000Z"),
        }
        resp = requests.get(url, headers=self._headers(), params=params)
        if resp.status_code == 200:
            return resp.json()
        return {"transactions": []}

    def sync_to_db(self) -> Dict[str, Any]:
        """
        Pull live data from Wise and sync into the local SQLite database.
        Returns a summary of synced balances and transactions.
        """
        upsert_institution(
            inst_id="wise",
            name="Wise",
            country="GB",
            status="connected"
        )

        profile_id = self.get_personal_profile_id()
        balances = self.get_balances(profile_id)

        synced_accounts = []
        total_transactions = 0

        for bal in balances:
            bal_id = str(bal["id"])
            currency = bal.get("currency", "GBP")
            balance_type = bal.get("type", "STANDARD")
            amount_val = bal.get("amount", {}).get("value", 0.0)
            cash_val = bal.get("cashAmount", {}).get("value", amount_val)

            # Name the account cleanly (e.g. "Wise GBP Account", "Wise Jar - EUR")
            acc_name = f"Wise {currency} ({balance_type.capitalize()})"
            db_acc_id = f"wise_{bal_id}_{currency.lower()}"

            # Save account balance to local database
            upsert_account(
                acc_id=db_acc_id,
                institution_id="wise",
                raw_account_id=bal_id,
                name=acc_name,
                account_type="savings" if balance_type == "SAVINGS" else "checking",
                currency=currency,
                current_balance=float(amount_val),
                available_balance=float(cash_val),
                estimated_interest_rate=0.0  # Wise default standard balance is ~0% unless Assets/Interest enabled
            )
            synced_accounts.append({
                "currency": currency,
                "type": balance_type,
                "balance": float(amount_val)
            })

            # Fetch transactions for this balance
            try:
                stmt = self.get_statement(profile_id, bal["id"], currency, days=60)
                tx_list = []
                for tx in stmt.get("transactions", []):
                    amt = tx.get("amount", {}).get("value", 0.0)
                    tx_list.append({
                        "transaction_id": str(tx.get("referenceNumber", tx.get("date"))),
                        "booking_date": tx.get("date", "")[:10],
                        "amount": float(amt),
                        "currency": currency,
                        "counterparty_name": tx.get("merchant", {}).get("name", "") or tx.get("details", {}).get("description", ""),
                        "description": tx.get("details", {}).get("description", "") or tx.get("type", ""),
                        "category": tx.get("details", {}).get("category", "General")
                    })
                if tx_list:
                    insert_transactions(db_acc_id, tx_list)
                    total_transactions += len(tx_list)
            except Exception:
                pass

        # Fetch up to 100 recent profile activities
        try:
            act_url = f"{WISE_API_BASE}/v1/profiles/{profile_id}/activities?size=100"
            act_resp = requests.get(act_url, headers=self._headers())
            if act_resp.status_code == 200:
                activities = act_resp.json().get("activities", [])
                primary_acc = f"wise_{balances[0]['id']}_{balances[0].get('currency', 'gbp').lower()}" if balances else "wise_default"
                act_txs = []
                for act in activities:
                    act_type = act.get("type", "")
                    sec_raw = act.get("secondaryAmount", "")
                    prim_raw = act.get("primaryAmount", "")
                    title = act.get("title", "").replace("<strong>", "").replace("</strong>", "")
                    desc = act.get("description", "")

                    # Choose raw text containing the relevant amount & currency
                    raw_text = sec_raw if (sec_raw and "GBP" in sec_raw) else prim_raw

                    # Extract numerical amount
                    num_val = 0.0
                    currency = "GBP"
                    for token in raw_text.replace("+", "").replace("<positive>", "").replace("</positive>", "").split():
                        cleaned = token.replace(",", "").replace("£", "").replace("$", "").replace("€", "")
                        try:
                            num_val = float(cleaned)
                        except ValueError:
                            if len(token) == 3 and token.isalpha():
                                currency = token.upper()

                    # Determine sign and category
                    if act_type in ["CARD_PAYMENT", "BALANCE_ASSET_FEE"]:
                        signed_amt = -abs(num_val)
                        category = "Platform Fee" if act_type == "BALANCE_ASSET_FEE" else "Card Spend"
                    elif act_type == "TRANSFER":
                        is_sent = "sent" in desc.lower() or not sec_raw
                        signed_amt = -abs(num_val) if is_sent else abs(num_val)
                        category = "Remittance / Transfer"
                    elif act_type == "BALANCE_DEPOSIT":
                        signed_amt = abs(num_val)
                        category = "Deposit / Income"
                    elif act_type == "CARD_CHECK":
                        signed_amt = 0.0
                        category = "Card Verification"
                    else:
                        signed_amt = -abs(num_val) if "sent" in desc.lower() else abs(num_val)
                        category = "General"

                    act_txs.append({
                        "transaction_id": act.get("id"),
                        "booking_date": (act.get("createdOn") or "")[:10],
                        "amount": signed_amt,
                        "currency": currency,
                        "counterparty_name": title or "Wise Transaction",
                        "description": f"{act_type}: {desc}" if desc else act_type,
                        "category": category
                    })
                if act_txs:
                    insert_transactions(primary_acc, act_txs)
                    total_transactions += len(act_txs)
        except Exception:
            pass

        return {
            "status": "success",
            "profile_id": profile_id,
            "accounts_synced": synced_accounts,
            "transactions_count": total_transactions,
        }
