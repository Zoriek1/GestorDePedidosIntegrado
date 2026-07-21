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
        # Garante unicidade de nome de usuário (índice único parcial, case-insensitive).
        _ensure_user_name_unique_index()


def _ensure_runtime_columns():
    """Adiciona colunas novas idempotentemente (para evitar migration manual em prod).

    Cada entrada: (tabela, coluna, tipo_lógico). O default/SQL é resolvido
    conforme o dialeto (SQLite usa 0/1; PostgreSQL exige FALSE/TRUE).
    """
    runtime_columns = [
        ("pedidos", "cartao_impresso", "boolean_false"),
        ("pedidos", "regra_pagamento", "string_30"),
        ("pedidos", "percentual_entrada", "float"),
        ("pedidos", "valor_entrada", "numeric_12_2"),
        ("pedidos", "valor_restante", "numeric_12_2"),
        ("pedidos", "forma_pagamento_entrada", "string_50"),
        ("pedidos", "forma_pagamento_restante", "string_50"),
        ("pedidos", "entrada_recebida_at", "datetime"),
        ("pedidos", "saldo_recebido_at", "datetime"),
    ]
    try:
        from sqlalchemy import inspect

        dialect = db.engine.dialect.name  # 'sqlite' | 'postgresql' | ...
        is_postgres = dialect == "postgresql"
        inspector = inspect(db.engine)

        bling_table_names = {
            "bling_credentials",
            "bling_payment_methods",
            "bling_financial_accounts",
            "bling_categories",
            "bling_payment_mapping",
            "bling_outbox",
            "bling_integration_logs",
        }
        existing_tables = set(inspector.get_table_names())
        missing_bling_tables = bling_table_names - existing_tables
        if missing_bling_tables:
            print(f"[DB] Criando tabelas Bling ausentes: {sorted(missing_bling_tables)}")
            db.create_all()
            inspector = inspect(db.engine)
            print("[OK] Tabelas Bling verificadas/criadas")

        def _column_def(kind: str) -> str:
            if kind == "boolean_false":
                if is_postgres:
                    return "BOOLEAN NOT NULL DEFAULT FALSE"
                return "BOOLEAN NOT NULL DEFAULT 0"
            if kind == "string_30":
                return "VARCHAR(30)"
            if kind == "string_50":
                return "VARCHAR(50)"
            if kind == "float":
                return "FLOAT"
            if kind == "numeric_12_2":
                return "NUMERIC(12, 2)"
            if kind == "datetime":
                return "TIMESTAMP" if is_postgres else "DATETIME"
            raise ValueError(f"Tipo desconhecido: {kind}")

        for table, column, kind in runtime_columns:
            if table not in inspector.get_table_names():
                continue
            existing = {c["name"] for c in inspector.get_columns(table)}
            if column in existing:
                continue
            definition = _column_def(kind)
            print(f"[DB] Adicionando coluna {table}.{column} ({dialect})...")
            db.session.execute(text(f"ALTER TABLE {table} ADD COLUMN {column} {definition}"))
            db.session.commit()
            print(f"[OK] Coluna {table}.{column} adicionada")
    except Exception as e:
        print(f"[DB] AVISO: ensure_runtime_columns falhou: {e}")
        try:
            db.session.rollback()
        except Exception:
            pass


def _ensure_user_name_unique_index():
    """Cria índice ÚNICO PARCIAL (só usuários ativos), case-insensitive, em users.name.

    Motivação: o login aceita e-mail OU nome; sem unicidade, dois usuários com o
    mesmo nome tornam o login por nome ambíguo (poderia entrar na conta errada).

    Decisões:
      - Parcial (WHERE is_active): soft-deletes/anonimizados (is_active=0) não colidem
        e nomes podem ser reusados após desativação (igual ao comportamento de e-mail).
      - Case-insensitive: casa com o login que compara lower(name).
      - Fail-safe: se já houver nomes duplicados entre ativos, apenas AVISA e NÃO cria
        o índice (não quebra o boot). Resolva os duplicados e reinicie para aplicar.
    """
    index_name = "ux_users_name_active_ci"
    try:
        from sqlalchemy import inspect

        inspector = inspect(db.engine)
        if "users" not in inspector.get_table_names():
            return
        existing_indexes = {ix.get("name") for ix in inspector.get_indexes("users")}
        if index_name in existing_indexes:
            return

        is_postgres = db.engine.dialect.name == "postgresql"
        # Predicado booleano portável (Postgres não aceita `is_active = 1`).
        active_pred = "is_active" if is_postgres else "is_active = 1"

        # Pré-checagem: existem nomes duplicados entre usuários ativos?
        dups = db.session.execute(
            text(
                "SELECT LOWER(name) AS n, COUNT(*) AS c FROM users "
                f"WHERE {active_pred} GROUP BY LOWER(name) HAVING COUNT(*) > 1"
            )
        ).fetchall()
        if dups:
            nomes = ", ".join(str(row[0]) for row in dups)
            print(
                "[DB] AVISO: índice único de nome NÃO criado — há nomes duplicados "
                f"entre usuários ativos: {nomes}. Resolva e reinicie para aplicar."
            )
            return

        if is_postgres:
            stmt = (
                f"CREATE UNIQUE INDEX IF NOT EXISTS {index_name} "
                f"ON users (LOWER(name)) WHERE {active_pred}"
            )
        else:
            stmt = (
                f"CREATE UNIQUE INDEX IF NOT EXISTS {index_name} "
                f"ON users (name COLLATE NOCASE) WHERE {active_pred}"
            )
        db.session.execute(text(stmt))
        db.session.commit()
        print(f"[OK] Índice único de nome criado: {index_name}")
    except Exception as e:
        print(f"[DB] AVISO: _ensure_user_name_unique_index falhou: {e}")
        try:
            db.session.rollback()
        except Exception:
            pass
