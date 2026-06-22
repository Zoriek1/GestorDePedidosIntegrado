# -*- coding: utf-8 -*-
"""Cliente HTTP para a API Bling v3."""

from typing import Any, Callable, Dict, Optional

import requests

from app.integrations.bling.errors import BlingApiError


class BlingClient:
    def __init__(
        self,
        access_token: str,
        base_url: str,
        timeout_seconds: int = 20,
        on_unauthorized: Optional[Callable[[], Optional[str]]] = None,
    ) -> None:
        self.access_token = access_token
        self.base_url = base_url.rstrip("/")
        self.timeout_seconds = timeout_seconds
        # Hook chamado em um 401: refresca o token e devolve o novo access_token.
        self.on_unauthorized = on_unauthorized

    def _headers(self) -> Dict[str, str]:
        return {
            "Accept": "application/json",
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.access_token}",
            "enable-jwt": "1",
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
        _retried: bool = False,
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

        if response.status_code == 401 and self.on_unauthorized and not _retried:
            # Token pode ter sido revogado antes de expirar: refresca e tenta 1x.
            new_token = self.on_unauthorized()
            if new_token:
                self.access_token = new_token
            return self._request(
                method, path, json_body=json_body, params=params, _retried=True
            )

        if response.status_code >= 400:
            raise BlingApiError(
                self._error_message(payload),
                status_code=response.status_code,
                payload=payload,
            )

        return payload if payload is not None else {"status_code": response.status_code}

    @staticmethod
    def _error_message(payload: Any) -> str:
        """Monta uma mensagem util a partir do erro do Bling, incluindo os
        campos de validacao (error.fields) que dizem exatamente o que falhou."""
        default = "Erro na API Bling"
        if not isinstance(payload, dict):
            return default
        error = payload.get("error")
        if not isinstance(error, dict):
            return payload.get("message") or payload.get("error") or default
        parts = [error.get("message") or default]
        if error.get("description"):
            parts.append(str(error["description"]))
        fields = error.get("fields")
        if isinstance(fields, list):
            for field in fields:
                if isinstance(field, dict):
                    element = field.get("element") or field.get("name") or "?"
                    msg = field.get("msg") or field.get("message") or ""
                    parts.append(f"{element}: {msg}".strip())
        return " | ".join(p for p in parts if p)

    def get(self, path: str, params: Optional[Dict[str, Any]] = None) -> Any:
        return self._request("GET", path, params=params)

    def post(self, path: str, payload: Optional[Dict[str, Any]] = None) -> Any:
        return self._request("POST", path, json_body=payload or {})

    def put(self, path: str, payload: Optional[Dict[str, Any]] = None) -> Any:
        return self._request("PUT", path, json_body=payload or {})

    def delete(self, path: str) -> Any:
        return self._request("DELETE", path)

    def create_order(self, payload: Dict[str, Any]) -> Any:
        return self.post("/pedidos/vendas", payload)

    def list_orders_by_store_number(self, numero_loja: str) -> Any:
        return self.get("/pedidos/vendas", params={"numerosLojas[]": numero_loja})

    def launch_order_accounts(self, order_id: str) -> Any:
        return self.post(f"/pedidos/vendas/{order_id}/lancar-contas")

    def list_receivables(self, params: Optional[Dict[str, Any]] = None) -> Any:
        return self.get("/contas/receber", params=params or {})

    def settle_receivable(self, receivable_id: str, payload: Dict[str, Any]) -> Any:
        return self.post(f"/contas/receber/{receivable_id}/baixar", payload)

    def search_products(self, params: Optional[Dict[str, Any]] = None) -> Any:
        return self.get("/produtos", params=params or {})

    def create_product(self, payload: Dict[str, Any]) -> Any:
        return self.post("/produtos", payload)

    def list_payment_methods(self) -> Any:
        return self.get("/formas-pagamentos", params={"situacao": 1})

    def list_financial_accounts(self) -> Any:
        return self.get("/contas-contabeis")

    def list_categories(self) -> Any:
        return self.get("/categorias/receitas-despesas")
