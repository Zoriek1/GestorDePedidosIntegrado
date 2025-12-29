# -*- coding: utf-8 -*-
"""
Testes para Repositories
"""
import pytest
from datetime import date, datetime
from app.repositories.pedido_repository import PedidoRepository
from app.repositories.cliente_repository import ClienteRepository
from app.models import Pedido, Cliente


class TestPedidoRepository:
    """Testes para PedidoRepository"""
    
    def test_get_by_id(self, session):
        """Testa busca de pedido por ID"""
        repo = PedidoRepository()
        
        # Criar pedido de teste
        pedido = Pedido(
            cliente="Test Client",
            telefone_cliente="11987654321",
            destinatario="Test Recipient",
            produto="Test Product",
            valor="100.00",
            dia_entrega=date(2024, 12, 31),
            horario="10:00",
            status="agendado"
        )
        session.add(pedido)
        session.commit()
        
        # Buscar por ID
        found = repo.get_by_id(pedido.id)
        assert found is not None
        assert found.id == pedido.id
        assert found.cliente == "Test Client"
    
    def test_buscar_por_status(self, session):
        """Testa busca de pedidos por status"""
        repo = PedidoRepository()
        
        # Criar pedidos com diferentes status
        pedido1 = Pedido(
            cliente="Client 1",
            telefone_cliente="11987654321",
            destinatario="Recipient 1",
            produto="Product 1",
            valor="100.00",
            dia_entrega=date(2024, 12, 31),
            horario="10:00",
            status="agendado"
        )
        pedido2 = Pedido(
            cliente="Client 2",
            telefone_cliente="11987654322",
            destinatario="Recipient 2",
            produto="Product 2",
            valor="200.00",
            dia_entrega=date(2024, 12, 31),
            horario="11:00",
            status="em_producao"
        )
        session.add_all([pedido1, pedido2])
        session.commit()
        
        # Buscar por status
        agendados = repo.buscar_por_status("agendado")
        assert len(agendados) == 1
        assert agendados[0].status == "agendado"
        
        em_producao = repo.buscar_por_status("em_producao")
        assert len(em_producao) == 1
        assert em_producao[0].status == "em_producao"
    
    def test_buscar_com_filtros(self, session):
        """Testa busca com múltiplos filtros"""
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
            status="agendado"
        )
        pedido2 = Pedido(
            cliente="Jane Smith",
            telefone_cliente="11987654322",
            destinatario="John Smith",
            produto="Tulips",
            valor="200.00",
            dia_entrega=date(2025, 1, 1),
            horario="11:00",
            status="agendado"
        )
        session.add_all([pedido1, pedido2])
        session.commit()
        
        # Buscar por status
        resultados = repo.buscar_com_filtros(status="agendado")
        assert len(resultados) == 2
        
        # Buscar por data
        resultados = repo.buscar_com_filtros(
            data_inicio=date(2024, 12, 31),
            data_fim=date(2024, 12, 31)
        )
        assert len(resultados) == 1
        assert resultados[0].cliente == "John Doe"
        
        # Buscar por texto
        resultados = repo.buscar_com_filtros(search="John")
        assert len(resultados) >= 1
    
    def test_atualizar_status(self, session):
        """Testa atualização de status"""
        repo = PedidoRepository()
        
        pedido = Pedido(
            cliente="Test Client",
            telefone_cliente="11987654321",
            destinatario="Test Recipient",
            produto="Test Product",
            valor="100.00",
            dia_entrega=date(2024, 12, 31),
            horario="10:00",
            status="agendado"
        )
        session.add(pedido)
        session.commit()
        
        # Atualizar status
        updated = repo.atualizar_status(pedido.id, "em_producao")
        assert updated is not None
        assert updated.status == "em_producao"
        
        # Verificar no banco
        found = repo.get_by_id(pedido.id)
        assert found.status == "em_producao"


class TestClienteRepository:
    """Testes para ClienteRepository"""
    
    def test_get_by_id(self, session):
        """Testa busca de cliente por ID"""
        repo = ClienteRepository()
        
        cliente = Cliente(
            nome="Test Client",
            telefone="11987654321",
            email="test@example.com"
        )
        session.add(cliente)
        session.commit()
        
        found = repo.get_by_id(cliente.id)
        assert found is not None
        assert found.nome == "Test Client"
    
    def test_buscar_por_telefone(self, session):
        """Testa busca de cliente por telefone"""
        repo = ClienteRepository()
        
        cliente = Cliente(
            nome="Test Client",
            telefone="11987654321",
            email="test@example.com"
        )
        session.add(cliente)
        session.commit()
        
        # Buscar por telefone formatado
        found = repo.buscar_por_telefone("(11) 98765-4321")
        assert found is not None
        assert found.telefone == "11987654321"
        
        # Buscar por telefone limpo
        found = repo.buscar_por_telefone("11987654321")
        assert found is not None
    
    def test_criar_ou_buscar(self, session):
        """Testa criação ou busca de cliente existente"""
        repo = ClienteRepository()
        
        # Criar primeiro cliente
        cliente1 = repo.criar_ou_buscar(
            nome="Test Client",
            telefone="11987654321",
            email="test@example.com"
        )
        assert cliente1 is not None
        assert cliente1.nome == "Test Client"
        
        # Tentar criar novamente (deve retornar o existente)
        cliente2 = repo.criar_ou_buscar(
            nome="Another Name",
            telefone="11987654321",
            email="another@example.com"
        )
        assert cliente2.id == cliente1.id
        assert cliente2.nome == "Test Client"  # Nome original mantido
    
    def test_buscar_por_nome(self, session):
        """Testa busca de clientes por nome"""
        repo = ClienteRepository()
        
        cliente1 = Cliente(nome="John Doe", telefone="11987654321")
        cliente2 = Cliente(nome="Jane Doe", telefone="11987654322")
        session.add_all([cliente1, cliente2])
        session.commit()
        
        resultados = repo.buscar_por_nome("John")
        assert len(resultados) == 1
        assert resultados[0].nome == "John Doe"
        
        resultados = repo.buscar_por_nome("Doe")
        assert len(resultados) == 2

