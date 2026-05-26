# -*- coding: utf-8 -*-
"""
Helper para Meta Conversions API
Função utilitária para criar outbox quando pedido é criado (Purchase imediato).
"""
import logging

from app.models.pedido import Pedido
from app.repositories.meta_capi_outbox_repository import MetaCapiOutboxRepository

logger = logging.getLogger(__name__)


def try_flush_pending_meta_capi_for_order(order_id: int) -> None:
    """
    Envia imediatamente o registro pending da outbox para a Meta (se existir).
    Falhas não propagam: o agendador continua como fallback.
    """
    try:
        from app.commands.send_daily_purchases_to_meta_command import (
            SendDailyPurchasesToMetaCommand,
        )

        repo = MetaCapiOutboxRepository()
        entry = repo.get_by_order_id(order_id)
        if not entry or entry.status != "pending":
            return

        cmd = SendDailyPurchasesToMetaCommand()
        stats = {
            "sent_success": 0,
            "sent_failed": 0,
            "failed_permanent": 0,
            "errors": [],
        }
        cmd._send_batch([entry], stats)
        logger.info(
            "meta_capi.flush_immediate",
            extra={
                "pedido_id": order_id,
                "event_id": f"order_{order_id}",
                "sent_success": stats["sent_success"],
                "sent_failed": stats["sent_failed"],
                "failed_permanent": stats["failed_permanent"],
            },
        )
    except Exception as e:
        logger.exception(
            "meta_capi.flush_immediate_failed",
            extra={"pedido_id": order_id, "error": str(e)},
        )


def _normalize_source_text(value: str | None) -> str:
    return (value or "").strip().lower()


# Fontes/canais com tracking próprio (pixel da Nuvemshop, etc).
# Enviar Purchase via CAPI duplica conversões — pular sempre.
_SKIP_SOURCE_TOKENS = ("site", "nuvemshop", "nuvem shop", "loja virtual")


def _matches_skip_token(value: str) -> bool:
    return any(token in value for token in _SKIP_SOURCE_TOKENS)


def should_skip_purchase_for_meta_capi(pedido: Pedido) -> bool:
    """
    Evita duplicação quando a compra já tem tracking próprio (pixel do site /
    Nuvemshop). Cobre tanto a fonte (Site/Nuvemshop) quanto a plataforma/canal.
    """
    fonte_rel = _normalize_source_text(
        getattr(getattr(pedido, "fonte_pedido_rel", None), "nome", "")
    )
    fonte_legacy = _normalize_source_text(getattr(pedido, "fonte_pedido", ""))
    plataforma = _normalize_source_text(getattr(pedido, "plataforma", ""))
    canal = _normalize_source_text(getattr(pedido, "canal", ""))

    for value in (fonte_rel, fonte_legacy, plataforma, canal):
        if value and _matches_skip_token(value):
            return True

    return False


def _resolve_fonte_label(pedido: Pedido) -> str | None:
    rel_name = getattr(getattr(pedido, "fonte_pedido_rel", None), "nome", None)
    return rel_name or getattr(pedido, "fonte_pedido", None)


def create_outbox_for_new_order(pedido: Pedido) -> bool:
    """
    Enfileira Purchase CAPI no ato da criação do pedido.

    - Roda independente de `status_pagamento` (envio na criação, não no pagamento).
    - Exclui fontes com pixel próprio (site/Nuvemshop) via `should_skip_purchase_for_meta_capi`.
    - Idempotente: se já existir outbox para o `event_id` (`order_<id>`), não recria.
    - Após enfileirar, tenta envio imediato via `try_flush_pending_meta_capi_for_order`.
    """
    fonte = _resolve_fonte_label(pedido)

    if should_skip_purchase_for_meta_capi(pedido):
        logger.info(
            "meta_capi.skip",
            extra={
                "pedido_id": pedido.id,
                "reason": "fonte_site_or_nuvemshop",
                "fonte": fonte,
            },
        )
        return False

    try:
        repo = MetaCapiOutboxRepository()
        if repo.get_by_order_id(pedido.id):
            logger.info(
                "meta_capi.skip",
                extra={
                    "pedido_id": pedido.id,
                    "reason": "already_enqueued",
                    "fonte": fonte,
                },
            )
            return False

        repo.create_from_pedido(pedido)
        logger.info(
            "meta_capi.enqueued",
            extra={
                "pedido_id": pedido.id,
                "event_id": f"order_{pedido.id}",
                "fonte": fonte,
                "fbp_present": bool(getattr(pedido, "fbp", None)),
                "fbc_present": bool(getattr(pedido, "fbc", None)),
                "phone_present": bool(getattr(pedido, "telefone_cliente", None)),
            },
        )
        try_flush_pending_meta_capi_for_order(pedido.id)
        return True
    except Exception as e:
        logger.exception(
            "meta_capi.enqueue_failed",
            extra={"pedido_id": pedido.id, "fonte": fonte, "error": str(e)},
        )
        return False


def create_outbox_if_purchase(
    pedido: Pedido, status_anterior: str = None, status_pagamento_anterior: str = None
) -> bool:
    """
    DEPRECATED — Purchase agora dispara na criação via `create_outbox_for_new_order`.

    Mantida para compatibilidade com testes e código legado que possa importar a função.
    Não é mais chamada nos endpoints de update de status/pagamento.
    """
    if not pedido.status_pagamento:
        return False

    status_pagamento_upper = pedido.status_pagamento.upper().strip()
    if status_pagamento_upper not in ["PAGO", "PARCIAL"]:
        return False

    if should_skip_purchase_for_meta_capi(pedido):
        logger.info(
            "meta_capi.skip",
            extra={
                "pedido_id": pedido.id,
                "reason": "fonte_site_or_nuvemshop",
                "fonte": _resolve_fonte_label(pedido),
                "via": "legacy_if_purchase",
            },
        )
        return False

    if status_pagamento_anterior:
        status_anterior_upper = status_pagamento_anterior.upper().strip()
        if status_anterior_upper in ["PAGO", "PARCIAL"]:
            return False

    try:
        outbox_repo = MetaCapiOutboxRepository()
        existing = outbox_repo.get_by_order_id(pedido.id)
        if not existing:
            outbox_repo.create_from_pedido(pedido)
            logger.info(
                "meta_capi.enqueued",
                extra={
                    "pedido_id": pedido.id,
                    "event_id": f"order_{pedido.id}",
                    "fonte": _resolve_fonte_label(pedido),
                    "via": "legacy_if_purchase",
                },
            )
            try_flush_pending_meta_capi_for_order(pedido.id)
            return True
        return False
    except Exception as e:
        logger.exception(
            "meta_capi.enqueue_failed",
            extra={"pedido_id": pedido.id, "error": str(e), "via": "legacy_if_purchase"},
        )
        return False
