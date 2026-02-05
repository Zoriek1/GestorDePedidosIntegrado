# -*- coding: utf-8 -*-
"""Testes do script de exportação para Google Sheets (identificar_aba, Nuvemshop = Site)."""
import importlib.util
from pathlib import Path

import pytest

# Carrega o módulo do script sem executar create_app
_backend_dir = Path(__file__).resolve().parent.parent
_script_path = _backend_dir / "scripts" / "export" / "exportar_vendas_sheets.py"
_spec = importlib.util.spec_from_file_location("exportar_vendas_sheets", _script_path)
_module = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_module)

identificar_aba = _module.identificar_aba
ABA_WHATSAPP = _module.ABA_WHATSAPP
ABA_CATALOGO = _module.ABA_CATALOGO
ABA_SITE = _module.ABA_SITE


@pytest.mark.parametrize(
    "fonte_nome,expected_aba",
    [
        ("WhatsApp", ABA_WHATSAPP),
        ("whatsapp", ABA_WHATSAPP),
        ("Catálogo", ABA_CATALOGO),
        ("catalogo", ABA_CATALOGO),
        ("Site", ABA_SITE),
        ("site", ABA_SITE),
        ("SITE", ABA_SITE),
        # Nuvemshop = subclasse de Site (mesma aba)
        ("Nuvemshop", ABA_SITE),
        ("nuvemshop", ABA_SITE),
        ("NuvemShop", ABA_SITE),
        ("Tiendanube", ABA_SITE),
        ("tiendanube", ABA_SITE),
    ],
)
def test_identificar_aba_fontes_conhecidas(fonte_nome, expected_aba):
    """Fontes conhecidas (incl. Nuvemshop) mapeiam para a aba correta."""
    assert identificar_aba(fonte_nome) == expected_aba


def test_identificar_aba_fonte_desconhecida_retorna_none():
    """Fonte desconhecida retorna None (pedido não entra em nenhuma aba)."""
    assert identificar_aba("Outra Fonte Qualquer") is None
    assert identificar_aba("") is None
