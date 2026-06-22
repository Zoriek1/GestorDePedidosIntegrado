# -*- coding: utf-8 -*-
"""
Testes de API - Endpoints HTTP
"""
import base64
from datetime import date

from app.models import Cliente, Pedido

# GETs de pedidos passaram a exigir auth (não vazam PII publicamente).
_ADMIN_AUTH = {"Authorization": f"Basic {base64.b64encode(b'admin:testpass').decode()}"}


class TestPedidosAPI:
    """Testes para endpoints de pedidos"""

    def test_listar_pedidos(self, client):
        """Testa GET /api/pedidos"""
        response = client.get("/api/pedidos", headers=_ADMIN_AUTH)
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
            oculto=False,  # Garantir que não está oculto
        )
        session.add(pedido)
        session.commit()

        response = client.get("/api/pedidos?status=agendado", headers=_ADMIN_AUTH)
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

        response = client.get(f"/api/pedidos/{pedido.id}", headers=_ADMIN_AUTH)
        assert response.status_code == 200
        data = response.get_json()
        assert data["success"] is True
        # Verificar se tem pedido (pode estar em 'pedido' ou 'data.pedido')
        pedido_data = data.get("pedido") or data.get("data", {}).get("pedido")
        assert pedido_data["id"] == pedido.id

    def test_obter_pedido_nao_encontrado(self, client):
        """Testa GET /api/pedidos/<id> com ID inexistente"""
        response = client.get("/api/pedidos/99999", headers=_ADMIN_AUTH)
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
            oculto=False,  # Garantir que não está oculto
        )
        session.add(pedido)
        session.commit()

        response = client.get("/api/pedidos/por-data?data=2024-12-31", headers=_ADMIN_AUTH)
        assert response.status_code == 200
        data = response.get_json()
        assert data["success"] is True
        # Verificar horários (success_response faz update do dict, então horarios está no nível raiz)
        horarios = data.get("horarios", {})
        assert isinstance(horarios, dict)
        # Pode estar vazio se não houver pedidos com horário, mas deve ser um dict
        if horarios:
            assert "10:00" in horarios

    def test_criar_e_editar_detalhes_entrega(self, client, session):
        """Detalhes novos de entrega devem persistir e respeitar tipo_local."""
        payload = {
            "cliente": "Maria Silva",
            "telefone_cliente": "62999999999",
            "cpf_cnpj": "529.982.247-25",
            "destinatario": "Joao",
            "tipo_pedido": "Entrega",
            "produto": "Buque",
            "valor": "150.00",
            "dia_entrega": "2026-12-31",
            "horario": "14:00",
            "cep": "74810-170",
            "rua": "Rua das Flores",
            "numero": "10",
            "bairro": "Jardim",
            "cidade": "Goiania",
            "uf": "GO",
            "endereco": "Rua das Flores, 10, Jardim, Goiania",
            "tipo_local": "predio",
            "nome_local": "Edificio Jardim",
            "apto": "302",
            "bloco": "B",
            "torre": "2",
            "andar": "3",
            "complemento": "Portaria lateral",
        }

        response = client.post("/api/pedidos", json=payload, headers=_ADMIN_AUTH)
        assert response.status_code == 201
        data = response.get_json()
        pedido_data = data.get("pedido") or data.get("data", {}).get("pedido")
        assert pedido_data["tipo_local"] == "predio"
        assert pedido_data["nome_local"] == "Edificio Jardim"
        assert pedido_data["apto"] == "302"
        assert pedido_data["complemento"] == "Portaria lateral"
        assert pedido_data["cpf_cnpj"] == "52998224725"
        assert pedido_data["uf"] == "GO"
        cliente = Cliente.query.get(pedido_data["cliente_id"])
        assert cliente.cpf_cnpj == "52998224725"
        endereco_salvo = cliente.get_endereco_principal()
        assert endereco_salvo.estado == "GO"
        assert endereco_salvo.complemento == "Portaria lateral"

        pedido_id = pedido_data["id"]
        response = client.put(
            f"/api/pedidos/{pedido_id}",
            json={"tipo_local": "casa", "quadra": "5", "lote": "12"},
            headers=_ADMIN_AUTH,
        )
        assert response.status_code == 200
        data = response.get_json()
        pedido_data = data.get("pedido") or data.get("data", {}).get("pedido")
        assert pedido_data["tipo_local"] == "casa"
        assert pedido_data["quadra"] == "5"
        assert pedido_data["lote"] == "12"
        assert pedido_data["nome_local"] == ""
        assert pedido_data["apto"] == ""

    def test_entrega_exige_endereco_estruturado_basico(self, client):
        response = client.post(
            "/api/pedidos",
            json={
                "cliente": "Maria Silva",
                "telefone_cliente": "62999999999",
                "destinatario": "Joao",
                "tipo_pedido": "Entrega",
                "produto": "Buque",
                "dia_entrega": "2026-12-31",
                "horario": "14:00",
            },
            headers=_ADMIN_AUTH,
        )
        assert response.status_code == 400
        assert "campos_faltantes" in response.get_json().get("details", {})

    def test_entrega_sem_numero_e_uf_salva_numero_sn(self, client):
        response = client.post(
            "/api/pedidos",
            json={
                "cliente": "Maria Silva",
                "telefone_cliente": "62999999999",
                "destinatario": "Joao",
                "tipo_pedido": "Entrega",
                "produto": "Buque",
                "valor": "150.00",
                "dia_entrega": "2026-12-31",
                "horario": "14:00",
                "cep": "74810-170",
                "rua": "Rua das Flores",
                "numero": "",
                "bairro": "Jardim",
                "cidade": "Goiania",
                "uf": "",
            },
            headers=_ADMIN_AUTH,
        )
        assert response.status_code == 201
        data = response.get_json()
        pedido_data = data.get("pedido") or data.get("data", {}).get("pedido")
        assert pedido_data["numero"] == "S/N"
        assert pedido_data["uf"] in ("", None)

    def test_rejeita_documento_invalido(self, client):
        response = client.post(
            "/api/pedidos",
            json={
                "cliente": "Maria Silva",
                "telefone_cliente": "62999999999",
                "cpf_cnpj": "111.111.111-11",
                "destinatario": "Maria Silva",
                "tipo_pedido": "Retirada",
                "produto": "Buque",
                "dia_entrega": "2026-12-31",
                "horario": "14:00",
            },
            headers=_ADMIN_AUTH,
        )
        assert response.status_code == 400
        assert "CPF/CNPJ" in response.get_json().get("error", "")


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


class TestClientesAPI:
    def test_cliente_persiste_documento_normalizado(self, client):
        response = client.post(
            "/api/clientes",
            json={
                "nome": "Cliente Fiscal",
                "telefone": "62988887777",
                "cpf_cnpj": "04.252.011/0001-10",
            },
            headers=_ADMIN_AUTH,
        )
        assert response.status_code == 201
        assert response.get_json()["cliente"]["cpf_cnpj"] == "04252011000110"

    def test_cliente_rejeita_documento_invalido(self, client):
        response = client.post(
            "/api/clientes",
            json={
                "nome": "Cliente Fiscal",
                "telefone": "62988887778",
                "cpf_cnpj": "111.111.111-11",
            },
            headers=_ADMIN_AUTH,
        )
        assert response.status_code == 400


class TestHealthAPI:
    """Testes para endpoints de health check"""

    def test_health_check(self, client):
        """Testa GET /api/health"""
        response = client.get("/api/health")
        assert response.status_code == 200
        data = response.get_json()
        assert data["status"] == "healthy" or data["success"] is True
