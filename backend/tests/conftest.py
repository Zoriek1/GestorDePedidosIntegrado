# -*- coding: utf-8 -*-
"""
Configuração de testes - Fixtures compartilhadas
"""
import pytest
import tempfile
import os
from pathlib import Path
from app import create_app, db
from app.config import Config


@pytest.fixture
def app():
    """Cria aplicação Flask para testes"""
    # Criar banco de dados temporário
    db_fd, db_path = tempfile.mkstemp()
    
    # Configurar app para testes
    app = create_app(config={
        'TESTING': True,
        'SQLALCHEMY_DATABASE_URI': f'sqlite:///{db_path}',
        'SECRET_KEY': 'test-secret-key',
        'WTF_CSRF_ENABLED': False
    })
    
    with app.app_context():
        db.create_all()
        yield app
        # Fechar todas as conexões antes de dropar
        db.session.close()
        db.engine.dispose()
        db.drop_all()
    
    os.close(db_fd)
    # Tentar deletar o arquivo, ignorar erro se ainda estiver em uso
    try:
        os.unlink(db_path)
    except (PermissionError, FileNotFoundError):
        pass


@pytest.fixture
def client(app):
    """Cliente de teste para requisições HTTP"""
    return app.test_client()


@pytest.fixture
def runner(app):
    """Runner para comandos CLI"""
    return app.test_cli_runner()


@pytest.fixture
def session(app):
    """Sessão de banco de dados para testes"""
    with app.app_context():
        # Usar a sessão do Flask-SQLAlchemy diretamente
        # Cada teste terá seu próprio app_context, então a sessão será isolada
        yield db.session
        
        # Limpar após cada teste
        db.session.rollback()
        db.session.remove()

