# -*- coding: utf-8 -*-
"""
Utilitários para manipulação de valores monetários BRL
Separação explícita da lógica de LTV para uso em outras funcionalidades
"""


def parse_brl_money(valor_str: str) -> float:
    """
    Converte valor String BRL para float

    Suporta formatos:
    - "R$ 225,00"
    - "1.234,56"
    - "225.00"
    - "225"
    - "225,50"

    Args:
        valor_str: String com valor monetário

    Returns:
        float: Valor convertido, ou 0.0 se inválido
    """
    if not valor_str:
        return 0.0

    try:
        # Remove "R$" e espaços
        valor_limpo = str(valor_str).strip().replace("R$", "").strip()
        if not valor_limpo:
            return 0.0

        # Detectar formato brasileiro (tem vírgula)
        if "," in valor_limpo:
            # Formato BR: "65,00" ou "1.234,56"
            valor_limpo = valor_limpo.replace(".", "").replace(",", ".")
        elif "." in valor_limpo:
            # Formato US: "10.00" ou número simples
            dot_count = valor_limpo.count(".")
            if dot_count == 1:
                # Um ponto = decimal: "10.00"
                valor_limpo = valor_limpo
            else:
                # Múltiplos pontos = separadores de milhar
                valor_limpo = valor_limpo.replace(".", "")
        # Se não tem vírgula nem ponto, é número simples: "10"

        return float(valor_limpo)
    except (ValueError, AttributeError, TypeError):
        # Se não conseguir converter, retorna 0.0
        return 0.0
