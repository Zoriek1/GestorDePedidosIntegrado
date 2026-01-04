# -*- coding: utf-8 -*-
"""
Testes da API - Endpoints principais
"""


def test_health_check(client):
    """Testa endpoint de health check"""
    response = client.get("/api/health")
    assert response.status_code == 200
    data = response.get_json()
    assert data["success"] is True


def test_backup_status(client):
    """Testa endpoint de status de backup"""
    response = client.get("/api/backup/status")
    assert response.status_code == 200
    data = response.get_json()
    assert "backup_stats" in data
