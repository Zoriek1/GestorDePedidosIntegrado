# -*- coding: utf-8 -*-
"""
Testes para Repositories
"""
from datetime import date

from app.models import Cliente, Pedido
from app.repositories.cliente_repository import ClienteRepository
from app.repositories.pedido_repository import PedidoRepository


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
            status="agendado",
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
            status="agendado",
        )
        pedido2 = Pedido(
            cliente="Client 2",
            telefone_cliente="11987654322",
            destinatario="Recipient 2",
            produto="Product 2",
            valor="200.00",
            dia_entrega=date(2024, 12, 31),
            horario="11:00",
            status="em_producao",
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
            status="agendado",
        )
        session.add_all([pedido1, pedido2])
        session.commit()

        # Buscar por status
        resultados, total = repo.buscar_com_filtros(status="agendado")
        assert len(resultados) == 2
        assert total == 2

        # Buscar por data
        resultados, total = repo.buscar_com_filtros(
            data_inicio=date(2024, 12, 31), data_fim=date(2024, 12, 31)
        )
        assert len(resultados) == 1
        assert total == 1
        assert resultados[0].cliente == "John Doe"

        # Buscar por texto
        resultados, total = repo.buscar_com_filtros(search="John")
        assert len(resultados) >= 1
        assert total >= 1

    def test_ordena_por_slot_inicio_nao_lexicografico(self, session):
        """INT-01: ordenar por horário real (slot_inicio, Time), não pela string.

        '9:00' deve vir antes de '10:00' (lexicograficamente '10:00' < '9:00').
        Faixa '9:00 - 12:00' (slot 09:00) vem junto das 09:00, com desempate por horário.
        Pedido sem slot_inicio parseável vai para o fim (NULLS LAST).
        """
        from datetime import time

        repo = PedidoRepository()
        dia = date(2026, 6, 20)

        def novo(horario, slot, dest):
            p = Pedido(
                cliente="C",
                telefone_cliente="11999999999",
                destinatario=dest,
                produto="Buquê",
                dia_entrega=dia,
                horario=horario,
                slot_inicio=slot,
                status="agendado",
            )
            session.add(p)
            return p

        novo("10:00", time(10, 0), "DEZ")
        novo("9:00", time(9, 0), "NOVE")
        novo("9:00 - 12:00", time(9, 0), "FAIXA")
        novo("sem hora", None, "SEMHORA")
        session.commit()

        resultados, _ = repo.buscar_com_filtros(
            data_inicio=dia, data_fim=dia, ordenar_por="dia_entrega", ordenar_direcao="asc"
        )
        ordem = [p.destinatario for p in resultados]
        # 09:00 antes de 10:00; entre os 09:00, '9:00' antes de '9:00 - 12:00'; null por último.
        assert ordem.index("NOVE") < ordem.index("DEZ")
        assert ordem.index("FAIXA") < ordem.index("DEZ")
        assert ordem.index("NOVE") < ordem.index("FAIXA")
        assert ordem[-1] == "SEMHORA"

    def test_busca_por_id_telefone_e_caixa(self, session):
        """BUS-01: busca acha por número do pedido, telefone (sem máscara) e ignora caixa.

        (Acento é insensível só no Postgres via f_unaccent; aqui, SQLite, valida o
        fallback lower()/LIKE + id + telefone.)
        """
        repo = PedidoRepository()
        p = Pedido(
            cliente="Mariana Silva",
            telefone_cliente="11988887777",
            destinatario="João",
            produto="Buquê de rosas",
            dia_entrega=date(2026, 6, 20),
            horario="10:00",
            status="agendado",
        )
        session.add(p)
        session.commit()

        # Por número do pedido (id)
        res, _ = repo.buscar_com_filtros(search=str(p.id))
        assert any(r.id == p.id for r in res)

        # Por telefone (só dígitos, sem máscara)
        res, _ = repo.buscar_com_filtros(search="98888")
        assert any(r.id == p.id for r in res)

        # Caixa diferente
        res, _ = repo.buscar_com_filtros(search="mariana")
        assert any(r.id == p.id for r in res)

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
            status="agendado",
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

        cliente = Cliente(nome="Test Client", telefone="11987654321", email="test@example.com")
        session.add(cliente)
        session.commit()

        found = repo.get_by_id(cliente.id)
        assert found is not None
        assert found.nome == "Test Client"

    def test_buscar_por_telefone(self, session):
        """Testa busca de cliente por telefone"""
        repo = ClienteRepository()

        cliente = Cliente(nome="Test Client", telefone="11987654321", email="test@example.com")
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
            nome="Test Client", telefone="11987654321", email="test@example.com"
        )
        assert cliente1 is not None
        assert cliente1.nome == "Test Client"

        # Tentar criar novamente (deve retornar o existente)
        cliente2 = repo.criar_ou_buscar(
            nome="Another Name", telefone="11987654321", email="another@example.com"
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
