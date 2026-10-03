import os
from datetime import datetime, timedelta
from typing import Any, Dict, Optional
from urllib.parse import urlencode

import requests

from fiduciary.config import (
    TRUELAYER_CLIENT_ID,
    TRUELAYER_CLIENT_SECRET,
    TRUELAYER_USE_SANDBOX,
)
from fiduciary.storage.db import (
    get_oauth_tokens,
    insert_transactions,
    save_net_worth_snapshot,
    save_oauth_tokens,
    upsert_account,
    upsert_institution,
)


class TrueLayerClient:
    def __init__(
        self,
        client_id: Optional[str] = None,
        client_secret: Optional[str] = None,
        use_sandbox: Optional[bool] = None,
    ):
        self.client_id = client_id or os.getenv("TRUELAYER_CLIENT_ID") or TRUELAYER_CLIENT_ID
        self.client_secret = client_secret or os.getenv("TRUELAYER_CLIENT_SECRET") or TRUELAYER_CLIENT_SECRET
        self.use_sandbox = use_sandbox if use_sandbox is not None else TRUELAYER_USE_SANDBOX

        if self.use_sandbox:
            self.auth_base = "https://auth.truelayer-sandbox.com"
            self.api_base = "https://api.truelayer-sandbox.com"
        else:
            self.auth_base = "https://auth.truelayer.com"
            self.api_base = "https://api.truelayer.com"

    def is_configured(self) -> bool:
        return bool(self.client_id and self.client_secret)

    def get_auth_url(self, redirect_uri: Optional[str] = None, provider_id: Optional[str] = None) -> str:
        """
        Generates the TrueLayer hosted consent screen URL.
        User selects bank (Revolut, Chase, HSBC, Lloyds, NatWest, Zopa) and approves via Face ID.
        """
        if not self.is_configured():
            raise ValueError("TrueLayer credentials not set in .env (TRUELAYER_CLIENT_ID, TRUELAYER_CLIENT_SECRET)")

        r_uri = redirect_uri or "http://localhost:8080/truelayer/callback"
        params = {
            "response_type": "code",
            "client_id": self.client_id,
            "scope": "info accounts balance transactions offline_access",
            "redirect_uri": r_uri,
            "providers": "mock uk-ob-all uk-oauth-all" if self.use_sandbox else "uk-ob-all uk-oauth-all",
        }
        if provider_id:
            params["provider_id"] = provider_id

        return f"{self.auth_base}/?{urlencode(params)}"

    def exchange_code(self, code: str, redirect_uri: Optional[str] = None) -> Dict[str, Any]:
        """Exchanges callback authorization code for an access token and persists tokens."""
        url = f"{self.auth_base}/connect/token"
        r_uri = redirect_uri or "http://localhost:8080/truelayer/callback"
        data = {
            "grant_type": "authorization_code",
            "client_id": self.client_id,
            "client_secret": self.client_secret,
            "redirect_uri": r_uri,
            "code": code,
        }
        resp = requests.post(url, data=data)
        resp.raise_for_status()
        token_data = resp.json()

        access_token = token_data.get("access_token")
        refresh_token = token_data.get("refresh_token")
        expires_in = int(token_data.get("expires_in", 3600))
        if access_token:
            save_oauth_tokens("truelayer", access_token, refresh_token, expires_in)

        return token_data

    def refresh_access_token(self, refresh_token: str) -> Optional[str]:
        """Exchanges a 90-day Open Banking refresh token for a fresh access token."""
        url = f"{self.auth_base}/connect/token"
        data = {
            "grant_type": "refresh_token",
            "client_id": self.client_id,
            "client_secret": self.client_secret,
            "refresh_token": refresh_token,
        }
        try:
            resp = requests.post(url, data=data, timeout=15)
            if resp.status_code == 200:
                token_data = resp.json()
                new_access_token = token_data.get("access_token")
                new_refresh_token = token_data.get("refresh_token") or refresh_token
                expires_in = int(token_data.get("expires_in", 3600))
                if new_access_token:
                    save_oauth_tokens("truelayer", new_access_token, new_refresh_token, expires_in)
                    return new_access_token
            return None
        except Exception:
            return None

    def get_valid_access_token(self) -> Optional[str]:
        """
        Returns an active access token, silently exchanging the refresh token
        if the current access token has expired.
        """
        tokens = get_oauth_tokens("truelayer")
        if not tokens:
            return None

        expires_at_str = tokens.get("expires_at")
        access_token = tokens.get("access_token")
        refresh_token = tokens.get("refresh_token")

        if expires_at_str and access_token:
            try:
                expires_at = datetime.fromisoformat(expires_at_str)
                if expires_at > datetime.now() + timedelta(seconds=60):
                    return access_token
            except Exception:
                pass

        if refresh_token:
            return self.refresh_access_token(refresh_token)

        return None

    def get_connection_status(self) -> Dict[str, Any]:
        """Returns Open Banking connection state and token status."""
        tokens = get_oauth_tokens("truelayer")
        if not tokens:
            return {
                "connected": False,
                "has_refresh_token": False,
                "status": "disconnected"
            }
        has_refresh = bool(tokens.get("refresh_token"))
        return {
            "connected": True,
            "has_refresh_token": has_refresh,
            "status": "connected" if has_refresh else "active_session",
            "expires_at": tokens.get("expires_at"),
            "updated_at": tokens.get("updated_at")
        }

    def sync_latest(self) -> Dict[str, Any]:
        """
        Silently refreshes access token and pulls the latest balances and
        transactions for all connected Open Banking accounts (Revolut, etc.).
        """
        token = self.get_valid_access_token()
        if not token:
            return {
                "status": "needs_reconnect",
                "error": "Open Banking session expired or not yet connected. Please click 'Connect Bank' to link Revolut.",
                "accounts_synced": [],
                "total_transactions": 0
            }
        return self.sync_accounts(token)

    def sync_accounts(self, access_token: str) -> Dict[str, Any]:
        """
        Pulls accounts, live balances, and 90 days of transactions from TrueLayer
        into the local SQLite database.
        """
        headers = {"Authorization": f"Bearer {access_token}"}

        # 1. Fetch Accounts
        acc_resp = requests.get(f"{self.api_base}/data/v1/accounts", headers=headers)
        acc_resp.raise_for_status()
        accounts_data = acc_resp.json().get("results", [])

        synced_accounts = []
        total_txs = 0

        for acc in accounts_data:
            raw_acc_id = acc.get("account_id")
            display_name = acc.get("display_name", "Account")
            currency = acc.get("currency", "GBP")
            acc_type = acc.get("account_type", "TRANSACTION").lower()
            provider = acc.get("provider", {})
            provider_id = provider.get("provider_id", "truelayer_bank")
            provider_name = provider.get("display_name", "Connected Bank")

            # Clean provider ID
            clean_inst_id = provider_id.replace("ob-", "").replace("oauth-", "")
            upsert_institution(clean_inst_id, provider_name, "GB", status="connected")

            # 2. Fetch Balance
            current_bal = 0.0
            avail_bal = 0.0
            try:
                bal_resp = requests.get(f"{self.api_base}/data/v1/accounts/{raw_acc_id}/balance", headers=headers)
                if bal_resp.status_code == 200:
                    b_results = bal_resp.json().get("results", [])
                    if b_results:
                        current_bal = float(b_results[0].get("current", 0.0))
                        avail_bal = float(b_results[0].get("available", current_bal))
            except Exception:
                pass

            acc_db_id = f"tl_{clean_inst_id}_{raw_acc_id[-6:]}"
            upsert_account(
                acc_id=acc_db_id,
                institution_id=clean_inst_id,
                raw_account_id=raw_acc_id,
                name=f"{provider_name} - {display_name}",
                account_type="savings" if "saving" in acc_type else "checking",
                currency=currency,
                current_balance=current_bal,
                available_balance=avail_bal,
                estimated_interest_rate=0.0
            )

            # 3. Fetch Settled Transactions (last 60 days)
            try:
                now = datetime.now()
                from_date = (now - timedelta(days=60)).strftime("%Y-%m-%d")
                to_date = now.strftime("%Y-%m-%d")
                tx_url = f"{self.api_base}/data/v1/accounts/{raw_acc_id}/transactions?from={from_date}&to={to_date}"
                tx_resp = requests.get(tx_url, headers=headers, timeout=15)
                raw_txs = []
                if tx_resp.status_code == 200:
                    raw_txs = tx_resp.json().get("results", [])

                # 4. Fetch Pending Transactions (recent card taps/authorizations done in last minutes/hours)
                try:
                    pending_url = f"{self.api_base}/data/v1/accounts/{raw_acc_id}/transactions/pending"
                    pending_resp = requests.get(pending_url, headers=headers, timeout=15)
                    if pending_resp.status_code == 200:
                        pending_txs = pending_resp.json().get("results", [])
                        raw_txs.extend(pending_txs)
                except Exception:
                    pass

                tx_list = []
                for t in raw_txs:
                    amt = float(t.get("amount", 0.0))
                    tx_list.append({
                        "transaction_id": str(t.get("transaction_id")),
                        "booking_date": (t.get("timestamp") or "")[:10] or now.strftime("%Y-%m-%d"),
                        "amount": amt,
                        "currency": t.get("currency", "GBP"),
                        "counterparty_name": t.get("merchant_name") or t.get("description", ""),
                        "description": t.get("description", ""),
                        "category": t.get("transaction_category", "General")
                    })
                if tx_list:
                    insert_transactions(acc_db_id, tx_list)
                    total_txs += len(tx_list)
            except Exception:
                pass

            synced_accounts.append({
                "institution": provider_name,
                "account": display_name,
                "balance": current_bal
            })

        save_net_worth_snapshot()

        return {
            "status": "success",
            "accounts_synced": synced_accounts,
            "total_transactions": total_txs
        }
