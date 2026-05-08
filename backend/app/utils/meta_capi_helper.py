# -*- coding: utf-8 -*-
"""
Helper para Meta Conversions API
Função utilitária para criar outbox quando pedido muda para Purchase
"""
from app.models.pedido import Pedido
from app.repositories.meta_capi_outbox_repository import MetaCapiOutboxRepository


def try_flush_pending_meta_capi_for_order(order_id: int) -> None:
    """
    Envia imediatamente o registro pending da outbox para a Meta (se existir).
    Falhas não propagam: o agendador diário continua como fallback.
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
    except Exception as e:
        print(f"[AVISO] Meta CAPI envio imediato falhou para pedido #{order_id}: {e}")


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


def create_outbox_if_purchase(
    pedido: Pedido, status_anterior: str = None, status_pagamento_anterior: str = None
) -> bool:
    """
    Cria registro na outbox se pedido é Purchase (status_pagamento = Pago ou Parcial)

    Args:
        pedido: Objeto Pedido
        status_anterior: Status anterior (opcional, para verificar se realmente mudou)
        status_pagamento_anterior: Status de pagamento anterior (opcional)

    Returns:
        bool: True se outbox foi criada, False caso contrário
    """
    # Verificar se é Purchase: apenas status_pagamento="Pago" ou "Parcial" (case-insensitive)
    # Não verificar status="concluido" porque pode agendar pedido para ano que vem
    if not pedido.status_pagamento:
        return False

    status_pagamento_upper = pedido.status_pagamento.upper().strip()
    if status_pagamento_upper not in ["PAGO", "PARCIAL"]:
        return False

    if should_skip_purchase_for_meta_capi(pedido):
        print(f"[META_CAPI] Ignorando pedido #{pedido.id} por origem site/nuvemshop")
        return False

    # Se status_pagamento_anterior fornecido, verificar se realmente mudou
    # Só criar se NÃO estava já Pago ou Parcial antes
    if status_pagamento_anterior:
        status_anterior_upper = status_pagamento_anterior.upper().strip()
        if status_anterior_upper in ["PAGO", "PARCIAL"]:
            # Já estava pago, não criar novamente
            return False

    try:
        outbox_repo = MetaCapiOutboxRepository()
        # Verificar se já existe (evitar duplicação)
        existing = outbox_repo.get_by_order_id(pedido.id)
        if not existing:
            outbox_repo.create_from_pedido(pedido)
            print(f"[META_CAPI] Outbox criada para pedido #{pedido.id}")
            try_flush_pending_meta_capi_for_order(pedido.id)
            return True
        return False
    except Exception as e:
        # Não falhar operação principal se houver erro na outbox
        print(f"[AVISO] Erro ao criar outbox para pedido #{pedido.id}: {e}")
        return False
