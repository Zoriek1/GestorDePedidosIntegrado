# -*- coding: utf-8 -*-
"""
Alocador automático de slots de entrega para pedidos importados do site (Nuvemshop).

Slot = janela fixa de 1 hora (08:00, 09:00, ..., 21:00). Capacidade 2 pedidos/slot.

Regras:
  - Mesmo dia, Expressa:     primeiro slot ≥ hora do pagamento (sem buffer).
  - Mesmo dia, não-expresso: primeiro slot ≥ hora_pagamento + 2h.
  - Dia futuro:              primeiro slot ≥ 08:00 (ignora buffer).
  - Sempre respeita o início da janela do cliente (custom_field "Período da Entrega").
  - Se todos os slots do dia esgotaram, empilha no último (não rejeita).

Deadline:
  - Expressa mesmo dia: paid_at + 1h truncado a minutos.
  - Caso contrário:    fim da janela do cliente (ex: 18:00 de "Tarde") ou DEFAULT_DAY_END.
"""

import re
from datetime import date, datetime, time, timedelta
from typing import Dict, Optional, Tuple

from app import db
from app.models.pedido import Pedido

DEFAULT_DAY_START = time(8, 0)
DEFAULT_DAY_END = time(22, 0)  # último slot que aceita: 21:00 (cobre 21:00-22:00)
SLOT_CAPACITY = 2
# INT-02: antecedência mínima entre o pagamento e o slot escolhido no mesmo dia.
#   - Expressa: 0h (intencional — a entrega expressa precisa de slot imediato).
#   - Padrão:   2h (piso mínimo para a florista montar e despachar).
EXPRESS_BUFFER_H = 0
DEFAULT_BUFFER_H = 2  # piso mínimo de antecedência (não-expressa)

_TIME_RANGE_RE = re.compile(r"(\d{1,2}):(\d{2})\s*-\s*(\d{1,2}):(\d{2})")
_SINGLE_TIME_RE = re.compile(r"(\d{1,2}):(\d{2})")


def parse_customer_window(horario: Optional[str]) -> Optional[Tuple[time, time]]:
    """
    Converte o campo `horario` (ex: "08:00 - 18:00", "13:00", None) numa tupla
    (start, end). Retorna None se não conseguir extrair.

    "HH:MM - HH:MM" → (HH:MM, HH:MM)
    "HH:MM"        → (HH:MM, HH:MM + 1h)
    """
    if not horario:
        return None
    s = horario.strip()
    m = _TIME_RANGE_RE.search(s)
    if m:
        try:
            start = time(int(m.group(1)), int(m.group(2)))
            end = time(int(m.group(3)), int(m.group(4)))
            return (start, end)
        except ValueError:
            return None
    m = _SINGLE_TIME_RE.search(s)
    if m:
        try:
            start = time(int(m.group(1)), int(m.group(2)))
            end_hour = (start.hour + 1) if start.hour < 23 else 23
            return (start, time(end_hour, start.minute))
        except ValueError:
            return None
    return None


def derive_slot_inicio(horario: Optional[str]) -> Optional[time]:
    """
    Deriva um `slot_inicio` (Time) a partir do campo `horario` (string BR) para
    pedidos manuais. Assim toda origem (site e manual) grava um horário comparável
    para ordenação (INT-01) e o pedido entra na contagem de ocupação do alocador
    (INT-02). Retorna None quando o horário não é parseável.
    """
    window = parse_customer_window(horario)
    return window[0] if window else None


def build_occupancy(dia_entrega: date) -> Dict[time, int]:
    """
    Contagem de pedidos por slot (janela de 1h) no dia.

    INT-02: conta TODOS os pedidos do dia que já têm `slot_inicio` — inclusive os
    manuais do Gestor, que agora gravam slot_inicio (INT-01). Como pedidos manuais
    podem ter slot_inicio fora da grade horária (ex.: 09:30), a contagem é agrupada
    pela HORA (09:30 conta no slot 09:00), refletindo a carga real de cada janela.
    Soft-deleted não ocupa slot.
    """
    rows = (
        db.session.query(Pedido.slot_inicio)
        .filter(Pedido.dia_entrega == dia_entrega)
        .filter(Pedido.slot_inicio.isnot(None))
        .filter(Pedido.deleted_at.is_(None))
        .all()
    )
    occupancy: Dict[time, int] = {}
    for (slot,) in rows:
        if slot is None:
            continue
        hour_slot = time(slot.hour, 0)
        occupancy[hour_slot] = occupancy.get(hour_slot, 0) + 1
    return occupancy


def _compute_deadline(
    is_expressa: bool,
    is_same_day: bool,
    paid_at_local: datetime,
    customer_window: Optional[Tuple[time, time]],
) -> time:
    if is_expressa and is_same_day:
        target = paid_at_local + timedelta(hours=1)
        # Trunca a minutos (sem segundos/microsegundos).
        return time(target.hour, target.minute)
    if customer_window:
        return customer_window[1]
    return DEFAULT_DAY_END


def _ceil_to_next_hour(dt: datetime) -> int:
    """
    Arredonda pra cima: se o datetime tem minutos > 0 (ou segundos), vai pra próxima hora.
    Ex: 11:00 → 11, 11:01 → 12, 11:46 → 12.
    Usado pra garantir que o slot alocado SEMPRE comece depois de `paid_at + buffer`,
    não no mesmo instante (slot 11:00 não faz sentido pra pedido pago 11:46).
    """
    if dt.minute > 0 or dt.second > 0 or dt.microsecond > 0:
        return dt.hour + 1
    return dt.hour


def allocate_slot(
    dia_entrega: date,
    paid_at_local: datetime,
    is_expressa: bool,
    customer_window: Optional[Tuple[time, time]],
    occupancy: Optional[Dict[time, int]] = None,
) -> Tuple[time, time]:
    """
    Retorna (slot_inicio, slot_deadline).

    Se `occupancy` não for passado, é consultado no banco. Permitir passar é útil em testes.
    """
    if occupancy is None:
        occupancy = build_occupancy(dia_entrega)

    is_same_day = dia_entrega == paid_at_local.date()

    if is_same_day:
        buffer_h = EXPRESS_BUFFER_H if is_expressa else DEFAULT_BUFFER_H
        threshold_hour = _ceil_to_next_hour(paid_at_local + timedelta(hours=buffer_h))
    else:
        threshold_hour = DEFAULT_DAY_START.hour

    window_start_hour = customer_window[0].hour if customer_window else DEFAULT_DAY_START.hour
    window_end_hour = customer_window[1].hour if customer_window else DEFAULT_DAY_END.hour

    candidate = max(threshold_hour, window_start_hour, DEFAULT_DAY_START.hour)

    # Limite superior do walk: respeita fim da janela do cliente, mas não ultrapassa
    # o último slot do dia. Para janelas exatas tipo "13:00 - 18:00", o último slot
    # válido é 17:00 (cobre 17:00-18:00); window_end_hour=18 satisfaz `cand < end_hour`.
    upper = min(DEFAULT_DAY_END.hour, window_end_hour)

    chosen: Optional[time] = None
    for h in range(candidate, upper):
        slot = time(h, 0)
        if occupancy.get(slot, 0) < SLOT_CAPACITY:
            chosen = slot
            break

    if chosen is None:
        # Lotado: empilha no último slot válido da janela do cliente
        # (ou último do dia se não houver janela).
        last_hour = max(upper - 1, DEFAULT_DAY_START.hour)
        chosen = time(last_hour, 0)

    deadline = _compute_deadline(is_expressa, is_same_day, paid_at_local, customer_window)
    return chosen, deadline
