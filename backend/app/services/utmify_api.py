# -*- coding: utf-8 -*-
"""
Cliente HTTP para API UTMify — POST /api-credentials/orders
Documentação: Integrações > Credenciais de API (UTMify).
"""
from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, Optional

import requests
from zoneinfo import ZoneInfo

from app.models.lead import Lead
from app.models.pedido import Pedido, TIMEZONE_BRASIL, datetime_now_brazil

UTC = ZoneInfo("UTC")


def _to_utc_str(dt: Optional[datetime]) -> Optional[str]:
    if dt is None:
        return None
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=TIMEZONE_BRASIL)
    return dt.astimezone(UTC).strftime("%Y-%m-%d %H:%M:%S")


def map_payment_method(pagamento: Optional[str]) -> str:
    """Mapeia texto livre de pagamento para o enum esperado pela UTMify."""
    if not pagamento:
        return "free_price"
    p = pagamento.lower()
    if "pix" in p:
        return "pix"
    if any(x in p for x in ("cartão", "cartao", "credito", "crédito", "card", "visa", "master")):
        return "credit_card"
    if "boleto" in p:
        return "boleto"
    return "free_price"


def tracking_parameters_from_lead(lead: Optional[Lead]) -> Dict[str, Any]:
    if not lead:
        return {}
    out: Dict[str, Any] = {}
    for key in (
        "src",
        "sck",
        "utm_source",
        "utm_medium",
        "utm_campaign",
        "utm_content",
        "utm_term",
    ):
        val = getattr(lead, key, None)
        if val:
            out[key] = val
    return out


def build_utmify_order_payload(
    pedido: Pedido,
    lead: Optional[Lead],
    *,
    platform: str,
    is_test: bool,
) -> Dict[str, Any]:
    """Monta o body JSON conforme contrato UTMify (venda = status paid)."""
    total_reais = float(pedido.total_pago())
    total_cents = int(round(total_reais * 100))
    qty = max(1, int(pedido.quantidade or 1))
    unit_reais = total_reais / qty if qty else total_reais
    price_in_cents = int(round(unit_reais * 100))

    phone_digits = "".join(c for c in (pedido.telefone_cliente or "") if c.isdigit()) or None

    approved_src = pedido.updated_at or datetime_now_brazil()

    customer: Dict[str, Any] = {
        "name": (pedido.cliente or "").strip() or "Cliente",
        "email": None,
        "phone": phone_digits,
        "document": None,
        "country": "BR",
        "ip": lead.ip_address if lead and lead.ip_address else None,
    }

    payload: Dict[str, Any] = {
        "orderId": str(pedido.id),
        "platform": platform,
        "paymentMethod": map_payment_method(pedido.pagamento),
        "status": "paid",
        "createdAt": _to_utc_str(pedido.created_at),
        "approvedDate": _to_utc_str(approved_src),
        "refundedAt": None,
        "customer": customer,
        "products": [
            {
                "id": str(pedido.id),
                "name": pedido.produto or "Produto",
                "planId": None,
                "planName": None,
                "quantity": qty,
                "priceInCents": price_in_cents,
            }
        ],
        "trackingParameters": tracking_parameters_from_lead(lead),
        "commission": {
            "totalPriceInCents": total_cents,
            "gatewayFeeInCents": 0,
            "userCommissionInCents": total_cents,
            "currency": "BRL",
        },
        "isTest": is_test,
    }
    return payload


def post_utmify_order(
    payload: Dict[str, Any],
    *,
    url: str,
    api_token: str,
    timeout_seconds: float,
) -> Dict[str, Any]:
    """
    Envia pedido para UTMify. Retorno estruturado para log (não levanta exceção).

    Returns:
        dict com ok (bool), status_code (Optional[int]), error (Optional[str])
    """
    headers = {"x-api-token": api_token, "Content-Type": "application/json"}
    try:
        resp = requests.post(url, json=payload, headers=headers, timeout=timeout_seconds)
    except requests.exceptions.Timeout:
        return {
            "ok": False,
            "status_code": None,
            "error": f"timeout após {timeout_seconds}s",
        }
    except requests.exceptions.RequestException as e:
        return {"ok": False, "status_code": None, "error": f"erro de rede: {e}"}

    if 200 <= resp.status_code < 300:
        return {"ok": True, "status_code": resp.status_code, "error": None}

    err_preview = (resp.text or "")[:500]
    return {
        "ok": False,
        "status_code": resp.status_code,
        "error": f"HTTP {resp.status_code}: {err_preview or resp.reason}",
    }
