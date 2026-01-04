# -*- coding: utf-8 -*-
"""
Testes de API - Endpoints HTTP
"""
from datetime import date

from app.models import Pedido


class TestPedidosAPI:
    """Testes para endpoints de pedidos"""

    def test_listar_pedidos(self, client):
        """Testa GET /api/pedidos"""
        response = client.get("/api/pedidos")
        assert response.status_code == 200
        data = response.get_json()
        assert data["success"] is True
        # A resposta pode ter 'pedidos' diretamente ou em 'data'
        assert "pedidos" in data or "data" in data

    def test_listar_pedidos_com_filtro_status(self, client, session):
        """Testa GET /api/pedidos?status=agendado"""
        # Criar pedido de teste
        pedido = Pedido(
            cliente="Test Client",
            telefone_cliente="11987654321",
            destinatario="Test Recipient",
            produto="Test Product",
            valor="100.00",
            dia_entrega=date(2024, 12, 31),
            horario="10:00",
            status="agendado",
        )
        session.add(pedido)
        session.commit()

        response = client.get("/api/pedidos?status=agendado")
        assert response.status_code == 200
        data = response.get_json()
        assert data["success"] is True
        # Verificar se tem pedidos (pode estar em 'pedidos' ou 'data.pedidos')
        pedidos = data.get("pedidos", []) or data.get("data", {}).get("pedidos", [])
        assert len(pedidos) >= 1

    def test_obter_pedido(self, client, session):
        """Testa GET /api/pedidos/<id>"""
        pedido = Pedido(
            cliente="Test Client",
            telefone_cliente="11987654321",
            destinatario="Test Recipient",
            produto="Test Product",
            valor="100.00",
            dia_entrega=date(2024, 12, 31),
            horario="10:00",
            status="agendado",
        )
        session.add(pedido)
        session.commit()

        response = client.get(f"/api/pedidos/{pedido.id}")
        assert response.status_code == 200
        data = response.get_json()
        assert data["success"] is True
        # Verificar se tem pedido (pode estar em 'pedido' ou 'data.pedido')
        pedido_data = data.get("pedido") or data.get("data", {}).get("pedido")
        assert pedido_data["id"] == pedido.id

    def test_obter_pedido_nao_encontrado(self, client):
        """Testa GET /api/pedidos/<id> com ID inexistente"""
        response = client.get("/api/pedidos/99999")
        assert response.status_code == 404
        data = response.get_json()
        # Pode retornar 'success': False ou apenas 'error'
        assert data.get("success") is False or "error" in data

    def test_pedidos_por_data(self, client, session):
        """Testa GET /api/pedidos/por-data"""
        pedido = Pedido(
            cliente="Test Client",
            telefone_cliente="11987654321",
            destinatario="Test Recipient",
            produto="Test Product",
            valor="100.00",
            dia_entrega=date(2024, 12, 31),
            horario="10:00",
            status="agendado",
        )
        session.add(pedido)
        session.commit()

        response = client.get("/api/pedidos/por-data?data=2024-12-31")
        assert response.status_code == 200
        data = response.get_json()
        assert data["success"] is True
        # Verificar horários (pode estar em 'horarios' ou 'data.horarios')
        horarios = data.get("horarios", {}) or data.get("data", {}).get("horarios", {})
        assert "10:00" in horarios


class TestAuthAPI:
    """Testes para endpoints de autenticação"""

    def test_login_endpoint_exists(self, client):
        """Testa que o endpoint POST /api/auth/login existe e responde"""
        # Testa apenas que o endpoint existe e retorna uma resposta válida
        # (sucesso ou erro de credenciais)
        response = client.post("/api/auth/login", json={"username": "admin", "password": "test123"})
        # Pode retornar 200 (sucesso) ou 401 (credenciais inválidas)
        assert response.status_code in [200, 401]
        data = response.get_json()
        assert "success" in data or "error" in data

    def test_login_credenciais_invalidas(self, client, app):
        """Testa POST /api/auth/login com credenciais inválidas"""
        with app.app_context():
            import os

            os.environ["EDIT_USERNAME"] = "admin"
            os.environ["EDIT_PASSWORD"] = "test123"

            response = client.post(
                "/api/auth/login",
                json={"username": "admin", "password": "senha_errada"},
            )
            assert response.status_code == 401
            data = response.get_json()
            assert data["success"] is False

    def test_check_auth_status(self, client):
        """Testa GET /api/auth/check"""
        response = client.get("/api/auth/check")
        assert response.status_code == 200
        data = response.get_json()
        # Verificar authenticated (pode estar diretamente ou em 'data')
        assert "authenticated" in data or "authenticated" in data.get("data", {})


class TestHealthAPI:
    """Testes para endpoints de health check"""

    def test_health_check(self, client):
        """Testa GET /api/health"""
        response = client.get("/api/health")
        assert response.status_code == 200
        data = response.get_json()
        assert data["status"] == "healthy" or data["success"] is True
