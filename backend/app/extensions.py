# -*- coding: utf-8 -*-
"""
Extensões Flask - Inicialização de extensões
Gerencia instância global do SQLAlchemy, Flask-Migrate e inicialização do banco de dados
"""
import os
import sys
from pathlib import Path

from flask_migrate import Migrate
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import Engine, event, text
from sqlalchemy.engine import make_url

# Instância global do SQLAlchemy
# CRÍTICO: Deve estar aqui para ser importada por models via 'from app import db'
db = SQLAlchemy()

# Instância global do Flask-Migrate
migrate = Migrate()


def _is_sqlite(database_uri: str) -> bool:
    """Retorna True se a URI for SQLite"""
    if not database_uri:
        return False
    url = make_url(database_uri)
    return url.drivername in ("sqlite", "sqlite+pysqlite")


def _get_sqlite_path(database_uri: str, app=None) -> Path:
    """Extrai e resolve caminho SQLite de forma determinística. Só usar quando _is_sqlite(uri)."""
    if not _is_sqlite(database_uri):
        raise ValueError(f"URI não é SQLite: {database_uri[:50]}...")
    url = make_url(database_uri)
    db_path_str = url.database

    if not db_path_str:
        raise ValueError(f"URI SQLite inválida: {database_uri}")

    db_path = Path(db_path_str)
    app_env = os.environ.get("APP_ENV") or os.environ.get("ENVIRONMENT", "development")
    is_production = app_env == "production"

    if db_path.is_absolute():
        return db_path.resolve()

    # Caminho relativo
    if is_production:
        raise ValueError(f"Em produção, DATABASE_PATH deve ser absoluto: {db_path}")

    # Dev: resolver contra app.instance_path (nunca cwd)
    if app:
        base_path = Path(app.instance_path)
    else:
        # Fallback se app não disponível
        from app.config import Config

        base_path = Config.INSTANCE_DIR

    return (base_path / db_path).resolve()


def configure_sqlite_pragmas():
    """Configura PRAGMAs via event hook (apenas SQLite)"""

    @event.listens_for(Engine, "connect")
    def set_sqlite_pragmas(dbapi_conn, connection_record):
        """Aplica PRAGMAs apenas em conexões SQLite"""
        # Verificar se é SQLite pelo engine/dialect
        try:
            # Tentar obter engine do connection_record
            if hasattr(connection_record, "dialect"):
                if connection_record.dialect.name != "sqlite":
                    return
            elif hasattr(connection_record, "connection") and hasattr(
                connection_record.connection, "engine"
            ):
                if connection_record.connection.engine.dialect.name != "sqlite":
                    return
            else:
                # Fallback: verificar pelo nome do módulo do driver
                driver_name = dbapi_conn.__class__.__module__.split(".")[0]
                if driver_name != "sqlite3":
                    return
        except Exception:
            # Se não conseguir verificar, não aplicar PRAGMAs (seguro)
            return

        cursor = dbapi_conn.cursor()
        cursor.execute("PRAGMA journal_mode = WAL")

        sync_mode = os.environ.get("SQLITE_SYNCHRONOUS", "FULL")
        cursor.execute(f"PRAGMA synchronous = {sync_mode}")

        # Foreign keys podem ser desabilitadas via variável de ambiente
        foreign_keys_enabled = os.environ.get("SQLITE_FOREIGN_KEYS", "ON").upper() in (
            "ON",
            "1",
            "TRUE",
            "YES",
        )
        if foreign_keys_enabled:
            cursor.execute("PRAGMA foreign_keys = ON")
        else:
            cursor.execute("PRAGMA foreign_keys = OFF")

        cursor.execute("PRAGMA busy_timeout = 5000")

        cursor.close()
        dbapi_conn.commit()


def _acquire_migration_lock(db_path: Path):
    """Adquire lock e retorna file descriptor (deve ser fechado no finally)"""
    lock_file = db_path.parent / f"{db_path.name}.migration.lock"
    fd = None

    try:
        if sys.platform == "win32":
            import msvcrt

            fd = open(lock_file, "w")
            msvcrt.locking(fd.fileno(), msvcrt.LK_NBLCK, 1)
        else:
            import fcntl

            fd = open(lock_file, "w")
            fcntl.flock(fd.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        return fd
    except (IOError, OSError) as e:
        if fd:
            fd.close()
        raise RuntimeError(f"Lock de migrations já adquirido: {e}") from e


def init_extensions(app):
    """
    Inicializa extensões Flask (SQLAlchemy, Flask-Migrate)

    Args:
        app: Instância da aplicação Flask
    """
    db.init_app(app)
    migrate.init_app(app, db)

    # Configurar PRAGMAs via event hook (apenas SQLite)
    configure_sqlite_pragmas()

    if _is_sqlite(app.config.get("SQLALCHEMY_DATABASE_URI", "")):
        foreign_keys_status = (
            "ON"
            if os.environ.get("SQLITE_FOREIGN_KEYS", "ON").upper() in ("ON", "1", "TRUE", "YES")
            else "OFF"
        )
        print(
            f"[DB] PRAGMAs configurados via event hook: WAL, synchronous, foreign_keys={foreign_keys_status}, busy_timeout"
        )
    else:
        print("[DB] PostgreSQL detectado - PRAGMAs não aplicados")


def init_database(app):
    """
    Inicializa banco de dados e cria tabelas

    Importa todos os models ANTES de criar tabelas para garantir que
    todas as tabelas sejam criadas corretamente.

    Args:
        app: Instância da aplicação Flask
    """
    with app.app_context():
        uri = app.config["SQLALCHEMY_DATABASE_URI"]
        app_env = os.environ.get("APP_ENV") or os.environ.get("ENVIRONMENT", "development")
        is_production = app_env == "production"
        allow_bootstrap = os.environ.get("ALLOW_DB_BOOTSTRAP", "").lower() == "true"

        if _is_sqlite(uri):
            db_path = _get_sqlite_path(uri, app)
            print(f"[DB] Caminho absoluto: {db_path.resolve()}")
            print(f"[DB] Arquivo existe: {db_path.exists()}")

            if db_path.exists():
                from datetime import datetime

                stat = db_path.stat()
                size_kb = stat.st_size / 1024
                mtime = datetime.fromtimestamp(stat.st_mtime)
                print(f"[DB] Tamanho: {size_kb:.2f} KB")
                print(f"[DB] Modificado: {mtime}")
            else:
                print("[DB] AVISO: Arquivo não existe!")

            if (
                is_production
                and not os.environ.get("APP_ENV")
                and not os.environ.get("ENVIRONMENT")
            ):
                print("[ERRO] APP_ENV ou ENVIRONMENT obrigatório em produção")
                sys.exit(1)

            if not db_path.exists():
                if is_production and not allow_bootstrap:
                    print(f"[ERRO] Banco não encontrado: {db_path}")
                    print("[ERRO] Em produção, banco deve existir ou usar ALLOW_DB_BOOTSTRAP=true")
                    print("[ERRO] Para criar banco: flask db upgrade (em DB vazio)")
                    sys.exit(1)
                print("[DB] Banco não existe - criando...")

            should_create = not db_path.exists() or allow_bootstrap
        else:
            # PostgreSQL: verificar conexão
            print("[DB] PostgreSQL - verificando conexão...")
            try:
                db.session.execute(text("SELECT 1"))
                db.session.commit()
                print("[DB] Conexão OK")
            except Exception as e:
                if is_production and not allow_bootstrap:
                    print(f"[ERRO] Falha ao conectar ao PostgreSQL: {e}")
                    sys.exit(1)
                print(f"[DB] AVISO: Falha ao conectar: {e}")
            should_create = allow_bootstrap

        # Importar todos os models ANTES de criar tabelas
        if should_create:
            db.create_all()
            print("[OK] Banco de dados inicializado")
            print(f"[OK] Tabelas criadas: {list(db.metadata.tables.keys())}")
        else:
            print("[OK] Banco de dados verificado")

        # Garante colunas adicionadas em versões posteriores sem migration manual.
        _ensure_runtime_columns()


def _ensure_runtime_columns():
    """Adiciona colunas novas idempotentemente (para evitar migration manual em prod).

    Cada entrada: (tabela, coluna, definição SQL pós-`ADD COLUMN`).
    """
    runtime_columns = [
        ("pedidos", "cartao_impresso", "BOOLEAN DEFAULT 0"),
    ]
    try:
        from sqlalchemy import inspect

        inspector = inspect(db.engine)
        for table, column, definition in runtime_columns:
            if table not in inspector.get_table_names():
                continue
            existing = {c["name"] for c in inspector.get_columns(table)}
            if column in existing:
                continue
            print(f"[DB] Adicionando coluna {table}.{column} (auto-ensure)...")
            db.session.execute(
                text(f"ALTER TABLE {table} ADD COLUMN {column} {definition}")
            )
            db.session.commit()
            print(f"[OK] Coluna {table}.{column} adicionada")
    except Exception as e:
        print(f"[DB] AVISO: ensure_runtime_columns falhou: {e}")
        try:
            db.session.rollback()
        except Exception:
            pass
