# -*- coding: utf-8 -*-
"""
Migration: Adicionar campos de geocodificação à tabela enderecos_clientes

Campos adicionados:
  - lat, lng (coordenadas geocodificadas)
  - location_type (ROOFTOP, RANGE_INTERPOLATED, etc.)
  - place_id (Google Place ID)
  - confidence_status (AUTO_OK, OK_WITH_CAUTION, NEEDS_REVIEW)
  - geocode_provider (ex: google)
  - address_canonical (string canônica para geocodificação)
  - address_hash (SHA-256 para detectar mudança)
  - last_geocoded_at (timestamp)
"""
import sys
from pathlib import Path

# Adicionar diretório raiz ao path
backend_dir = Path(__file__).parent.parent.parent
sys.path.insert(0, str(backend_dir))

from app import create_app, db

app = create_app()

NEW_COLUMNS = [
    ("lat", "FLOAT"),
    ("lng", "FLOAT"),
    ("location_type", "VARCHAR(30)"),
    ("place_id", "VARCHAR(255)"),
    ("confidence_status", "VARCHAR(20)"),
    ("geocode_provider", "VARCHAR(20)"),
    ("address_canonical", "VARCHAR(500)"),
    ("address_hash", "VARCHAR(64)"),
    ("last_geocoded_at", "DATETIME"),
]

TABLE = "enderecos_clientes"


def migrate():
    """Adiciona colunas de geocodificação ao enderecos_clientes."""
    with app.app_context():
        inspector = db.inspect(db.engine)

        if TABLE not in inspector.get_table_names():
            print(f"[SKIP] Tabela '{TABLE}' não existe. Nada a fazer.")
            return

        existing = [col["name"] for col in inspector.get_columns(TABLE)]
        added = 0

        for col_name, col_type in NEW_COLUMNS:
            if col_name in existing:
                print(f"[SKIP] Coluna '{col_name}' já existe em '{TABLE}'")
                continue
            sql = f"ALTER TABLE {TABLE} ADD COLUMN {col_name} {col_type}"
            db.session.execute(db.text(sql))
            added += 1
            print(f"[OK]   Coluna '{col_name}' ({col_type}) adicionada")

        # Criar índice em address_hash se não existir
        indexes = inspector.get_indexes(TABLE)
        hash_idx_exists = any("address_hash" in (idx.get("column_names") or []) for idx in indexes)
        if not hash_idx_exists and "address_hash" not in [
            c for c, _ in NEW_COLUMNS if c not in existing
        ]:
            # Coluna já existia antes — verificar se precisa de índice
            pass
        elif not hash_idx_exists:
            try:
                db.session.execute(
                    db.text(f"CREATE INDEX ix_{TABLE}_address_hash ON {TABLE} (address_hash)")
                )
                print(f"[OK]   Índice ix_{TABLE}_address_hash criado")
            except Exception as idx_err:
                print(f"[WARN] Índice address_hash não criado: {idx_err}")

        db.session.commit()
        print(f"\n[DONE] {added} coluna(s) adicionada(s) à tabela '{TABLE}'.")


if __name__ == "__main__":
    print("=" * 60)
    print("Migration: Geocodificação em enderecos_clientes")
    print("=" * 60)
    migrate()
    print("=" * 60)
