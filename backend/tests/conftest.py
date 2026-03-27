# -*- coding: utf-8 -*-
"""
Configuração de testes - Fixtures compartilhadas
"""
import os
import sys
import tempfile
from pathlib import Path

import pytest

# Adicionar backend ao path para que os imports funcionem
backend_dir = Path(__file__).parent.parent
if str(backend_dir) not in sys.path:
    sys.path.insert(0, str(backend_dir))

# Os testes usam Basic auth admin:testpass (ver test_leads.py, etc.).
# Em Docker, ADMIN_PASSWORD vem do Compose e setdefault não sobrescreve → 401.
if os.environ.get("PYTEST_KEEP_ADMIN_PASSWORD") != "1":
    os.environ["ADMIN_PASSWORD"] = "testpass"

from app import create_app, db  # noqa: E402


@pytest.fixture
def app():
    """Cria aplicação Flask para testes"""
    # Criar banco de dados temporário
    db_fd, db_path = tempfile.mkstemp()
    prev_fk_env = os.environ.get("SQLITE_FOREIGN_KEYS")
    os.environ["SQLITE_FOREIGN_KEYS"] = "OFF"

    # Configurar app para testes
    app = create_app(
        config={
            "TESTING": True,
            "SQLALCHEMY_DATABASE_URI": f"sqlite:///{db_path}",
            "SECRET_KEY": "test-secret-key",
            "WTF_CSRF_ENABLED": False,
        }
    )

    with app.app_context():
        db.create_all()
        yield app
        # Fechar sessão antes de dropar
        db.session.close()
        # SQLite com foreign_keys=ON pode falhar ao dropar tabelas em teardown
        # Desativar FK para garantir limpeza determinística no ambiente de teste
        with db.engine.connect() as conn:
            conn.execute(db.text("PRAGMA foreign_keys=OFF"))
            conn.commit()
        db.drop_all()
        db.engine.dispose()

    if prev_fk_env is None:
        os.environ.pop("SQLITE_FOREIGN_KEYS", None)
    else:
        os.environ["SQLITE_FOREIGN_KEYS"] = prev_fk_env

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
