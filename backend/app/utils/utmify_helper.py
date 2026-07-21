# -*- coding: utf-8 -*-
"""
Hook de venda para UTMify: resolve lead (atribuição) e envia POST best-effort.
"""
from __future__ import annotations

import logging
from typing import Optional, Tuple

from flask import current_app

from app.models.lead import Lead
from app.models.pedido import Pedido
from app.services.utmify_api import build_utmify_order_payload, post_utmify_order

logger = logging.getLogger(__name__)


def extract_fbclid_from_fbc(fbc: Optional[str]) -> Optional[str]:
    """Extrai fbclid do cookie/string _fbc (ex.: fb.1.timestamp.xyz) ou retorna valor cru."""
    if not fbc or not str(fbc).strip():
        return None
    raw = str(fbc).strip()
    parts = raw.split(".")
    if len(parts) >= 4 and parts[0].lower() == "fb":
        return parts[-1]
    return raw


def normalize_phone_digits(phone: Optional[str]) -> Optional[str]:
    if not phone:
        return None
    d = "".join(c for c in phone if c.isdigit())
    return d or None


def resolve_lead_for_pedido(pedido: Pedido) -> Tuple[Optional[Lead], str]:
    """
    Lead mais recente para atribuição, prioridade:
    1) telefone + lead com sck (mais recente entre esses)
    2) fbclid derivado de pedido.fbc
    3) telefone (qualquer lead mais recente)
    """
    phone = normalize_phone_digits(pedido.telefone_cliente)
    fbclid = extract_fbclid_from_fbc(pedido.fbc)

    if phone:
        leads_phone = Lead.query.filter(Lead.phone == phone).order_by(Lead.created_at.desc()).all()
        for lead in leads_phone:
            if lead.sck:
                return lead, "sck"

    if fbclid:
        lead = Lead.query.filter(Lead.fbclid == fbclid).order_by(Lead.created_at.desc()).first()
        if lead:
            return lead, "fbclid"

    if phone:
        lead = Lead.query.filter(Lead.phone == phone).order_by(Lead.created_at.desc()).first()
        if lead:
            return lead, "phone"

    return None, "none"


def _is_purchase_transition(pedido: Pedido, status_pagamento_anterior: Optional[str]) -> bool:
    """Mesma regra de gatilho que Meta CAPI outbox (Pago/Parcial e transição real)."""
    if not pedido.status_pagamento:
        return False
    cur = pedido.status_pagamento.upper().strip()
    if cur not in ("PAGO", "PARCIAL"):
        return False
    if status_pagamento_anterior:
        prev = status_pagamento_anterior.upper().strip()
        if prev in ("PAGO", "PARCIAL"):
            return False
    return True


def send_utmify_if_purchase(
    pedido: Pedido,
    status_anterior: Optional[str] = None,
    status_pagamento_anterior: Optional[str] = None,
) -> bool:
    """
    Envia conversão para UTMify se configurado e se houve transição para pagamento pago/parcial.
    Falhas de rede/API não propagam exceção.

    Args:
        pedido: pedido já persistido (após commit)
        status_anterior: ignorado (compatível com assinatura do hook Meta)
        status_pagamento_anterior: valor do campo antes da atualização

    Returns:
        True se tentou enviar e obteve HTTP 2xx; False caso contrário ou skip.
    """
    from app.services.secure_config import secure_runtime_config

    _ = status_anterior
    with secure_runtime_config(getattr(pedido, "store_ref_id", None)) as tenant_config:
        if not tenant_config.get("UTMIFY_ENABLED"):
            return False
        if not _is_purchase_transition(pedido, status_pagamento_anterior):
            return False

        token = (tenant_config.get("UTMIFY_API_TOKEN") or "").strip()
        if not token:
            logger.warning("[UTMIFY] UTMIFY_ENABLED sem UTMIFY_API_TOKEN — pedido_id=%s", pedido.id)
            return False

        url = (current_app.config.get("UTMIFY_POSTBACK_URL") or "").strip()
        if not url:
            logger.warning("[UTMIFY] UTMIFY_POSTBACK_URL vazio — pedido_id=%s", pedido.id)
            return False

        platform = (tenant_config.get("UTMIFY_PLATFORM") or "WhatsAppManual").strip()
        timeout = float(current_app.config.get("UTMIFY_TIMEOUT_SECONDS") or 5)
        is_test = bool(tenant_config.get("UTMIFY_IS_TEST"))

    lead, match = resolve_lead_for_pedido(pedido)
    payload = build_utmify_order_payload(pedido, lead, platform=platform, is_test=is_test)

    result = post_utmify_order(payload, url=url, api_token=token, timeout_seconds=timeout)

    logger.info(
        "[UTMIFY] pedido_id=%s status_pagamento=%s match=%s http=%s ok=%s",
        pedido.id,
        pedido.status_pagamento,
        match,
        result.get("status_code"),
        result.get("ok"),
    )
    if not result.get("ok"):
        logger.warning(
            "[UTMIFY] falha pedido_id=%s match=%s: %s",
            pedido.id,
            match,
            result.get("error"),
        )

    return bool(result.get("ok"))
