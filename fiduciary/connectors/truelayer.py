import os
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional
from urllib.parse import urlencode

import requests

from fiduciary.config import (
    TRUELAYER_CLIENT_ID,
    TRUELAYER_CLIENT_SECRET,
    TRUELAYER_USE_SANDBOX,
)
from fiduciary.storage.db import (
    _names_match,
    get_all_oauth_tokens,
    get_oauth_tokens,
    insert_transactions,
    purge_stale_pending_transactions,
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
        """Exchanges callback authorization code for an access token and persists tokens per institution."""
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
        
        inst_key = "truelayer"
        if access_token:
            # Query accounts immediately to identify the exact provider bank (e.g. revolut, lloyds)
            try:
                acc_resp = requests.get(
                    f"{self.api_base}/data/v1/accounts",
                    headers={"Authorization": f"Bearer {access_token}"},
                    timeout=8
                )
                if acc_resp.status_code == 200:
                    results = acc_resp.json().get("results", [])
                    if results:
                        p_id = results[0].get("provider", {}).get("provider_id", "")
                        clean_id = p_id.replace("ob-", "").replace("oauth-", "").strip().lower()
                        if clean_id:
                            inst_key = f"truelayer:{clean_id}"
            except Exception:
                pass

            # Save isolated token for this bank so it never overwrites other banks (e.g. Revolut alongside Lloyds)
            save_oauth_tokens(inst_key, access_token, refresh_token, expires_in)
            # Also maintain generic alias
            save_oauth_tokens("truelayer", access_token, refresh_token, expires_in)

        token_data["provider_key"] = inst_key
        return token_data

    def refresh_access_token(self, refresh_token: str, provider_key: str = "truelayer") -> Optional[str]:
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
                    save_oauth_tokens(provider_key, new_access_token, new_refresh_token, expires_in)
                    return new_access_token
            return None
        except Exception:
            return None

    def get_all_valid_access_tokens(self) -> List[Dict[str, Any]]:
        """
        Returns active access tokens for all connected banks (Revolut, Lloyds, etc.),
        silently exchanging refresh tokens if expired.
        """
        all_tokens = get_all_oauth_tokens("truelayer")
        valid_list = []
        seen_refresh_or_access = set()

        for tok in all_tokens:
            p_key = tok.get("provider", "truelayer")
            access_tok = tok.get("access_token")
            ref_tok = tok.get("refresh_token")
            exp_str = tok.get("expires_at")

            unique_key = ref_tok or access_tok
            if not unique_key or unique_key in seen_refresh_or_access:
                continue
            seen_refresh_or_access.add(unique_key)

            token_to_use = None
            if exp_str and access_tok:
                try:
                    exp_dt = datetime.fromisoformat(exp_str)
                    if exp_dt > datetime.now() + timedelta(seconds=60):
                        token_to_use = access_tok
                except Exception:
                    pass

            if not token_to_use and ref_tok:
                token_to_use = self.refresh_access_token(ref_tok, provider_key=p_key)

            if token_to_use:
                valid_list.append({
                    "provider": p_key,
                    "access_token": token_to_use
                })

        return valid_list

    def get_valid_access_token(self) -> Optional[str]:
        """
        Returns an active access token, maintaining backward compatibility.
        """
        valid_tokens = self.get_all_valid_access_tokens()
        if valid_tokens:
            return valid_tokens[0]["access_token"]
        return None

    def get_connection_status(self) -> Dict[str, Any]:
        """Returns Open Banking connection state, connected institutions, and token status."""
        all_tokens = get_all_oauth_tokens("truelayer")
        if not all_tokens:
            return {
                "connected": False,
                "has_refresh_token": False,
                "status": "disconnected",
                "connected_banks": []
            }
        
        connected_banks = []
        for t in all_tokens:
            p = t.get("provider", "")
            if ":" in p:
                bank_name = p.split(":", 1)[1].upper()
                if bank_name not in connected_banks:
                    connected_banks.append(bank_name)
        
        has_refresh = any(bool(t.get("refresh_token")) for t in all_tokens)
        latest_token = all_tokens[0] if all_tokens else {}
        return {
            "connected": len(all_tokens) > 0,
            "has_refresh_token": has_refresh,
            "status": "connected" if has_refresh else "active_session",
            "connected_banks": connected_banks,
            "expires_at": latest_token.get("expires_at"),
            "updated_at": latest_token.get("updated_at")
        }

    def sync_latest(self) -> Dict[str, Any]:
        """
        Silently refreshes access tokens and pulls the latest balances and
        transactions for all connected Open Banking accounts (Revolut, Lloyds, etc.).
        """
        valid_tokens = self.get_all_valid_access_tokens()
        if not valid_tokens:
            return {
                "status": "needs_reconnect",
                "error": "Open Banking session expired or not yet connected. Please click 'Connect Bank' to link your bank.",
                "accounts_synced": [],
                "total_transactions": 0
            }

        all_synced_accounts = []
        total_txs = 0
        errors = []

        for item in valid_tokens:
            p_key = item["provider"]
            access_tok = item["access_token"]
            try:
                res = self.sync_accounts(access_tok, provider_key=p_key)
                all_synced_accounts.extend(res.get("accounts_synced", []))
                total_txs += res.get("total_transactions", 0)
            except requests.exceptions.HTTPError as he:
                # If 401 Unauthorized, automatically attempt refresh & retry
                if he.response is not None and he.response.status_code == 401:
                    tok_data = get_oauth_tokens(p_key)
                    ref_tok = tok_data.get("refresh_token") if tok_data else None
                    if ref_tok:
                        try:
                            new_access_tok = self.refresh_access_token(ref_tok, provider_key=p_key)
                            if new_access_tok:
                                res = self.sync_accounts(new_access_tok, provider_key=p_key)
                                all_synced_accounts.extend(res.get("accounts_synced", []))
                                total_txs += res.get("total_transactions", 0)
                                continue
                        except Exception as refresh_err:
                            errors.append(f"{p_key} (token refresh failed): {refresh_err}")
                            continue
                errors.append(f"{p_key}: {he}")
            except Exception as e:
                errors.append(f"{p_key}: {e}")

        return {
            "status": "success" if all_synced_accounts else ("error" if errors else "empty"),
            "accounts_synced": all_synced_accounts,
            "total_transactions": total_txs,
            "errors": errors if errors else None
        }

    def sync_accounts(self, access_token: str, provider_key: Optional[str] = None) -> Dict[str, Any]:
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
            clean_inst_id = provider_id.replace("ob-", "").replace("oauth-", "").strip().lower()
            upsert_institution(clean_inst_id, provider_name, "GB", status="connected")

            # Persist isolated token key for this specific bank if not already saved
            try:
                cur_tokens = get_oauth_tokens(provider_key or "truelayer")
                if cur_tokens:
                    save_oauth_tokens(
                        f"truelayer:{clean_inst_id}",
                        access_token,
                        cur_tokens.get("refresh_token"),
                        expires_in_seconds=3600
                    )
            except Exception:
                pass

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
            settled_list = []
            try:
                now = datetime.now()
                from_date = (now - timedelta(days=60)).strftime("%Y-%m-%d")
                to_date = now.strftime("%Y-%m-%d")
                tx_url = f"{self.api_base}/data/v1/accounts/{raw_acc_id}/transactions?from={from_date}&to={to_date}"
                tx_resp = requests.get(tx_url, headers=headers, timeout=15)
                if tx_resp.status_code == 200:
                    for t in tx_resp.json().get("results", []):
                        amt = float(t.get("amount", 0.0))
                        settled_list.append({
                            "transaction_id": str(t.get("transaction_id")),
                            "booking_date": (t.get("timestamp") or "")[:10] or now.strftime("%Y-%m-%d"),
                            "amount": amt,
                            "currency": t.get("currency", "GBP"),
                            "counterparty_name": t.get("merchant_name") or t.get("description", ""),
                            "description": t.get("description", ""),
                            "category": t.get("transaction_category", "General"),
                            "status": "settled"
                        })
            except Exception:
                pass

            # 4. Fetch Pending Transactions (recent card taps/authorizations done in last minutes/hours)
            pending_list = []
            try:
                pending_url = f"{self.api_base}/data/v1/accounts/{raw_acc_id}/transactions/pending"
                pending_resp = requests.get(pending_url, headers=headers, timeout=15)
                if pending_resp.status_code == 200:
                    for p in pending_resp.json().get("results", []):
                        amt = float(p.get("amount", 0.0))
                        p_desc = p.get("merchant_name") or p.get("description", "")
                        p_date = (p.get("timestamp") or "")[:10] or now.strftime("%Y-%m-%d")

                        # Intra-sync deduplication:
                        # Skip if matching transaction is already settled in this batch
                        already_settled = False
                        for s in settled_list:
                            if abs(s["amount"] - amt) < 0.01:
                                s_desc = s["counterparty_name"] or s["description"]
                                if p_desc.lower() == s_desc.lower() or _names_match(p_desc, s_desc):
                                    try:
                                        d_s = datetime.strptime(s["booking_date"], "%Y-%m-%d")
                                        d_p = datetime.strptime(p_date, "%Y-%m-%d")
                                        if abs((d_s - d_p).days) <= 3:
                                            already_settled = True
                                            break
                                    except Exception:
                                        pass
                        if not already_settled:
                            pending_list.append({
                                "transaction_id": str(p.get("transaction_id")),
                                "booking_date": p_date,
                                "amount": amt,
                                "currency": p.get("currency", "GBP"),
                                "counterparty_name": p_desc,
                                "description": p.get("description", ""),
                                "category": p.get("transaction_category", "General"),
                                "status": "pending"
                            })
            except Exception:
                pass

            # Insert settled first (automatically reconciles and purges matching pending records in SQLite)
            if settled_list:
                insert_transactions(acc_db_id, settled_list)
                total_txs += len(settled_list)

            # Insert remaining genuinely pending transactions
            if pending_list:
                insert_transactions(acc_db_id, pending_list)
                total_txs += len(pending_list)

            # Purge any stale pending transactions that are no longer active in TrueLayer
            active_pending_ids = {f"{acc_db_id}_{p['transaction_id']}" for p in pending_list}
            purge_stale_pending_transactions(acc_db_id, active_pending_ids)

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
