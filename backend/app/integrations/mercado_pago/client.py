# -*- coding: utf-8 -*-
"""Cliente HTTP para a API do Mercado Pago."""

from typing import Any, Dict, Optional

import requests

from app.integrations.mercado_pago.errors import MercadoPagoApiError


class MercadoPagoClient:
    def __init__(
        self,
        access_token: str,
        base_url: str = "https://api.mercadopago.com",
        timeout_seconds: int = 20,
    ) -> None:
        self.access_token = access_token
        self.base_url = base_url.rstrip("/")
        self.timeout_seconds = timeout_seconds

    def _headers(self) -> Dict[str, str]:
        return {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.access_token}",
        }

    def _url(self, path: str) -> str:
        path = path if path.startswith("/") else f"/{path}"
        return f"{self.base_url}{path}"

    def _request(
        self,
        method: str,
        path: str,
        *,
        json_body: Optional[Dict[str, Any]] = None,
        params: Optional[Dict[str, Any]] = None,
    ) -> Any:
        response = requests.request(
            method,
            self._url(path),
            headers=self._headers(),
            json=json_body,
            params=params,
            timeout=self.timeout_seconds,
        )

        payload: Any = None
        if response.status_code != 204 and response.text:
            try:
                payload = response.json()
            except Exception:
                payload = {"raw_text": response.text[:2000]}

        if response.status_code >= 400:
            msg = "Erro na API Mercado Pago"
            if isinstance(payload, dict):
                msg = payload.get("message") or payload.get("error") or msg
            raise MercadoPagoApiError(msg, status_code=response.status_code, payload=payload)

        return payload if payload is not None else {"status_code": response.status_code}

    def get(self, path: str, params: Optional[Dict[str, Any]] = None) -> Any:
        return self._request("GET", path, params=params)

    def post(self, path: str, payload: Optional[Dict[str, Any]] = None) -> Any:
        return self._request("POST", path, json_body=payload or {})

    def delete(self, path: str) -> Any:
        return self._request("DELETE", path)

    def get_payment(self, payment_id: str) -> Any:
        return self.get(f"/v1/payments/{payment_id}")

    def create_webhook(self, url: str, secret: str) -> Any:
        return self.post(
            "/webhooks",
            {
                "url": url,
                "events": [{"type": "payment"}],
                "secret": secret,
            },
        )

    def list_webhooks(self) -> Any:
        return self.get("/webhooks")

    def delete_webhook(self, webhook_id: str) -> Any:
        return self.delete(f"/webhooks/{webhook_id}")
