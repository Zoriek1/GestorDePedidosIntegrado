# -*- coding: utf-8 -*-
"""
Testes da API - Endpoints complementares
"""


def test_backup_status(client):
    """Testa endpoint de status de backup"""
    response = client.get("/api/backup/status")
    assert response.status_code == 200
    data = response.get_json()
    assert "backup_stats" in data
