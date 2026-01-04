# -*- coding: utf-8 -*-
"""
Testes dos Models - Validação de modelos de dados
"""
from app import db
from app.models import Cliente, Pedido


def test_pedido_creation(app):
    """Testa criação de pedido"""
    from datetime import date
    with app.app_context():
        pedido = Pedido(
            cliente="Teste Cliente",
            telefone_cliente="123456789",
            destinatario="Teste Destinatário",
            produto="Teste Produto",
            valor="100.00",
            dia_entrega=date(2024, 12, 31),
            horario="14:00"
        )
        db.session.add(pedido)
        db.session.commit()

        assert pedido.id is not None
        assert pedido.cliente == "Teste Cliente"


def test_cliente_creation(app):
    """Testa criação de cliente"""
    with app.app_context():
        cliente = Cliente(
            nome="Teste Cliente",
            telefone="123456789"
        )
        db.session.add(cliente)
        db.session.commit()

        assert cliente.id is not None
        assert cliente.nome == "Teste Cliente"

