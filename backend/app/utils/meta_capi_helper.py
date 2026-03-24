# -*- coding: utf-8 -*-
"""
Helper para Meta Conversions API
Função utilitária para criar outbox quando pedido muda para Purchase
"""
from app.models.pedido import Pedido
from app.repositories.meta_capi_outbox_repository import MetaCapiOutboxRepository


def _normalize_source_text(value: str | None) -> str:
    return (value or "").strip().lower()


def should_skip_purchase_for_meta_capi(pedido: Pedido) -> bool:
    """
    Evita duplicação quando a compra já tem tracking próprio.
    """
    fonte_rel = _normalize_source_text(getattr(getattr(pedido, "fonte_pedido_rel", None), "nome", ""))
    fonte_legacy = _normalize_source_text(getattr(pedido, "fonte_pedido", ""))
    plataforma = _normalize_source_text(getattr(pedido, "plataforma", ""))
    canal = _normalize_source_text(getattr(pedido, "canal", ""))

    if fonte_rel == "site" or fonte_legacy == "site" or canal == "site":
        return True

    if plataforma == "nuvemshop":
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
            return True
        return False
    except Exception as e:
        # Não falhar operação principal se houver erro na outbox
        print(f"[AVISO] Erro ao criar outbox para pedido #{pedido.id}: {e}")
        return False
