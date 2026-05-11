# -*- coding: utf-8 -*-
"""
Migration: Adicionar colunas parcelas_cartao e taxa_cartao_valor na tabela pedidos.

- parcelas_cartao: número de parcelas no cartão de crédito (1 = à vista).
- taxa_cartao_valor: snapshot da taxa do adquirente cobrada no momento do save.
  Mantém o cálculo de comissão estável mesmo se a config global de taxas mudar.
"""
import sys
from pathlib import Path

backend_dir = Path(__file__).parent.parent.parent
sys.path.insert(0, str(backend_dir))

from app import create_app, db  # noqa: E402

app = create_app()


def add_columns():
    with app.app_context():
        inspector = db.inspect(db.engine)
        existing = [col["name"] for col in inspector.get_columns("pedidos")]

        print("[MIGRATION] Adicionando colunas de taxa de cartão na tabela pedidos...")

        if "parcelas_cartao" not in existing:
            try:
                db.session.execute(
                    db.text("ALTER TABLE pedidos ADD COLUMN parcelas_cartao INTEGER NULL")
                )
                db.session.commit()
                print("[OK] Coluna 'parcelas_cartao' adicionada")
            except Exception as e:
                db.session.rollback()
                print(f"[ERRO] Erro ao adicionar coluna 'parcelas_cartao': {e}")
        else:
            print("[SKIP] Coluna 'parcelas_cartao' já existe")

        if "taxa_cartao_valor" not in existing:
            try:
                db.session.execute(
                    db.text("ALTER TABLE pedidos ADD COLUMN taxa_cartao_valor FLOAT NULL DEFAULT 0")
                )
                db.session.commit()
                print("[OK] Coluna 'taxa_cartao_valor' adicionada")
            except Exception as e:
                db.session.rollback()
                print(f"[ERRO] Erro ao adicionar coluna 'taxa_cartao_valor': {e}")
        else:
            print("[SKIP] Coluna 'taxa_cartao_valor' já existe")

        print("[OK] Migration concluída")


if __name__ == "__main__":
    add_columns()
