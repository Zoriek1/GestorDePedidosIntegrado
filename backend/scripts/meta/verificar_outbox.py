# -*- coding: utf-8 -*-
"""
Script para verificar registros na outbox Meta CAPI
Mostra estatísticas e lista registros por status
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

from app import create_app, db
from app.models.meta_capi_outbox import MetaCapiOutbox
from app.models.pedido import Pedido


def verificar_outbox(order_id=None):
    """Verifica registros na outbox Meta CAPI"""
    app = create_app()
    with app.app_context():
        print("=" * 60)
        print("VERIFICAÇÃO DE OUTBOX META CAPI")
        print("=" * 60)
        print()

        # Se order_id fornecido, buscar específico
        if order_id:
            entry = MetaCapiOutbox.query.filter_by(order_id=order_id).first()
            if entry:
                print(f"[OK] Outbox encontrada para pedido #{order_id}:")
                print(f"   ID: {entry.id}")
                print(f"   Event ID: {entry.event_id}")
                print(f"   Status: {entry.status}")
                print(f"   Tentativas: {entry.attempts}")
                print(f"   Criado em: {entry.created_at}")
                if entry.sent_at:
                    print(f"   Enviado em: {entry.sent_at}")
                if entry.last_error:
                    print(f"   Último erro: {entry.last_error}")
                if entry.error_type:
                    print(f"   Tipo de erro: {entry.error_type}")
                print()
            else:
                print(f"[ERRO] Nenhuma outbox encontrada para pedido #{order_id}")
                print()
            return

        # Estatísticas gerais
        total = MetaCapiOutbox.query.count()
        pending = MetaCapiOutbox.query.filter_by(status="pending").count()
        sent = MetaCapiOutbox.query.filter_by(status="sent").count()
        failed = MetaCapiOutbox.query.filter_by(status="failed").count()

        print("[INFO] ESTATISTICAS:")
        print(f"   Total de registros: {total}")
        print(f"   Pendentes: {pending}")
        print(f"   Enviados: {sent}")
        print(f"   Falhados: {failed}")
        print()

        # Listar últimos 10 registros
        print("[INFO] ULTIMOS 10 REGISTROS:")
        print("-" * 60)
        recent = (
            MetaCapiOutbox.query.order_by(MetaCapiOutbox.created_at.desc()).limit(10).all()
        )

        if not recent:
            print("   Nenhum registro encontrado")
        else:
            for entry in recent:
                status_label = {
                    "pending": "[PENDENTE]",
                    "sent": "[ENVIADO]",
                    "failed": "[FALHADO]",
                }.get(entry.status, "[?]")

                print(
                    f"{status_label} Pedido #{entry.order_id} | {entry.event_id} | {entry.status} | "
                    f"Tentativas: {entry.attempts} | Criado: {entry.created_at.strftime('%Y-%m-%d %H:%M:%S')}"
                )
        print()

        # Listar pendentes
        if pending > 0:
            print(f"[PENDENTE] REGISTROS PENDENTES ({pending}):")
            print("-" * 60)
            pendentes = (
                MetaCapiOutbox.query.filter_by(status="pending")
                .order_by(MetaCapiOutbox.created_at.asc())
                .limit(10)
                .all()
            )
            for entry in pendentes:
                pedido = Pedido.query.get(entry.order_id)
                cliente = pedido.cliente if pedido else "N/A"
                print(
                    f"   Pedido #{entry.order_id} ({cliente}) | Criado: {entry.created_at.strftime('%Y-%m-%d %H:%M:%S')}"
                )
            if pending > 10:
                print(f"   ... e mais {pending - 10} registros pendentes")
            print()

        # Listar falhados
        if failed > 0:
            print(f"[FALHADO] REGISTROS FALHADOS ({failed}):")
            print("-" * 60)
            falhados = (
                MetaCapiOutbox.query.filter_by(status="failed")
                .order_by(MetaCapiOutbox.updated_at.desc())
                .limit(10)
                .all()
            )
            for entry in falhados:
                pedido = Pedido.query.get(entry.order_id)
                cliente = pedido.cliente if pedido else "N/A"
                error_preview = (
                    entry.last_error[:50] + "..." if entry.last_error and len(entry.last_error) > 50 else entry.last_error or "N/A"
                )
                print(
                    f"   Pedido #{entry.order_id} ({cliente}) | Tentativas: {entry.attempts} | "
                    f"Tipo: {entry.error_type or 'N/A'} | Erro: {error_preview}"
                )
            if failed > 10:
                print(f"   ... e mais {failed - 10} registros falhados")
            print()


if __name__ == "__main__":
    # Aceitar order_id como argumento opcional
    order_id = None
    if len(sys.argv) > 1:
        try:
            order_id = int(sys.argv[1])
        except ValueError:
            print(f"[ERRO] Erro: '{sys.argv[1]}' não é um ID válido")
            print("Uso: python verificar_outbox.py [order_id]")
            sys.exit(1)

    verificar_outbox(order_id)
