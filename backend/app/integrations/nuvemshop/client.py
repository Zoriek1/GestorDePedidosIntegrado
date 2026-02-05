"""
Cliente HTTP para API Nuvemshop.
"""

from typing import Any, Dict, Optional

import requests

DEFAULT_API_VERSION = "2025-03"
DEFAULT_BASE_URL = "https://api.nuvemshop.com.br"


class NuvemshopClient:
    def __init__(
        self,
        store_id: str,
        access_token: str,
        user_agent: str,
        base_url: str = DEFAULT_BASE_URL,
        api_version: str = DEFAULT_API_VERSION,
        timeout_seconds: int = 20,
    ) -> None:
        self.store_id = str(store_id)
        self.access_token = access_token
        self.user_agent = user_agent
        self.base_url = base_url.rstrip("/")
        self.api_version = api_version
        self.timeout_seconds = timeout_seconds

    def _headers(self) -> Dict[str, str]:
        return {
            "Authentication": f"bearer {self.access_token}",
            "User-Agent": self.user_agent,
            "Content-Type": "application/json",
        }

    def _url(self, path: str) -> str:
        return f"{self.base_url}/{self.api_version}/{self.store_id}{path}"

    def get_order(self, order_id: str) -> Dict[str, Any]:
        url = self._url(f"/orders/{order_id}")
        response = requests.get(url, headers=self._headers(), timeout=self.timeout_seconds)
        response.raise_for_status()
        return response.json()

    def create_webhook(self, event: str, url: str) -> Dict[str, Any]:
        payload = {"event": event, "url": url}
        response = requests.post(
            self._url("/webhooks"),
            json=payload,
            headers=self._headers(),
            timeout=self.timeout_seconds,
        )
        response.raise_for_status()
        return response.json()

    def list_webhooks(self, event: Optional[str] = None) -> Dict[str, Any]:
        params: Dict[str, Any] = {}
        if event:
            params["event"] = event
        response = requests.get(
            self._url("/webhooks"),
            params=params,
            headers=self._headers(),
            timeout=self.timeout_seconds,
        )
        response.raise_for_status()
        return response.json()
