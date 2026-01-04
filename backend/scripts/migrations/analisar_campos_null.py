# -*- coding: utf-8 -*-
"""
Script para analisar campos NULL na tabela pedidos
e identificar colunas que podem ser removidas
"""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

from sqlalchemy import text  # noqa: E402

from app import create_app, db  # noqa: E402


def analisar_campos():
    """Analisa campos NULL na tabela pedidos"""
    app = create_app()

    with app.app_context():
        print("=" * 60)
        print("ANÁLISE DE CAMPOS NULL NA TABELA PEDIDOS")
        print("=" * 60)

        # Conta total de pedidos
        result = db.session.execute(text("SELECT COUNT(*) FROM pedidos"))
        total = result.scalar()
        print(f"\nTotal de pedidos: {total}\n")

        if total == 0:
            print("Nenhum pedido para analisar.")
            return

        # Campos para analisar
        campos = [
            "flores_cor",
            "valor",
            "cep",
            "rua",
            "numero",
            "bairro",
            "cidade",
            "endereco",
            "obs_entrega",
            "mensagem",
            "pagamento",
            "observacoes",
            "fonte_pedido",
            "fonte_pedido_id",
            "status_pagamento",
            "cliente_id",
            "distancia_km",
            "taxa_entrega",
            "coords_lat",
            "coords_lon",
            "updated_at",
        ]

        print(f"{'Campo':<20} {'NULLs':<10} {'Preenchidos':<12} {'% NULL':<10}")
        print("-" * 55)

        campos_sempre_null = []

        for campo in campos:
            try:
                result = db.session.execute(
                    text(f"SELECT COUNT(*) FROM pedidos WHERE {campo} IS NULL OR {campo} = ''")
                )
                nulls = result.scalar()
                preenchidos = total - nulls
                pct = (nulls / total) * 100

                print(f"{campo:<20} {nulls:<10} {preenchidos:<12} {pct:.1f}%")

                if nulls == total:
                    campos_sempre_null.append(campo)
            except Exception as e:
                print(f"{campo:<20} Erro: {e}")

        if campos_sempre_null:
            print("\n" + "=" * 60)
            print("CAMPOS SEMPRE NULL (candidatos a remoção):")
            print("=" * 60)
            for campo in campos_sempre_null:
                print(f"  - {campo}")

            print("\n⚠ ATENÇÃO: Remover colunas do SQLite requer recriar a tabela.")
            print("  Recomendado: manter as colunas mas ignorá-las no código.")

        # Verifica campo fonte_pedido deprecated
        result = db.session.execute(
            text(
                "SELECT COUNT(*) FROM pedidos WHERE fonte_pedido IS NOT NULL AND fonte_pedido != ''"
            )
        )
        fonte_antiga = result.scalar()

        if fonte_antiga > 0:
            print(
                f"\n⚠ {fonte_antiga} pedidos ainda usam 'fonte_pedido' (string) ao invés de 'fonte_pedido_id'"
            )


def limpar_fonte_pedido_string():
    """Move dados de fonte_pedido (string) para fonte_pedido_id"""
    app = create_app()

    with app.app_context():
        from app.models.fonte_pedido import FontePedido
        from app.models.pedido import Pedido

        print("\nMigrando fonte_pedido string -> fonte_pedido_id...")

        pedidos = Pedido.query.filter(
            Pedido.fonte_pedido.isnot(None),
            Pedido.fonte_pedido != "",
            Pedido.fonte_pedido_id.is_(None),
        ).all()

        for pedido in pedidos:
            fonte = FontePedido.query.filter_by(nome=pedido.fonte_pedido).first()
            if fonte:
                pedido.fonte_pedido_id = fonte.id
                print(f"  Pedido #{pedido.id}: '{pedido.fonte_pedido}' -> ID {fonte.id}")

        db.session.commit()
        print(f"✓ {len(pedidos)} pedidos atualizados")


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument("--migrar", action="store_true", help="Migrar fonte_pedido string para ID")
    args = parser.parse_args()

    analisar_campos()

    if args.migrar:
        limpar_fonte_pedido_string()
