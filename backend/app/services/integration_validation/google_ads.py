# -*- coding: utf-8 -*-
"""Validacoes isoladas do canal Google Ads.

Decisao de produto (F6): validar SOMENTE formato. O teste real (link de
conversao ativo) so faz sentido end-to-end, nao por credencial isolada.
"""

from __future__ import annotations

import re

GOOGLE_ADS_CUSTOMER_ID_RE = re.compile(r"^\d{3}-\d{3}-\d{4}$")
GOOGLE_ADS_CONVERSION_ACTION_ID_RE = re.compile(r"^\d{5,15}$")


def validate_google_ads_customer_id(value: str | None) -> tuple[bool, str | None]:
    if not value:
        return False, "Customer ID vazio"
    if not GOOGLE_ADS_CUSTOMER_ID_RE.match(value):
        return False, "Customer ID deve estar no formato 123-456-7890"
    return True, None


def validate_google_ads_conversion_action_id(value: str | None) -> tuple[bool, str | None]:
    if not value:
        return False, "Conversion Action ID vazio"
    if not GOOGLE_ADS_CONVERSION_ACTION_ID_RE.match(value):
        return False, "Conversion Action ID deve ter 5-15 digitos"
    return True, None
