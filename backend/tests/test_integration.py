# -*- coding: utf-8 -*-
"""
Testes de Integração - Validação de que repositories e schemas funcionam juntos
"""
from datetime import date

from app.models import Pedido
from app.repositories.cliente_repository import ClienteRepository
from app.repositories.pedido_repository import PedidoRepository
from app.schemas.cliente_schema import ClienteCreateSchema
from app.schemas.pedido_schema import PedidoCreateSchema, PedidoUpdateSchema


class TestIntegration:
    """Testes de integração entre repositories e schemas"""

    def test_criar_pedido_com_schema_e_repository(self, session):
        """Testa criar pedido usando schema para validação e repository para persistência"""
        schema = PedidoCreateSchema()
        repo = PedidoRepository()

        # Dados válidos
        data = {
            "cliente": "John Doe",
            "telefone_cliente": "11987654321",
            "destinatario": "Jane Doe",
            "produto": "Roses",
            "dia_entrega": "2024-12-31",
            "horario": "10:00",
            "status": "agendado",
        }

        # Validar com schema
        validated_data = schema.load(data)

        # Criar com repository
        pedido = repo.create(**validated_data)

        assert pedido is not None
        assert pedido.id is not None
        assert pedido.cliente == "John Doe"
        assert pedido.status == "agendado"

        # Buscar novamente
        found = repo.get_by_id(pedido.id)
        assert found is not None
        assert found.cliente == "John Doe"

    def test_atualizar_pedido_com_schema_e_repository(self, session):
        """Testa atualizar pedido usando schema e repository"""
        schema = PedidoUpdateSchema()
        repo = PedidoRepository()

        # Criar pedido inicial
        pedido = Pedido(
            cliente="John Doe",
            telefone_cliente="11987654321",
            destinatario="Jane Doe",
            produto="Roses",
            valor="100.00",
            dia_entrega=date(2024, 12, 31),
            horario="10:00",
            status="agendado",
        )
        session.add(pedido)
        session.commit()

        # Dados de atualização
        update_data = {"status": "em_producao", "observacoes": "Atualizado via teste"}

        # Validar com schema
        validated_data = schema.load(update_data)

        # Atualizar com repository
        updated = repo.update(pedido, **validated_data)

        assert updated.status == "em_producao"
        assert updated.observacoes == "Atualizado via teste"

    def test_criar_cliente_com_schema_e_repository(self, session):
        """Testa criar cliente usando schema e repository"""
        schema = ClienteCreateSchema()
        repo = ClienteRepository()

        data = {
            "nome": "John Doe",
            "telefone": "11987654321",
            "email": "john@example.com",
        }

        # Validar com schema
        validated_data = schema.load(data)

        # Criar com repository
        cliente = repo.create(**validated_data)

        assert cliente is not None
        assert cliente.id is not None
        assert cliente.nome == "John Doe"
        assert cliente.telefone == "11987654321"

    def test_buscar_pedidos_com_filtros(self, session):
        """Testa busca de pedidos com múltiplos filtros usando repository"""
        repo = PedidoRepository()

        # Criar pedidos de teste
        pedido1 = Pedido(
            cliente="John Doe",
            telefone_cliente="11987654321",
            destinatario="Jane Doe",
            produto="Roses",
            valor="100.00",
            dia_entrega=date(2024, 12, 31),
            horario="10:00",
            status="agendado",
        )
        pedido2 = Pedido(
            cliente="Jane Smith",
            telefone_cliente="11987654322",
            destinatario="John Smith",
            produto="Tulips",
            valor="200.00",
            dia_entrega=date(2025, 1, 1),
            horario="11:00",
            status="em_producao",
        )
        session.add_all([pedido1, pedido2])
        session.commit()

        # Buscar por status
        agendados = repo.buscar_por_status("agendado")
        assert len(agendados) == 1
        assert agendados[0].cliente == "John Doe"

        # Buscar com filtros múltiplos
        resultados, total = repo.buscar_com_filtros(
            status="agendado",
            data_inicio=date(2024, 12, 31),
            data_fim=date(2024, 12, 31),
        )
        assert len(resultados) == 1
        assert total == 1
        assert resultados[0].cliente == "John Doe"
