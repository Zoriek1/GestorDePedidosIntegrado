# -*- coding: utf-8 -*-
"""Normalizacao e validacao de dados fiscais brasileiros."""

import re
from typing import Any, Optional


VALID_UFS = {
    "AC",
    "AL",
    "AP",
    "AM",
    "BA",
    "CE",
    "DF",
    "ES",
    "GO",
    "MA",
    "MT",
    "MS",
    "MG",
    "PA",
    "PB",
    "PR",
    "PE",
    "PI",
    "RJ",
    "RN",
    "RS",
    "RO",
    "RR",
    "SC",
    "SP",
    "SE",
    "TO",
}


def normalize_cpf_cnpj(value: Any) -> Optional[str]:
    """Retorna somente os digitos de CPF/CNPJ, ou None quando vazio."""
    digits = re.sub(r"\D", "", str(value or ""))
    return digits or None


def _valid_check_digits(digits: str, first_weights: list[int], second_weights: list[int]) -> bool:
    first_total = sum(int(number) * weight for number, weight in zip(digits, first_weights))
    first_digit = 11 - (first_total % 11)
    first_digit = 0 if first_digit >= 10 else first_digit
    if first_digit != int(digits[-2]):
        return False

    second_total = sum(int(number) * weight for number, weight in zip(digits, second_weights))
    second_digit = 11 - (second_total % 11)
    second_digit = 0 if second_digit >= 10 else second_digit
    return second_digit == int(digits[-1])


def is_valid_cpf_cnpj(value: Any) -> bool:
    """Valida tamanho, repeticao e digitos verificadores de CPF ou CNPJ."""
    digits = normalize_cpf_cnpj(value)
    if not digits or len(digits) not in (11, 14) or len(set(digits)) == 1:
        return False

    if len(digits) == 11:
        return _valid_check_digits(
            digits,
            list(range(10, 1, -1)),
            list(range(11, 1, -1)),
        )

    return _valid_check_digits(
        digits,
        [5, 4, 3, 2, 9, 8, 7, 6, 5, 4, 3, 2],
        [6, 5, 4, 3, 2, 9, 8, 7, 6, 5, 4, 3, 2],
    )


def normalize_uf(value: Any) -> Optional[str]:
    """Normaliza uma UF brasileira; retorna None quando vazia ou invalida."""
    uf = str(value or "").strip().upper()
    return uf if uf in VALID_UFS else None
