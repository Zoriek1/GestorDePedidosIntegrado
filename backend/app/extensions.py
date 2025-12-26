# -*- coding: utf-8 -*-
"""
Extensões Flask - Inicialização de extensões
Gerencia instância global do SQLAlchemy e inicialização do banco de dados
"""
from flask_sqlalchemy import SQLAlchemy

# Instância global do SQLAlchemy
# CRÍTICO: Deve estar aqui para ser importada por models via 'from app import db'
db = SQLAlchemy()


def init_extensions(app):
    """
    Inicializa extensões Flask (SQLAlchemy)
    
    Args:
        app: Instância da aplicação Flask
    """
    db.init_app(app)


def init_database(app):
    """
    Inicializa banco de dados e cria tabelas
    
    Importa todos os models ANTES de criar tabelas para garantir que
    todas as tabelas sejam criadas corretamente.
    
    Args:
        app: Instância da aplicação Flask
    """
    with app.app_context():
        # Importar todos os models ANTES de criar tabelas
        # Esta ordem é CRÍTICA para que db.create_all() crie todas as tabelas
        from app.models import Pedido, RotaOtimizada, Cliente, EnderecoCliente, FontePedido
        from app.models.pedido_fonte import PedidoFonte  # Não é model SQLAlchemy, mas precisa estar importado
        
        # Criar todas as tabelas
        db.create_all()
        
        print("[OK] Banco de dados inicializado")
        print(f"[OK] Tabelas criadas: {db.metadata.tables.keys()}")


