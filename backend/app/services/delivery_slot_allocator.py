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
from datetime import date, datetime, time, timedelta
import re
from typing import Dict, Optional, Tuple

from app import db
from app.models.pedido import Pedido

DEFAULT_DAY_START = time(8, 0)
DEFAULT_DAY_END = time(22, 0)  # último slot que aceita: 21:00 (cobre 21:00-22:00)
SLOT_CAPACITY = 2
EXPRESS_BUFFER_H = 0
DEFAULT_BUFFER_H = 2

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


def build_occupancy(dia_entrega: date) -> Dict[time, int]:
    """Contagem de pedidos já alocados por slot no dia."""
    rows = (
        db.session.query(Pedido.slot_inicio, db.func.count(Pedido.id))
        .filter(Pedido.dia_entrega == dia_entrega)
        .filter(Pedido.slot_inicio.isnot(None))
        .group_by(Pedido.slot_inicio)
        .all()
    )
    return {slot: count for slot, count in rows}


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
