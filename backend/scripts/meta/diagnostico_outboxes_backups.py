# -*- coding: utf-8 -*-
"""
Script de diagnóstico completo: Outboxes e Backups
Verifica:
1. Criação de outboxes do dia
2. Envio de outboxes (agendador de tarefas)
3. Backups recentes do sistema
"""
import sys
import subprocess
from pathlib import Path
from datetime import datetime, date, timedelta

try:
    from zoneinfo import ZoneInfo
except ImportError:
    from backports.zoneinfo import ZoneInfo

# Adicionar diretório raiz ao path
backend_dir = Path(__file__).parent.parent.parent
sys.path.insert(0, str(backend_dir))

# Carregar variáveis de ambiente
from dotenv import load_dotenv

env_path = backend_dir / ".env"
load_dotenv(env_path, override=True)

from sqlalchemy import func

from app import create_app, db
from app.models.meta_capi_outbox import MetaCapiOutbox
from app.models.pedido import Pedido
from app.utils.backup_helper import get_backup_stats, get_last_backup_time, has_recent_backup
from app.utils.backup_helper import BackupManager
from app.config import Config

# Timezone do Brasil
TIMEZONE_BRASIL = ZoneInfo("America/Sao_Paulo")

# Nome da tarefa agendada
TASK_NAME = "GestorPedidos_MetaCAPI_Daily"


def verificar_agendador_tarefas():
    """Verifica status da tarefa agendada no Windows Task Scheduler"""
    print("=" * 60)
    print("1. VERIFICAÇÃO DO AGENDADOR DE TAREFAS")
    print("=" * 60)
    print()

    try:
        # Verificar se tarefa existe
        result = subprocess.run(
            ["powershell", "-Command", f"Get-ScheduledTask -TaskName '{TASK_NAME}' -ErrorAction SilentlyContinue"],
            capture_output=True,
            text=True,
            timeout=10
        )

        if result.returncode != 0 or not result.stdout.strip():
            print(f"[AVISO] Tarefa '{TASK_NAME}' não encontrada!")
            print("[INFO] Execute: backend\\scripts\\meta\\install_meta_capi_task.ps1")
            print()
            return False

        # Obter informações da tarefa
        info_result = subprocess.run(
            ["powershell", "-Command", f"Get-ScheduledTaskInfo -TaskName '{TASK_NAME}' | ConvertTo-Json"],
            capture_output=True,
            text=True,
            timeout=10
        )

        if info_result.returncode == 0:
            print(f"[OK] Tarefa '{TASK_NAME}' encontrada")
            # Parse básico do JSON (simplificado)
            if "LastRunTime" in info_result.stdout:
                print(f"[INFO] Última execução: Verifique no Agendador de Tarefas")
            if "LastTaskResult" in info_result.stdout:
                print(f"[INFO] Último resultado: Verifique no Agendador de Tarefas")
        else:
            print(f"[OK] Tarefa '{TASK_NAME}' encontrada")
            print("[INFO] Execute 'Get-ScheduledTaskInfo -TaskName' para mais detalhes")

        print()
        return True

    except Exception as e:
        print(f"[ERRO] Erro ao verificar agendador: {e}")
        print("[INFO] Verifique manualmente no Agendador de Tarefas do Windows")
        print()
        return False


def verificar_outboxes_do_dia():
    """Verifica criação e envio de outboxes do dia"""
    print("=" * 60)
    print("2. VERIFICAÇÃO DE OUTBOXES DO DIA")
    print("=" * 60)
    print()

    hoje = datetime.now(TIMEZONE_BRASIL).date()
    inicio_dia = datetime.combine(hoje, datetime.min.time(), tzinfo=TIMEZONE_BRASIL)
    fim_dia = datetime.combine(
        hoje, datetime.max.time().replace(microsecond=0), tzinfo=TIMEZONE_BRASIL
    )

    # Pedidos pagos criados/atualizados hoje
    pedidos_pagos_hoje = (
        Pedido.query.filter(
            func.upper(Pedido.status_pagamento).in_(["PAGO", "PARCIAL"]),
            Pedido.updated_at >= inicio_dia,
            Pedido.updated_at <= fim_dia,
            Pedido.deleted_at.is_(None),
        )
        .order_by(Pedido.updated_at.desc())
        .all()
    )

    print(f"[INFO] Data de referência: {hoje}")
    print(f"[INFO] Pedidos pagos criados/atualizados hoje: {len(pedidos_pagos_hoje)}")
    print()

    # Outboxes criadas hoje
    outboxes_criadas_hoje = (
        MetaCapiOutbox.query.filter(
            MetaCapiOutbox.created_at >= inicio_dia,
            MetaCapiOutbox.created_at <= fim_dia,
        )
        .order_by(MetaCapiOutbox.created_at.desc())
        .all()
    )

    print(f"[INFO] Outboxes criadas hoje: {len(outboxes_criadas_hoje)}")
    print()

    # Verificar pedidos pagos hoje SEM outbox
    pedidos_sem_outbox = []
    for pedido in pedidos_pagos_hoje:
        existing = MetaCapiOutbox.query.filter_by(order_id=pedido.id).first()
        if not existing:
            pedidos_sem_outbox.append(pedido)

    if pedidos_sem_outbox:
        print(f"[AVISO] Pedidos pagos hoje SEM outbox: {len(pedidos_sem_outbox)}")
        print("[INFO] Estes pedidos deveriam ter outbox criada:")
        for pedido in pedidos_sem_outbox[:10]:  # Mostrar até 10
            print(f"  - Pedido #{pedido.id} | Status: {pedido.status_pagamento} | Atualizado: {pedido.updated_at}")
        if len(pedidos_sem_outbox) > 10:
            print(f"  ... e mais {len(pedidos_sem_outbox) - 10} pedidos")
        print()
        print("[SOLUÇÃO] Execute: python backend\\scripts\\meta\\criar_outbox_faltantes.py")
        print()
    else:
        print("[OK] Todos os pedidos pagos hoje têm outbox criada")
        print()

    # Outboxes enviadas hoje
    outboxes_enviadas_hoje = (
        MetaCapiOutbox.query.filter(
            MetaCapiOutbox.sent_at >= inicio_dia,
            MetaCapiOutbox.sent_at <= fim_dia,
        )
        .order_by(MetaCapiOutbox.sent_at.desc())
        .all()
    )

    print(f"[INFO] Outboxes enviadas hoje: {len(outboxes_enviadas_hoje)}")
    if outboxes_enviadas_hoje:
        print("[INFO] Últimas 5 outboxes enviadas:")
        for outbox in outboxes_enviadas_hoje[:5]:
            pedido = Pedido.query.get(outbox.order_id)
            print(
                f"  - Pedido #{outbox.order_id} | Enviado: {outbox.sent_at.strftime('%H:%M:%S')} | "
                f"Tentativas: {outbox.attempts}"
            )
        print()

    # Outboxes pendentes
    outboxes_pendentes = (
        MetaCapiOutbox.query.filter_by(status="pending")
        .order_by(MetaCapiOutbox.created_at.asc())
        .all()
    )

    print(f"[INFO] Outboxes pendentes (total): {len(outboxes_pendentes)}")
    if outboxes_pendentes:
        print("[INFO] Primeiras 5 pendentes:")
        for outbox in outboxes_pendentes[:5]:
            pedido = Pedido.query.get(outbox.order_id)
            print(
                f"  - Pedido #{outbox.order_id} | Criado: {outbox.created_at.strftime('%Y-%m-%d %H:%M:%S')}"
            )
        print()

    # Outboxes falhadas retryable
    outboxes_failed_retryable = (
        MetaCapiOutbox.query.filter_by(status="failed", error_type="retryable")
        .filter(MetaCapiOutbox.attempts < 3)
        .order_by(MetaCapiOutbox.updated_at.desc())
        .all()
    )

    print(f"[INFO] Outboxes falhadas retryable (tentativas < 3): {len(outboxes_failed_retryable)}")
    if outboxes_failed_retryable:
        print("[INFO] Primeiras 5 falhadas retryable:")
        for outbox in outboxes_failed_retryable[:5]:
            error_preview = (
                outbox.last_error[:50] + "..." if outbox.last_error and len(outbox.last_error) > 50
                else outbox.last_error or "N/A"
            )
            print(
                f"  - Pedido #{outbox.order_id} | Tentativas: {outbox.attempts} | "
                f"Erro: {error_preview}"
            )
        print()

    # Estatísticas gerais
    total_outboxes = MetaCapiOutbox.query.count()
    total_pending = MetaCapiOutbox.query.filter_by(status="pending").count()
    total_sent = MetaCapiOutbox.query.filter_by(status="sent").count()
    total_failed = MetaCapiOutbox.query.filter_by(status="failed").count()

    print("[INFO] ESTATÍSTICAS GERAIS:")
    print(f"  Total de outboxes: {total_outboxes}")
    print(f"  Pendentes: {total_pending}")
    print(f"  Enviadas: {total_sent}")
    print(f"  Falhadas: {total_failed}")
    print()

    return {
        "pedidos_pagos_hoje": len(pedidos_pagos_hoje),
        "outboxes_criadas_hoje": len(outboxes_criadas_hoje),
        "outboxes_enviadas_hoje": len(outboxes_enviadas_hoje),
        "pedidos_sem_outbox": len(pedidos_sem_outbox),
        "outboxes_pendentes": len(outboxes_pendentes),
        "outboxes_failed_retryable": len(outboxes_failed_retryable),
    }


def verificar_backups():
    """Verifica backups recentes do sistema"""
    print("=" * 60)
    print("3. VERIFICAÇÃO DE BACKUPS")
    print("=" * 60)
    print()

    try:
        # Estatísticas gerais
        stats = get_backup_stats()
        print(f"[INFO] Total de backups: {stats['count']}")
        print(f"[INFO] Tamanho total: {stats['total_size_mb']:.2f} MB")
        if stats['oldest']:
            print(f"[INFO] Backup mais antigo: {stats['oldest'].strftime('%Y-%m-%d %H:%M:%S')}")
        if stats['newest']:
            print(f"[INFO] Backup mais recente: {stats['newest'].strftime('%Y-%m-%d %H:%M:%S')}")
        print()

        # Último backup
        last_backup = get_last_backup_time()
        if last_backup:
            backup_path, mod_time, size_mb = last_backup
            print(f"[INFO] Último backup:")
            print(f"  Arquivo: {backup_path.name}")
            print(f"  Data/hora: {mod_time.strftime('%Y-%m-%d %H:%M:%S')}")
            print(f"  Tamanho: {size_mb:.2f} MB")
            
            # Verificar se é recente (últimas 24h)
            agora = datetime.now(TIMEZONE_BRASIL)
            horas_atras = (agora - mod_time.replace(tzinfo=TIMEZONE_BRASIL)).total_seconds() / 3600
            
            if horas_atras <= 24:
                print(f"[OK] Backup recente (há {horas_atras:.1f} horas)")
            else:
                print(f"[AVISO] Backup antigo (há {horas_atras:.1f} horas)")
            print()
        else:
            print("[AVISO] Nenhum backup encontrado!")
            print()

        # Listar últimos 5 backups
        db_path = Config.DATABASE_PATH
        backend_dir = Path(__file__).parent.parent.parent
        instance_dir = backend_dir / "instance"
        backup_dir = instance_dir / "backups"
        
        backup_mgr = BackupManager(db_path=db_path, backup_dir=backup_dir)
        backups = backup_mgr.list_backups()
        
        if backups:
            print("[INFO] Últimos 5 backups:")
            for i, (backup_path, size_mb, mod_time) in enumerate(backups[:5], 1):
                print(
                    f"  {i}. {backup_path.name} ({size_mb:.2f} MB) - "
                    f"{mod_time.strftime('%Y-%m-%d %H:%M:%S')}"
                )
            print()
        else:
            print("[AVISO] Nenhum backup encontrado no diretório")
            print()

        # Verificar backup agendado
        print("[INFO] Verificando tarefa de backup agendada...")
        try:
            backup_task_result = subprocess.run(
                ["powershell", "-Command", "Get-ScheduledTask | Where-Object {$_.TaskName -like '*Backup*'} | Select-Object -First 1 -ExpandProperty TaskName"],
                capture_output=True,
                text=True,
                timeout=10
            )
            
            if backup_task_result.returncode == 0 and backup_task_result.stdout.strip():
                task_name = backup_task_result.stdout.strip()
                print(f"[OK] Tarefa de backup encontrada: {task_name}")
            else:
                print("[AVISO] Nenhuma tarefa de backup encontrada")
                print("[INFO] Execute: backend\\scripts\\backup\\install_backup_task.ps1")
        except Exception as e:
            print(f"[AVISO] Erro ao verificar tarefa de backup: {e}")
        
        print()

    except Exception as e:
        print(f"[ERRO] Erro ao verificar backups: {e}")
        import traceback
        traceback.print_exc()
        print()


def main():
    """Função principal"""
    app = create_app()

    with app.app_context():
        print("=" * 60)
        print("DIAGNÓSTICO COMPLETO: OUTBOXES E BACKUPS")
        print("=" * 60)
        print()
        print(f"Data/hora: {datetime.now(TIMEZONE_BRASIL).strftime('%Y-%m-%d %H:%M:%S')}")
        print()

        # 1. Verificar agendador de tarefas
        task_ok = verificar_agendador_tarefas()

        # 2. Verificar outboxes do dia
        outbox_stats = verificar_outboxes_do_dia()

        # 3. Verificar backups
        verificar_backups()

        # Resumo final
        print("=" * 60)
        print("RESUMO FINAL")
        print("=" * 60)
        print()

        # Agendador
        if task_ok:
            print("[OK] Tarefa agendada configurada")
        else:
            print("[AVISO] Tarefa agendada não encontrada ou com problemas")

        # Outboxes
        if outbox_stats["pedidos_sem_outbox"] == 0:
            print("[OK] Todos os pedidos pagos hoje têm outbox")
        else:
            print(f"[AVISO] {outbox_stats['pedidos_sem_outbox']} pedidos pagos hoje sem outbox")

        if outbox_stats["outboxes_enviadas_hoje"] > 0:
            print(f"[OK] {outbox_stats['outboxes_enviadas_hoje']} outboxes enviadas hoje")
        else:
            print("[AVISO] Nenhuma outbox enviada hoje")

        if outbox_stats["outboxes_pendentes"] > 0:
            print(f"[INFO] {outbox_stats['outboxes_pendentes']} outboxes pendentes aguardando envio")

        if outbox_stats["outboxes_failed_retryable"] > 0:
            print(f"[INFO] {outbox_stats['outboxes_failed_retryable']} outboxes falhadas retryable serão retentadas")

        # Backups
        has_recent = has_recent_backup(hours=24)
        if has_recent:
            print("[OK] Backup recente encontrado (últimas 24h)")
        else:
            print("[AVISO] Nenhum backup recente encontrado (últimas 24h)")

        print()
        print("=" * 60)
        print("FIM DO DIAGNÓSTICO")
        print("=" * 60)


if __name__ == "__main__":
    main()