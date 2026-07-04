# -*- coding: utf-8 -*-
"""
Migration: cria a tabela pedido_sugestoes_endereco.

Guarda sugestões de correção de endereço feitas pelo cliente na página pública de
acompanhamento. A equipe revisa e decide aplicar/ignorar. Idempotente: cria a tabela
apenas se ainda não existir (bancos novos já a recebem via db.create_all()).
"""
import sys
from pathlib import Path

backend_dir = Path(__file__).parent.parent.parent
sys.path.insert(0, str(backend_dir))

from app import create_app, db

app = create_app()


def create_table():
    with app.app_context():
        inspector = db.inspect(db.engine)
        if inspector.has_table("pedido_sugestoes_endereco"):
            print("[SKIP] Tabela 'pedido_sugestoes_endereco' já existe")
            return

        print("[MIGRATION] Criando tabela pedido_sugestoes_endereco...")
        # Importa o model e cria apenas a tabela dele.
        from app.models.pedido_sugestao_endereco import PedidoSugestaoEndereco

        PedidoSugestaoEndereco.__table__.create(bind=db.engine)
        print("[OK] Tabela 'pedido_sugestoes_endereco' criada")


if __name__ == "__main__":
    create_table()
