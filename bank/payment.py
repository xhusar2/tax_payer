from __future__ import annotations

from typing import Any, Dict

import requests

from config.settings import BANK_API_KEY, BANK_API_URL, BANK_ACCOUNT_NUMBER


class BankPayment:
    """
    Thin wrapper over a hypothetical bank API for inkaso / direct debit.
    You’ll need to adapt this to your real bank (Fio, Air, KB, …).
    """

    def __init__(
        self,
        api_url: str | None = None,
        account_number: str | None = None,
        api_key: str | None = None,
    ) -> None:
        self.api_url = api_url or BANK_API_URL
        self.account_number = account_number or BANK_ACCOUNT_NUMBER
        self.api_key = api_key or BANK_API_KEY

        if not self.api_url:
            raise RuntimeError("BANK_API_URL not configured")
        if not self.account_number:
            raise RuntimeError("BANK_ACCOUNT_NUMBER not configured")
        if not self.api_key:
            raise RuntimeError("BANK_API_KEY not configured")

        self.session = requests.Session()
        self.session.headers.update(
            {
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
            }
        )

    def create_inkaso(
        self,
        amount: float,
        variable_symbol: str,
        recipient_account: str,
        recipient_name: str,
        message: str | None = None,
    ) -> Dict[str, Any]:
        """
        Create an inkaso (direct debit) order.

        This is pseudo‑API; adjust endpoint + payload keys to what your bank uses.
        """
        payload: Dict[str, Any] = {
            "type": "inkaso",
            "from_account": self.account_number,
            "to_account": recipient_account,
            "to_name": recipient_name,
            "amount": round(float(amount), 2),
            "variable_symbol": variable_symbol,
        }
        if message:
            payload["message"] = message

        resp = self.session.post(f"{self.api_url.rstrip('/')}/payments", json=payload, timeout=30)
        resp.raise_for_status()
        return resp.json()





