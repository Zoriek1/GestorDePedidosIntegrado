# -*- coding: utf-8 -*-
"""
Migration: busca de pedidos insensível a acento/caixa + performance (BUS-01).

Cria (Postgres only):
  - extensões pg_trgm e unaccent;
  - função IMMUTABLE f_unaccent(text) (wrapper indexável de unaccent);
  - índices GIN trigram em f_unaccent(cliente|destinatario|produto|endereco);
  - coluna gerada telefone_digits (só dígitos) + índice GIN trigram.

As extensões pg_trgm/unaccent são compartilhadas com o catálogo de arranjos (CAT-01).

Idempotente (IF NOT EXISTS / OR REPLACE). NO-OP em SQLite — lá a busca cai para
lower()/LIKE no repositório, sem trigram/unaccent.

Uso (VPS):
    docker compose exec backend python scripts/migrations/add_search_trgm_unaccent.py
"""

from app import create_app, db

STATEMENTS = [
    "CREATE EXTENSION IF NOT EXISTS pg_trgm",
    "CREATE EXTENSION IF NOT EXISTS unaccent",
    # unaccent é STABLE; o wrapper IMMUTABLE permite indexar (sem ele volta o seq scan).
    """
    CREATE OR REPLACE FUNCTION f_unaccent(text) RETURNS text AS
    $$ SELECT public.unaccent('public.unaccent', $1) $$
    LANGUAGE sql IMMUTABLE PARALLEL SAFE STRICT
    """,
    "CREATE INDEX IF NOT EXISTS idx_pedidos_cliente_trgm "
    "ON pedidos USING gin (f_unaccent(cliente) gin_trgm_ops)",
    "CREATE INDEX IF NOT EXISTS idx_pedidos_destinatario_trgm "
    "ON pedidos USING gin (f_unaccent(destinatario) gin_trgm_ops)",
    "CREATE INDEX IF NOT EXISTS idx_pedidos_produto_trgm "
    "ON pedidos USING gin (f_unaccent(produto) gin_trgm_ops)",
    "CREATE INDEX IF NOT EXISTS idx_pedidos_endereco_trgm "
    "ON pedidos USING gin (f_unaccent(endereco) gin_trgm_ops)",
    # Telefone normalizado (só dígitos) como coluna gerada + índice trigram.
    "ALTER TABLE pedidos ADD COLUMN IF NOT EXISTS telefone_digits text "
    "GENERATED ALWAYS AS (regexp_replace(telefone_cliente, '\\D', '', 'g')) STORED",
    "CREATE INDEX IF NOT EXISTS idx_pedidos_tel "
    "ON pedidos USING gin (telefone_digits gin_trgm_ops)",
]


def run() -> bool:
    dialect = db.engine.dialect.name
    print(f"[INFO] Dialeto: {dialect}")
    if dialect != "postgresql":
        print("[OK] SQLite/outro — nada a fazer (fallback lower()/LIKE no repositório).")
        return True

    for sql in STATEMENTS:
        compact = " ".join(sql.split())
        print(f"[INFO] Executando: {compact[:80]}...")
        db.session.execute(db.text(sql))
        db.session.commit()
    print("[OK] Extensões, f_unaccent, índices trigram e telefone_digits prontos.")
    return True


if __name__ == "__main__":
    print("=" * 60)
    print("Migration: busca trigram/unaccent (BUS-01)")
    print("=" * 60)
    with create_app().app_context():
        try:
            run()
        except Exception as e:
            print(f"[ERRO] {e}")
            db.session.rollback()
            raise
    print("=" * 60)
