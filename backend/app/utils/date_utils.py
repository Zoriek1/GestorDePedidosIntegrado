# -*- coding: utf-8 -*-
from datetime import date, timedelta
from typing import Optional


def get_monday(ref_date: Optional[date] = None) -> date:
    """Retorna a segunda-feira da semana fornecida (ou da semana atual)."""
    if ref_date is None:
        ref_date = date.today()
    return ref_date - timedelta(days=ref_date.weekday())
