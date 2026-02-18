# -*- coding: utf-8 -*-
"""
Script para criar outboxes faltantes (backfill)
Busca pedidos com status_pagamento="Pago" ou "Parcial" que ainda não têm outbox
e cria os registros faltantes
"""
import sys
from pathlib import Path

# Adicionar diretório raiz ao path
backend_dir = Path(__file__).parent.parent.parent
sys.path.insert(0, str(backend_dir))

# Carregar variáveis de ambiente do arquivo .env ANTES de importar app
from dotenv import load_dotenv

env_path = backend_dir / ".env"
load_dotenv(env_path)

from sqlalchemy import func

from app import create_app
from app.models.meta_capi_outbox import MetaCapiOutbox
from app.models.pedido import Pedido
from app.repositories.meta_capi_outbox_repository import MetaCapiOutboxRepository

app = create_app()


def criar_outbox_faltantes(limit=None, dry_run=False):
    """
    Cria outboxes faltantes para pedidos pagos

    Args:
        limit: Limite de pedidos para processar (None = todos)
        dry_run: Se True, apenas mostra o que seria criado sem criar

    Returns:
        dict: Estatísticas do processamento
    """
    with app.app_context():
        print("=" * 60)
        print("CRIAR OUTBOXES FALTANTES (BACKFILL)")
        print("=" * 60)
        print()

        if dry_run:
            print("[DRY-RUN] MODO DRY-RUN: Nenhuma outbox será criada")
            print()

        # Buscar pedidos com status_pagamento="Pago" ou "Parcial" (case-insensitive)
        # que ainda não têm outbox
        query = (
            Pedido.query.filter(
                func.upper(Pedido.status_pagamento).in_(["PAGO", "PARCIAL"]),
                Pedido.deleted_at.is_(None),  # Excluir soft-deleted
            )
            .outerjoin(MetaCapiOutbox, Pedido.id == MetaCapiOutbox.order_id)  # LEFT JOIN com outbox
            .filter(MetaCapiOutbox.id.is_(None))  # Apenas pedidos SEM outbox
            .order_by(Pedido.updated_at.desc())
        )

        if limit:
            query = query.limit(limit)

        pedidos_sem_outbox = query.all()

        print(f"[INFO] Pedidos encontrados sem outbox: {len(pedidos_sem_outbox)}")
        print()

        if not pedidos_sem_outbox:
            print("[OK] Nenhum pedido sem outbox encontrado!")
            return {
                "total_encontrados": 0,
                "criados": 0,
                "erros": 0,
                "erros_detalhes": [],
            }

        # Estatísticas
        stats = {
            "total_encontrados": len(pedidos_sem_outbox),
            "criados": 0,
            "erros": 0,
            "erros_detalhes": [],
        }

        # Processar cada pedido
        outbox_repo = MetaCapiOutboxRepository()

        print("[INFO] Processando pedidos...")
        print("-" * 60)

        for pedido in pedidos_sem_outbox:
            try:
                status_pagamento = pedido.status_pagamento or "N/A"
                valor = pedido.valor or "N/A"
                cliente = pedido.cliente or "N/A"

                print(
                    f"Pedido #{pedido.id} | {cliente[:30]:<30} | Status: {status_pagamento:<10} | Valor: {valor}"
                )

                if not dry_run:
                    # Criar outbox
                    outbox = outbox_repo.create_from_pedido(pedido)
                    if outbox:
                        stats["criados"] += 1
                        print(f"  [OK] Outbox criada: #{outbox.id}")
                    else:
                        # Já existe (race condition?)
                        print(
                            "  [AVISO] Outbox já existe (pode ter sido criada por outro processo)"
                        )
                else:
                    stats["criados"] += 1
                    print("  [DRY-RUN] Seria criada outbox")

            except Exception as e:
                stats["erros"] += 1
                error_msg = f"Erro ao criar outbox para pedido #{pedido.id}: {str(e)}"
                stats["erros_detalhes"].append(error_msg)
                print(f"  [ERRO] {error_msg}")

        print()
        print("=" * 60)
        print("RESUMO")
        print("=" * 60)
        print(f"Total encontrados: {stats['total_encontrados']}")
        print(f"Outboxes criadas: {stats['criados']}")
        print(f"Erros: {stats['erros']}")

        if stats["erros"] > 0:
            print()
            print("Erros detalhados:")
            for erro in stats["erros_detalhes"]:
                print(f"  - {erro}")

        return stats


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Criar outboxes faltantes para pedidos pagos")
    parser.add_argument(
        "--limit",
        type=int,
        default=None,
        help="Limite de pedidos para processar (padrão: todos)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Modo dry-run: mostra o que seria criado sem criar",
    )

    args = parser.parse_args()

    try:
        stats = criar_outbox_faltantes(limit=args.limit, dry_run=args.dry_run)

        if stats["erros"] > 0:
            sys.exit(1)
        else:
            sys.exit(0)
    except KeyboardInterrupt:
        print("\n\n[AVISO] Operação cancelada pelo usuário")
        sys.exit(1)
    except Exception as e:
        print(f"\n\n[ERRO] Erro fatal: {str(e)}")
        import traceback

        traceback.print_exc()
        sys.exit(1)
