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
    if isinstance(ref_date, datetime):
        ref_date = ref_date.date()
    if ref_date is None:
        ref_date = date.today()
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

    return date.today()


def commission_base(pedido) -> float:
    """
    Retorna o valor líquido usado como base de cálculo da comissão.

    - Retirada: valor bruto do pedido (sem taxa de entrega).
    - Entrega:  valor bruto − taxa_entrega (nunca negativo).
    """
    from flask import current_app

    valor = pedido.total_pago()
    tipo = (getattr(pedido, "tipo_pedido", None) or "Entrega").strip()
    if tipo.lower() == "retirada":
        return valor
    taxa = float(getattr(pedido, "taxa_entrega", None) or 0.0)
    base = max(0.0, valor - taxa)
    if taxa > valor:
        current_app.logger.warning(
            "[COMISSAO] taxa_entrega (%.2f) > valor (%.2f) no pedido #%s — base zerada",
            taxa, valor, getattr(pedido, "id", "?"),
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
    if ledger_repo.get_active_by_pedido_id(pedido.id):
        return

    # 2. Determinar fonte do pedido
    fonte_nome = ""
    if pedido.fonte_pedido_rel:
        fonte_nome = pedido.fonte_pedido_rel.nome or ""
    elif pedido.fonte_pedido:
        fonte_nome = pedido.fonte_pedido or ""

    source = map_fonte_to_source(fonte_nome)
    if not source:
        return

    if source == "lucro_bruto":
        return

    # 3. Buscar config de comissão
    config = user_repo.get_active_commission(user_id=vendedor_id, source=source)
    if not config:
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

    # 6. Criar entry
    category = f"comissao_{source}"
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
        created_by=vendedor_id,
    )
    db.session.add(entry)
    db.session.commit()
    current_app.logger.info(
        "[COMISSAO] Pedido #%s: R$%.2f (%s) → user %s",
        pedido.id, commission_amount, category, vendedor_id,
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
    from app.models.ledger_entry import LedgerEntry
    from app.repositories.ledger_repository import LedgerRepository
    from app.utils.date_utils import get_monday

    ledger_repo = LedgerRepository()
    existing = ledger_repo.get_active_by_pedido_id(pedido.id)
    if not existing:
        # Nenhuma comissão ativa — gerar normalmente
        generate_commission(pedido, vendedor_id)
        return

    old_amount = float(existing.amount)
    old_week_ref = existing.week_ref

    # Marcar entry antiga como void
    existing.voided = True
    db.session.flush()

    # Criar DEBIT de estorno
    debit = LedgerEntry(
        user_id=existing.user_id,
        type="DEBIT",
        category="ajuste_debito",
        amount=old_amount,
        description=f"Estorno comissão Pedido #{pedido.id} (edição)",
        week_ref=old_week_ref,
        status="settled",
        created_by=vendedor_id,
    )
    db.session.add(debit)
    db.session.commit()

    current_app.logger.info(
        "[COMISSAO] Estorno Pedido #%s: R$%.2f voidado, DEBIT ajuste criado",
        pedido.id, old_amount,
    )

    # Gerar nova comissão com valores atuais
    generate_commission(pedido, vendedor_id)
