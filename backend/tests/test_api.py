# -*- coding: utf-8 -*-
"""
Testes da API - Endpoints complementares
"""
import base64

_ADMIN_AUTH = {"Authorization": f"Basic {base64.b64encode(b'admin:testpass').decode()}"}


def test_backup_status(client):
    """Testa endpoint de status de backup (requer auth admin)"""
    response = client.get("/api/backup/status", headers=_ADMIN_AUTH)
    assert response.status_code == 200
    data = response.get_json()
    assert "backup_stats" in data


def test_backup_status_requires_auth(client):
    """Sem auth, endpoint deve retornar 401/403 (regressão guard)."""
    response = client.get("/api/backup/status")
    assert response.status_code in (401, 403)
