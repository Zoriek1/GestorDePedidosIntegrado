# -*- coding: utf-8 -*-
"""
CommissionService — gera entries de comissão ao fechar um pedido
"""
from __future__ import annotations

import unicodedata
from datetime import date, datetime, timedelta


def map_fonte_to_source(nome: str) -> str:
    """
    Normaliza o nome da fonte do pedido para o código usado em commission_config.source.

    Exemplos:
        "WhatsApp" → "whatsapp"
        "Balcão"   → "balcao"
        "Site"     → "site"
        "Indicação" → "indicacao"
    """
    if not nome:
        return ""
    nfkd = unicodedata.normalize("NFD", nome)
    ascii_name = "".join(c for c in nfkd if unicodedata.category(c) != "Mn")
    return ascii_name.lower().strip().replace(" ", "_")


def get_monday(ref_date) -> date:
    """Retorna a segunda-feira da semana da data fornecida."""
    from app.utils.date_utils import get_monday as _get_monday
    from app.utils.date_utils import today_brazil

    if isinstance(ref_date, datetime):
        ref_date = ref_date.date()
    if ref_date is None:
        ref_date = today_brazil()
    return _get_monday(ref_date)


def get_due_date_for_commission(dia_entrega: date, payment_day: int) -> date:
    """
    Calcula a due_date de uma comissão usando a lógica PgtDay:

    - Se dia_entrega < PgtDay desta semana  → receber neste PgtDay
    - Se dia_entrega >= PgtDay desta semana → receber no próximo PgtDay

    payment_day: 0=Seg, 1=Ter, 2=Qua, 3=Qui, 4=Sex, 5=Sáb, 6=Dom
    """
    monday = dia_entrega - timedelta(days=dia_entrega.weekday())
    pgt_this_week = monday + timedelta(days=payment_day)

    if dia_entrega < pgt_this_week:
        return pgt_this_week
    else:
        return pgt_this_week + timedelta(weeks=1)


def resolve_commission_reference_date(pedido) -> date:
    """
    Define a data de referência da comissão:
    - Usa paid_at se disponível (data real de pagamento, imutável).
    - Fallback: created_at.
    - Fallback final: date.today().
    """
    paid_at = getattr(pedido, "paid_at", None)
    if paid_at:
        return paid_at.date() if isinstance(paid_at, datetime) else paid_at

    created_at = getattr(pedido, "created_at", None)
    if created_at:
        return created_at.date() if isinstance(created_at, datetime) else created_at

    dia_entrega = getattr(pedido, "dia_entrega", None)
    if isinstance(dia_entrega, date):
        return dia_entrega

    from app.utils.date_utils import today_brazil

    return today_brazil()


def commission_base(pedido) -> float:
    """
    Retorna o valor líquido usado como base de cálculo da comissão.

    - Retirada: valor bruto − taxa_cartao_valor.
    - Entrega:  valor bruto − taxa_entrega − taxa_cartao_valor (nunca negativo).

    taxa_cartao_valor é um snapshot gravado no save do pedido (ver
    services/taxa_cartao.aplicar_taxa_cartao_snapshot), garantindo que
    mudanças posteriores na config global não recalculem comissões antigas.
    """
    from flask import current_app

    valor = pedido.total_pago()
    taxa_cartao = float(getattr(pedido, "taxa_cartao_valor", None) or 0.0)
    tipo = (getattr(pedido, "tipo_pedido", None) or "Entrega").strip()

    if tipo.lower() == "retirada":
        base = max(0.0, valor - taxa_cartao)
        if taxa_cartao > valor:
            current_app.logger.warning(
                "[COMISSAO] taxa_cartao (%.2f) > valor (%.2f) no pedido #%s — base zerada",
                taxa_cartao,
                valor,
                getattr(pedido, "id", "?"),
            )
        return base

    taxa_entrega = float(getattr(pedido, "taxa_entrega", None) or 0.0)
    base = max(0.0, valor - taxa_entrega - taxa_cartao)
    if (taxa_entrega + taxa_cartao) > valor:
        current_app.logger.warning(
            "[COMISSAO] taxa_entrega+taxa_cartao (%.2f) > valor (%.2f) no pedido #%s — base zerada",
            taxa_entrega + taxa_cartao,
            valor,
            getattr(pedido, "id", "?"),
        )
    return base


def generate_commission(pedido, vendedor_id: int, reference_date: date | None = None) -> None:
    """
    Gera entry de comissão no ledger ao fechar um pedido.

    Idempotente: se já existe entry ativa para esse pedido_id, não cria duplicata.
    Não processa pedidos com source='lucro_bruto' (placeholder).
    """
    from flask import current_app

    from app import db
    from app.models.ledger_entry import LedgerEntry
    from app.repositories.ledger_repository import LedgerRepository
    from app.repositories.user_repository import UserRepository

    ledger_repo = LedgerRepository()
    user_repo = UserRepository()

    # 1. Idempotência — verifica entry não-voidada
    if ledger_repo.get_by_pedido_id(pedido.id):
        return

    # 2. Determinar fonte do pedido (preferência: fonte real)
    fonte_pedido_id = getattr(pedido, "fonte_pedido_id", None)
    fonte_nome = ""
    if getattr(pedido, "fonte_pedido_rel", None):
        fonte_nome = pedido.fonte_pedido_rel.nome or ""
    elif getattr(pedido, "fonte_pedido", None):
        fonte_nome = pedido.fonte_pedido or ""

    source = map_fonte_to_source(fonte_nome)

    # 3. Buscar config de comissão
    config = user_repo.get_active_commission(
        user_id=vendedor_id,
        fonte_pedido_id=fonte_pedido_id,
        source=source or None,
    )
    if not config:
        current_app.logger.warning(
            "[COMISSAO] Pedido #%s sem CommissionConfig ativa "
            "(vendedor=%s fonte_pedido_id=%s source=%r); comissão pulada.",
            pedido.id,
            vendedor_id,
            fonte_pedido_id,
            source,
        )
        return

    # Compatibilidade com placeholder legado
    config_source = (config.source or "").strip()
    if config_source == "lucro_bruto":
        return

    # 4. Calcular base líquida
    base = commission_base(pedido)
    if base <= 0:
        return

    commission_amount = round(base * config.rate, 2)
    if commission_amount <= 0:
        return

    # 5. Semana de referência e due_date com payment_day configurado
    ref_date = reference_date or resolve_commission_reference_date(pedido)
    week_ref = get_monday(ref_date)

    payroll_configs = user_repo.get_payroll_configs(vendedor_id)
    semanal_config = next(
        (c for c in payroll_configs if c.frequency == "semanal" and c.payment_day is not None),
        None,
    )
    due_date = (
        get_due_date_for_commission(ref_date, semanal_config.payment_day)
        if semanal_config
        else ref_date
    )

    # 6. Criar entry (com snapshot da rate/source para estorno estável)
    category_source = config_source or source or "fonte"
    category = f"comissao_{category_source}"
    entry = LedgerEntry(
        user_id=vendedor_id,
        type="CREDIT",
        category=category,
        amount=commission_amount,
        description=f"Comissão {config.rate * 100:.0f}% — Pedido #{pedido.id}",
        pedido_id=pedido.id,
        week_ref=week_ref,
        due_date=due_date,
        status="active",
        commission_rate=config.rate,
        commission_source=category_source,
        created_by=vendedor_id,
    )
    db.session.add(entry)
    db.session.flush()
    current_app.logger.info(
        "[COMISSAO] Pedido #%s: R$%.2f (%s) → user %s",
        pedido.id,
        commission_amount,
        category,
        vendedor_id,
    )


def void_and_recreate_commission(pedido, vendedor_id: int) -> None:
    """
    Estorna a comissão ativa de um pedido (voided=True + DEBIT de ajuste)
    e cria nova comissão com os valores atuais.

    Chamado quando campos que afetam comissão são alterados em pedido já comissionado:
    vendedor_id, fonte_pedido, valor, tipo_pedido, taxa_entrega.
    """
    from flask import current_app

    from app import db
    from app.models.ledger_entry import LedgerEntry, datetime_now_brazil
    from app.repositories.ledger_repository import LedgerRepository

    ledger_repo = LedgerRepository()
    existing = ledger_repo.get_active_by_pedido_id(pedido.id)
    if not existing:
        # Nenhuma comissão ativa — gerar normalmente
        generate_commission(pedido, vendedor_id)
        return

    old_amount = float(existing.amount)
    old_week_ref = existing.week_ref
    # Snapshot fields preservam a config histórica (rate/source no momento original)
    old_rate = existing.commission_rate
    old_source = existing.commission_source

    # Marcar entry antiga como void
    existing.voided = True
    existing.void_reason = "edit_estorno"
    db.session.flush()

    # Criar DEBIT de estorno (categoria ajuste_debito é excluída do saldo —
    # serve apenas para auditoria do estorno)
    debit = LedgerEntry(
        user_id=existing.user_id,
        type="DEBIT",
        category="ajuste_debito",
        amount=old_amount,
        description=f"Estorno comissão Pedido #{pedido.id} (edição)",
        week_ref=old_week_ref,
        status="settled",
        settled_at=datetime_now_brazil(),
        commission_rate=old_rate,
        commission_source=old_source,
        created_by=vendedor_id,
    )
    db.session.add(debit)
    db.session.flush()

    current_app.logger.info(
        "[COMISSAO] Estorno Pedido #%s: R$%.2f voidado (rate=%s source=%s), " "DEBIT ajuste criado",
        pedido.id,
        old_amount,
        old_rate,
        old_source,
    )

    # Gerar nova comissão com valores atuais
    generate_commission(pedido, vendedor_id)


def void_active_commission(pedido, reason: str) -> bool:
    """
    Marca o CREDIT ativo do pedido como voided, sem criar DEBIT.

    Usado quando o pedido sai do estado pago (regressão de status) ou é
    soft-deletado: o valor não foi realmente entregue ao vendedor, então o
    void simplesmente remove o crédito do saldo. Nenhuma contrapartida é
    necessária.

    Returns: True se voidou um CREDIT, False se não havia CREDIT ativo.
    """
    from flask import current_app

    from app import db
    from app.repositories.ledger_repository import LedgerRepository

    existing = LedgerRepository().get_active_by_pedido_id(pedido.id)
    if not existing:
        return False

    existing.voided = True
    existing.void_reason = reason
    db.session.flush()

    current_app.logger.info(
        "[COMISSAO] Pedido #%s: CREDIT R$%.2f voidado (reason=%s)",
        pedido.id,
        float(existing.amount),
        reason,
    )
    return True
