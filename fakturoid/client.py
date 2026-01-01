from __future__ import annotations

from datetime import date
from typing import Any, Dict, List, Optional

import requests

from config.settings import (
    FAKTUROID_CLIENT_ID,
    FAKTUROID_CLIENT_SECRET,
    FAKTUROID_SLUG,
    FAKTUROID_USER_AGENT,
)


class FakturoidClient:
    """
    Minimal Fakturoid v3 client – only what we need for invoices.
    Uses OAuth2 client_credentials with client_id/client_secret.
    Docs: https://www.fakturoid.cz/api/v3
    """

    BASE_URL = "https://app.fakturoid.cz/api/v3"
    TOKEN_URL = "https://app.fakturoid.cz/api/v3/oauth/token"

    def __init__(
        self,
        slug: Optional[str] = None,
        client_id: Optional[str] = None,
        client_secret: Optional[str] = None,
        user_agent: Optional[str] = None,
    ) -> None:
        self.slug = slug or FAKTUROID_SLUG
        self.client_id = client_id or FAKTUROID_CLIENT_ID
        self.client_secret = client_secret or FAKTUROID_CLIENT_SECRET
        self.user_agent = user_agent or FAKTUROID_USER_AGENT

        if not (self.slug and self.client_id and self.client_secret):
            raise RuntimeError("Fakturoid OAuth2 credentials missing in environment/config")

        self.session = requests.Session()
        self.session.headers.update(
            {
                "User-Agent": self.user_agent,
                "Accept": "application/json",
            }
        )

        self._access_token: Optional[str] = None
        self._token_type: str = "Bearer"

    def _url(self, path: str) -> str:
        return f"{self.BASE_URL}/accounts/{self.slug}{path}"

    def _ensure_token(self) -> None:
        if self._access_token is not None:
            return

        data = {"grant_type": "client_credentials"}
        headers = {"Content-Type": "application/x-www-form-urlencoded"}
        # HTTP Basic auth with client_id:client_secret, as per docs
        resp = self.session.post(
            self.TOKEN_URL,
            data=data,
            headers=headers,
            auth=(self.client_id, self.client_secret),
            timeout=30,
        )
        resp.raise_for_status()
        payload = resp.json()
        token = payload.get("access_token")
        if not token:
            raise RuntimeError(f"Failed to obtain Fakturoid access token: {payload!r}")
        self._access_token = token
        # e.g. "Bearer" – use whatever server returns
        self._token_type = (payload.get("token_type") or "Bearer").strip()

    def _auth_headers(self) -> Dict[str, str]:
        self._ensure_token()
        return {"Authorization": f"{self._token_type} {self._access_token}"}

    def list_invoices(
        self,
        since: Optional[date] = None,
        until: Optional[date] = None,
        status: str = "paid",
        page: int = 1,
    ) -> List[Dict[str, Any]]:
        """
        Fetch invoices with basic filtering.
        You can loop over pages while response is non-empty.
        """
        params: Dict[str, Any] = {"page": page}
        if status:
            params["status"] = status
        if since:
            params["since"] = since.isoformat()
        if until:
            params["until"] = until.isoformat()

        headers = {**self.session.headers, **self._auth_headers()}
        resp = self.session.get(
            self._url("/invoices.json"),
            headers=headers,
            params=params,
            timeout=30,
        )
        resp.raise_for_status()
        data = resp.json()
        if not isinstance(data, list):
            raise RuntimeError(f"Unexpected invoices response: {data!r}")
        return data

    def iter_invoices(
        self,
        since: Optional[date] = None,
        until: Optional[date] = None,
        status: str = "paid",
    ) -> List[Dict[str, Any]]:
        """
        Convenience: pull all pages into one list.
        For bigger volumes you might want a generator instead.
        """
        page = 1
        all_invoices: List[Dict[str, Any]] = []
        while True:
            chunk = self.list_invoices(since=since, until=until, status=status, page=page)
            if not chunk:
                break
            all_invoices.extend(chunk)
            page += 1
        return all_invoices


