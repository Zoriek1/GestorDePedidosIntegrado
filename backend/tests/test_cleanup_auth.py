# -*- coding: utf-8 -*-
"""
Garante que POST /api/cleanup (operação destrutiva — arquiva pedidos)
exige autenticação. Regressão guard para o decorator @requires_any_role.
"""


def test_cleanup_requires_admin(client):
    """POST /api/cleanup sem auth deve retornar 401/403."""
    response = client.post("/api/cleanup", json={"days": 1})
    assert response.status_code in (401, 403), (
        f"Endpoint destrutivo sem proteção (status {response.status_code}). "
        "Verificar @requires_any_role em core.py:limpar_pedidos_antigos"
    )
