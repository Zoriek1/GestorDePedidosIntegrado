#!/usr/bin/env python3
"""
Migration standalone — adiciona colunas de geocodificação em enderecos_clientes.
Usa psycopg2 direto, sem Flask.

Uso na VPS (dentro do container backend):
  docker exec -it <container_backend> python /app/backend/scripts/migrations/run_add_geocoding.py

Ou direto no host com acesso ao DB:
  DATABASE_URL=postgresql://user:pass@host:5432/db python run_add_geocoding.py
"""
import os
import sys

try:
    import psycopg2
except ImportError:
    print("[ERRO] psycopg2 não instalado. Instale com: pip install psycopg2-binary")
    sys.exit(1)

DATABASE_URL = os.environ.get(
    "DATABASE_URL",
    "postgresql://admin:Plante1998@db:5432/Pedidos_App",
)

TABLE = "enderecos_clientes"

COLUMNS = [
    ("lat", "FLOAT"),
    ("lng", "FLOAT"),
    ("location_type", "VARCHAR(30)"),
    ("place_id", "VARCHAR(255)"),
    ("confidence_status", "VARCHAR(20)"),
    ("geocode_provider", "VARCHAR(20)"),
    ("address_canonical", "VARCHAR(500)"),
    ("address_hash", "VARCHAR(64)"),
    ("last_geocoded_at", "TIMESTAMP"),
]


def main():
    print(f"Conectando em: {DATABASE_URL.split('@')[1] if '@' in DATABASE_URL else '***'}")
    conn = psycopg2.connect(DATABASE_URL)
    conn.autocommit = True
    cur = conn.cursor()

    # Verificar se tabela existe
    cur.execute(
        "SELECT 1 FROM information_schema.tables WHERE table_name = %s",
        (TABLE,),
    )
    if not cur.fetchone():
        print(f"[SKIP] Tabela '{TABLE}' não existe. Nada a fazer.")
        cur.close()
        conn.close()
        return

    # Colunas existentes
    cur.execute(
        "SELECT column_name FROM information_schema.columns WHERE table_name = %s",
        (TABLE,),
    )
    existing = {row[0] for row in cur.fetchall()}

    added = 0
    for col_name, col_type in COLUMNS:
        if col_name in existing:
            print(f"[SKIP] '{col_name}' já existe")
            continue
        cur.execute(f"ALTER TABLE {TABLE} ADD COLUMN {col_name} {col_type}")
        print(f"[OK]   '{col_name}' ({col_type}) adicionada")
        added += 1

    # Índice
    cur.execute(
        "SELECT 1 FROM pg_indexes WHERE tablename = %s AND indexname = %s",
        (TABLE, f"ix_{TABLE}_address_hash"),
    )
    if not cur.fetchone():
        cur.execute(
            f"CREATE INDEX ix_{TABLE}_address_hash ON {TABLE} (address_hash)"
        )
        print(f"[OK]   Índice ix_{TABLE}_address_hash criado")

    cur.close()
    conn.close()
    print(f"\n[DONE] {added} coluna(s) adicionada(s).")


if __name__ == "__main__":
    main()

