# -*- coding: utf-8 -*-
"""
Testes para Schemas (Marshmallow)
"""
import pytest
from datetime import date
from marshmallow import ValidationError
from app.schemas.pedido_schema import PedidoCreateSchema, PedidoUpdateSchema
from app.schemas.cliente_schema import ClienteCreateSchema, ClienteUpdateSchema


class TestPedidoSchema:
    """Testes para schemas de Pedido"""
    
    def test_pedido_create_schema_valid(self):
        """Testa criação de pedido com dados válidos"""
        schema = PedidoCreateSchema()
        
        data = {
            'cliente': 'John Doe',
            'telefone_cliente': '11987654321',
            'destinatario': 'Jane Doe',
            'produto': 'Roses',
            'dia_entrega': '2024-12-31',
            'horario': '10:00',
            'status': 'agendado'
        }
        
        result = schema.load(data)
        assert result['cliente'] == 'John Doe'
        assert result['destinatario'] == 'Jane Doe'
        assert result['horario'] == '10:00'
    
    def test_pedido_create_schema_missing_required(self):
        """Testa validação de campos obrigatórios"""
        schema = PedidoCreateSchema()
        
        data = {
            'cliente': 'John Doe'
            # Faltam campos obrigatórios
        }
        
        with pytest.raises(ValidationError) as exc_info:
            schema.load(data)
        
        errors = exc_info.value.messages
        assert 'telefone_cliente' in errors
        assert 'destinatario' in errors
        assert 'produto' in errors
        assert 'dia_entrega' in errors
        assert 'horario' in errors
    
    def test_pedido_create_schema_invalid_horario(self):
        """Testa validação de formato de horário"""
        schema = PedidoCreateSchema()
        
        data = {
            'cliente': 'John Doe',
            'telefone_cliente': '11987654321',
            'destinatario': 'Jane Doe',
            'produto': 'Roses',
            'dia_entrega': '2024-12-31',
            'horario': '25:00'  # Horário inválido
        }
        
        with pytest.raises(ValidationError) as exc_info:
            schema.load(data)
        
        errors = exc_info.value.messages
        assert 'horario' in errors
    
    def test_pedido_create_schema_invalid_status(self):
        """Testa validação de status"""
        schema = PedidoCreateSchema()
        
        data = {
            'cliente': 'John Doe',
            'telefone_cliente': '11987654321',
            'destinatario': 'Jane Doe',
            'produto': 'Roses',
            'dia_entrega': '2024-12-31',
            'horario': '10:00',
            'status': 'status_invalido'
        }
        
        with pytest.raises(ValidationError) as exc_info:
            schema.load(data)
        
        errors = exc_info.value.messages
        assert 'status' in errors
    
    def test_pedido_update_schema_partial(self):
        """Testa atualização parcial de pedido"""
        schema = PedidoUpdateSchema()
        
        # Apenas alguns campos
        data = {
            'status': 'em_producao',
            'observacoes': 'Atualizado via teste'
        }
        
        result = schema.load(data)
        assert result['status'] == 'em_producao'
        assert result['observacoes'] == 'Atualizado via teste'


class TestClienteSchema:
    """Testes para schemas de Cliente"""
    
    def test_cliente_create_schema_valid(self):
        """Testa criação de cliente com dados válidos"""
        schema = ClienteCreateSchema()
        
        data = {
            'nome': 'John Doe',
            'telefone': '11987654321',
            'email': 'john@example.com'
        }
        
        result = schema.load(data)
        assert result['nome'] == 'John Doe'
        assert result['telefone'] == '11987654321'
        assert result['email'] == 'john@example.com'
    
    def test_cliente_create_schema_missing_required(self):
        """Testa validação de campos obrigatórios"""
        schema = ClienteCreateSchema()
        
        data = {
            'nome': 'John Doe'
            # Faltam telefone
        }
        
        with pytest.raises(ValidationError) as exc_info:
            schema.load(data)
        
        errors = exc_info.value.messages
        assert 'telefone' in errors
    
    def test_cliente_create_schema_invalid_email(self):
        """Testa validação de email"""
        schema = ClienteCreateSchema()
        
        data = {
            'nome': 'John Doe',
            'telefone': '11987654321',
            'email': 'email_invalido'  # Email inválido
        }
        
        with pytest.raises(ValidationError) as exc_info:
            schema.load(data)
        
        errors = exc_info.value.messages
        assert 'email' in errors
    
    def test_cliente_update_schema_partial(self):
        """Testa atualização parcial de cliente"""
        schema = ClienteUpdateSchema()
        
        data = {
            'email': 'novo@example.com'
        }
        
        result = schema.load(data)
        assert result['email'] == 'novo@example.com'

