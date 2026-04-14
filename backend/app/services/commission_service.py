# -*- coding: utf-8 -*-
"""
CommissionService — gera entries de comissão ao fechar um pedido
"""
from __future__ import annotations

import unicodedata
from datetime import date, datetime


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
    # Remover acentos (NFD + keep ASCII)
    nfkd = unicodedata.normalize("NFD", nome)
    ascii_name = "".join(c for c in nfkd if unicodedata.category(c) != "Mn")
    return ascii_name.lower().strip().replace(" ", "_")


def get_monday(ref_date) -> date:
    """Retorna a segunda-feira da semana da data fornecida."""
    if isinstance(ref_date, datetime):
        ref_date = ref_date.date()
    if ref_date is None:
        from datetime import date as _date
        ref_date = _date.today()
    return ref_date - __import__("datetime").timedelta(days=ref_date.weekday())


def get_due_date_for_commission(dia_entrega: date, payment_day: int) -> date:
    """
    Calcula a due_date de uma comissão usando a lógica PgtDay:

    - Se dia_entrega < PgtDay desta semana  → receber neste PgtDay
    - Se dia_entrega >= PgtDay desta semana → receber no próximo PgtDay

    payment_day: 0=Seg, 1=Ter, 2=Qua, 3=Qui, 4=Sex, 5=Sáb, 6=Dom
    """
    from datetime import timedelta

    monday = dia_entrega - timedelta(days=dia_entrega.weekday())
    pgt_this_week = monday + timedelta(days=payment_day)

    if dia_entrega < pgt_this_week:
        return pgt_this_week
    else:
        return pgt_this_week + timedelta(weeks=1)


def generate_commission(pedido, vendedor_id: int) -> None:
    """
    Gera entry de comissão no ledger ao fechar um pedido.

    Idempotente: se já existe entry para esse pedido_id, não cria duplicata.
    Não processa pedidos com source='lucro_bruto' (placeholder).
    """
    from app import db
    from app.models.ledger_entry import LedgerEntry
    from app.repositories.ledger_repository import LedgerRepository
    from app.repositories.user_repository import UserRepository

    ledger_repo = LedgerRepository()
    user_repo = UserRepository()

    # 1. Idempotência
    if ledger_repo.get_by_pedido_id(pedido.id):
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

    # 3. Placeholder lucro_bruto — não calcular automaticamente
    if source == "lucro_bruto":
        return

    # 4. Buscar config de comissão
    config = user_repo.get_active_commission(user_id=vendedor_id, source=source)
    if not config:
        return

    # 5. Calcular valor (usa total_pago() que já faz parse_brl_money)
    valor = pedido.total_pago()
    if valor <= 0:
        return

    commission_amount = round(valor * config.rate, 2)
    if commission_amount <= 0:
        return

    # 6. Semana de referência e due_date com lógica PgtDay
    ref_date = pedido.dia_entrega if isinstance(pedido.dia_entrega, date) else date.today()
    week_ref = get_monday(ref_date)

    # Buscar payment_day do vendedor para calcular PgtDay
    due_date = None
    payroll_configs = user_repo.get_payroll_configs(vendedor_id)
    semanal_config = next(
        (c for c in payroll_configs if c.frequency == "semanal" and c.payment_day is not None),
        None,
    )
    if semanal_config is not None:
        due_date = get_due_date_for_commission(ref_date, semanal_config.payment_day)

    # 7. Criar entry
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
        created_by=vendedor_id,
    )
    db.session.add(entry)
    db.session.commit()
    print(f"[COMISSAO] Pedido #{pedido.id}: R${commission_amount:.2f} ({category}) → user {vendedor_id}")
