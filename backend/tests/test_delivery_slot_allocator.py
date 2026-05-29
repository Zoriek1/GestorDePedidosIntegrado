# -*- coding: utf-8 -*-
"""
Testes do alocador de slots de entrega.

Esses testes não tocam o banco — passam a `occupancy` direto pra `allocate_slot`,
que aceita o parâmetro pra facilitar testes determinísticos.
"""
from datetime import date, datetime, time

from app.services.delivery_slot_allocator import (
    DEFAULT_DAY_END,
    SLOT_CAPACITY,
    allocate_slot,
    parse_customer_window,
)


# ---------------------------------------------------------------------------
# parse_customer_window
# ---------------------------------------------------------------------------


def test_parse_customer_window_range():
    assert parse_customer_window("08:00 - 18:00") == (time(8, 0), time(18, 0))


def test_parse_customer_window_tarde():
    assert parse_customer_window("13:00 - 18:00") == (time(13, 0), time(18, 0))


def test_parse_customer_window_single_time():
    start, end = parse_customer_window("15:00")
    assert start == time(15, 0)
    assert end == time(16, 0)


def test_parse_customer_window_none():
    assert parse_customer_window(None) is None
    assert parse_customer_window("") is None
    assert parse_customer_window("texto sem hora") is None


# ---------------------------------------------------------------------------
# allocate_slot — mesmo dia
# ---------------------------------------------------------------------------


def test_allocate_express_pega_proximo_slot_da_hora_atual():
    """Cenário do pedido #263: pago 11:46 Expressa → slot 12:00 (próxima hora ≥ now)."""
    paid_at = datetime(2026, 5, 29, 11, 46)
    slot, deadline = allocate_slot(
        dia_entrega=date(2026, 5, 29),
        paid_at_local=paid_at,
        is_expressa=True,
        customer_window=(time(8, 0), time(18, 0)),
        occupancy={},
    )
    assert slot == time(12, 0)
    assert deadline == time(12, 46)


def test_allocate_express_pula_slot_lotado():
    """Slot 12:00 com 2 ocupantes → pula pra 13:00."""
    paid_at = datetime(2026, 5, 29, 11, 46)
    slot, _ = allocate_slot(
        dia_entrega=date(2026, 5, 29),
        paid_at_local=paid_at,
        is_expressa=True,
        customer_window=(time(8, 0), time(18, 0)),
        occupancy={time(12, 0): SLOT_CAPACITY},
    )
    assert slot == time(13, 0)


def test_allocate_express_pula_varios_lotados():
    paid_at = datetime(2026, 5, 29, 11, 0)
    slot, _ = allocate_slot(
        dia_entrega=date(2026, 5, 29),
        paid_at_local=paid_at,
        is_expressa=True,
        customer_window=None,
        occupancy={
            time(11, 0): SLOT_CAPACITY,
            time(12, 0): SLOT_CAPACITY,
            time(13, 0): 1,
        },
    )
    assert slot == time(13, 0)


def test_allocate_padrao_aplica_buffer_2h():
    """Pago 11:00 não-expresso, dia inteiro → slot ≥ 13:00."""
    paid_at = datetime(2026, 5, 29, 11, 0)
    slot, deadline = allocate_slot(
        dia_entrega=date(2026, 5, 29),
        paid_at_local=paid_at,
        is_expressa=False,
        customer_window=(time(8, 0), time(18, 0)),
        occupancy={},
    )
    assert slot == time(13, 0)
    assert deadline == time(18, 0)


def test_allocate_padrao_respeita_janela_cliente_tarde():
    """Pago 09:00 + Tarde (13-18) → primeiro slot é 13:00 (apesar do buffer dar 11)."""
    paid_at = datetime(2026, 5, 29, 9, 0)
    slot, deadline = allocate_slot(
        dia_entrega=date(2026, 5, 29),
        paid_at_local=paid_at,
        is_expressa=False,
        customer_window=(time(13, 0), time(18, 0)),
        occupancy={},
    )
    assert slot == time(13, 0)
    assert deadline == time(18, 0)


def test_allocate_padrao_buffer_passa_janela_cliente():
    """Pago 12:00 + Manhã (08-12) → buffer puxa pra 14:00 mas janela acaba 12:00 — empilha 11."""
    paid_at = datetime(2026, 5, 29, 12, 0)
    slot, _ = allocate_slot(
        dia_entrega=date(2026, 5, 29),
        paid_at_local=paid_at,
        is_expressa=False,
        customer_window=(time(8, 0), time(12, 0)),
        occupancy={},
    )
    # Como buffer (14) > window_end (12), o loop não roda;
    # cai no fallback "último slot válido da janela" = 11:00.
    assert slot == time(11, 0)


# ---------------------------------------------------------------------------
# allocate_slot — dia futuro
# ---------------------------------------------------------------------------


def test_allocate_dia_futuro_ignora_buffer():
    """Comprou sexta 20:00 pra segunda dia inteiro → segunda 08:00, deadline 18:00."""
    paid_at = datetime(2026, 5, 29, 20, 0)  # sexta
    dia_entrega = date(2026, 6, 1)  # segunda
    slot, deadline = allocate_slot(
        dia_entrega=dia_entrega,
        paid_at_local=paid_at,
        is_expressa=False,
        customer_window=(time(8, 0), time(18, 0)),
        occupancy={},
    )
    assert slot == time(8, 0)
    assert deadline == time(18, 0)


def test_allocate_dia_futuro_respeita_janela_cliente():
    """Comprou sexta 20:00 pra segunda Tarde → segunda 13:00."""
    paid_at = datetime(2026, 5, 29, 20, 0)
    dia_entrega = date(2026, 6, 1)
    slot, _ = allocate_slot(
        dia_entrega=dia_entrega,
        paid_at_local=paid_at,
        is_expressa=False,
        customer_window=(time(13, 0), time(18, 0)),
        occupancy={},
    )
    assert slot == time(13, 0)


def test_allocate_dia_futuro_pula_slots_lotados():
    """Segunda 08:00 lotado → 09:00."""
    paid_at = datetime(2026, 5, 29, 20, 0)
    dia_entrega = date(2026, 6, 1)
    slot, _ = allocate_slot(
        dia_entrega=dia_entrega,
        paid_at_local=paid_at,
        is_expressa=False,
        customer_window=(time(8, 0), time(18, 0)),
        occupancy={time(8, 0): SLOT_CAPACITY, time(9, 0): 1},
    )
    assert slot == time(9, 0)


# ---------------------------------------------------------------------------
# allocate_slot — edge cases
# ---------------------------------------------------------------------------


def test_allocate_dia_inteiro_lotado_empilha_ultimo_slot():
    """Todos os slots 2/2 → empilha no último (21:00), não falha."""
    paid_at = datetime(2026, 5, 29, 11, 0)
    full = {time(h, 0): SLOT_CAPACITY for h in range(8, 22)}
    slot, _ = allocate_slot(
        dia_entrega=date(2026, 5, 29),
        paid_at_local=paid_at,
        is_expressa=False,
        customer_window=(time(8, 0), time(22, 0)),
        occupancy=full,
    )
    assert slot == time(21, 0)


def test_allocate_sem_customer_window_usa_default_day_end():
    paid_at = datetime(2026, 5, 29, 11, 0)
    slot, deadline = allocate_slot(
        dia_entrega=date(2026, 5, 29),
        paid_at_local=paid_at,
        is_expressa=False,
        customer_window=None,
        occupancy={},
    )
    assert slot == time(13, 0)
    assert deadline == DEFAULT_DAY_END


def test_allocate_express_deadline_trunca_segundos():
    """Pago 11:46:37 Expressa → deadline 12:46 (segundos descartados)."""
    paid_at = datetime(2026, 5, 29, 11, 46, 37)
    _, deadline = allocate_slot(
        dia_entrega=date(2026, 5, 29),
        paid_at_local=paid_at,
        is_expressa=True,
        customer_window=None,
        occupancy={},
    )
    assert deadline == time(12, 46)
