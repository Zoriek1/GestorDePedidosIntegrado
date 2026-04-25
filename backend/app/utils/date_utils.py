# -*- coding: utf-8 -*-
from datetime import date, datetime, timedelta
from typing import Optional

try:
    from zoneinfo import ZoneInfo
except ImportError:
    from backports.zoneinfo import ZoneInfo

TIMEZONE_BRASIL = ZoneInfo("America/Sao_Paulo")


def today_brazil() -> date:
    """Retorna a data atual no fuso America/Sao_Paulo, evitando drift por TZ do servidor."""
    return datetime.now(TIMEZONE_BRASIL).date()


def get_monday(ref_date: Optional[date] = None) -> date:
    """Retorna a segunda-feira da semana fornecida (ou da semana atual em horário Brasil)."""
    if ref_date is None:
        ref_date = today_brazil()
    return ref_date - timedelta(days=ref_date.weekday())
