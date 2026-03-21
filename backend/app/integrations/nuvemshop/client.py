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

    def get_order_custom_fields(self, order_id: str) -> list:
        """
        Busca custom fields associados a um pedido específico.
        Na API Nuvemshop, custom fields vêm de endpoint separado e NÃO estão
        incluídos no objeto do pedido retornado por get_order().
        """
        url = self._url(f"/orders/{order_id}/custom-fields")
        response = requests.get(url, headers=self._headers(), timeout=self.timeout_seconds)
        response.raise_for_status()
        result = response.json()
        return result if isinstance(result, list) else []

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

    def list_products(
        self,
        fields: Optional[str] = None,
        per_page: int = 200,
        page: int = 1,
    ) -> list:
        """
        Lista produtos da loja Nuvemshop com suporte a paginação.

        Args:
            fields: Campos a retornar (ex: "id,variants") — reduz payload
            per_page: Itens por página (máx 200)
            page: Número da página

        Returns:
            Lista de produtos
        """
        params: Dict[str, Any] = {"per_page": per_page, "page": page}
        if fields:
            params["fields"] = fields

        response = requests.get(
            self._url("/products"),
            params=params,
            headers=self._headers(),
            timeout=self.timeout_seconds,
        )
        response.raise_for_status()
        result = response.json()
        return result if isinstance(result, list) else []

    def list_orders(
        self,
        limit: Optional[int] = None,
        since_id: Optional[int] = None,
        status: Optional[str] = None,
        created_at_min: Optional[str] = None,
        created_at_max: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Lista pedidos da loja Nuvemshop.

        Args:
            limit: Número máximo de pedidos a retornar
            since_id: Retornar apenas pedidos com ID maior que este valor
            status: Filtrar por status (open, closed, cancelled, etc)
            created_at_min: Data mínima de criação (formato ISO 8601)
            created_at_max: Data máxima de criação (formato ISO 8601)

        Returns:
            Dict com lista de pedidos e metadados de paginação
        """
        params: Dict[str, Any] = {}
        if limit is not None:
            params["limit"] = limit
        if since_id is not None:
            params["since_id"] = since_id
        if status:
            params["status"] = status
        if created_at_min:
            params["created_at_min"] = created_at_min
        if created_at_max:
            params["created_at_max"] = created_at_max

        response = requests.get(
            self._url("/orders"),
            params=params,
            headers=self._headers(),
            timeout=self.timeout_seconds,
        )
        response.raise_for_status()
        return response.json()
