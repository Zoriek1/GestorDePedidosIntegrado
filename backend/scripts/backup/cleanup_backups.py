# -*- coding: utf-8 -*-
"""
Script de Limpeza de Backups com Política GFS (P1.2)
Aplica política de retenção GFS a backups locais e remotos
"""
import argparse
import os
import sys
from pathlib import Path
from typing import Dict

# Adicionar backend ao path
backend_dir = Path(__file__).parent.parent.parent
if str(backend_dir) not in sys.path:
    sys.path.insert(0, str(backend_dir))

# Carregar .env se disponível
try:
    from dotenv import load_dotenv
    env_path = backend_dir / '.env'
    if env_path.exists():
        load_dotenv(env_path)
except ImportError:
    pass  # dotenv não instalado, continuar sem

from app.config import Config  # noqa: E402
from scripts.backup.retention import GFSRetentionPolicy, apply_gfs_retention  # noqa: E402

# Importar status (P1.5) com fallback
try:
    from scripts.backup.status import update_backup_status
    STATUS_AVAILABLE = True
except ImportError:
    STATUS_AVAILABLE = False


def count_backup_files(backup_dir: Path) -> int:
    """Conta arquivos de backup em um diretório"""
    if not backup_dir.exists():
        return 0

    patterns = ["database_*.db", "database_*.zip"]
    count = 0
    for pattern in patterns:
        count += len(list(backup_dir.glob(pattern)))
    return count


def cleanup_directory(
    backup_dir: Path,
    policy: GFSRetentionPolicy,
    dry_run: bool = False
) -> Dict[str, int]:
    """
    Aplica limpeza GFS em um diretório

    Returns:
        Dict com contadores: {'total': int, 'kept': int, 'deleted': int, 'by_slot': dict}
    """
    if not backup_dir.exists():
        print(f"[AVISO] Diretório não existe: {backup_dir}")
        return {'total': 0, 'kept': 0, 'deleted': 0, 'by_slot': {}}

    # Encontrar todos os backups
    backup_files = []
    patterns = ["database_*.db", "database_*.zip"]
    for pattern in patterns:
        backup_files.extend(backup_dir.glob(pattern))

    if not backup_files:
        print(f"[INFO] Nenhum backup encontrado em {backup_dir}")
        return {'total': 0, 'kept': 0, 'deleted': 0, 'by_slot': {}}

    print(f"[INFO] Encontrados {len(backup_files)} backups em {backup_dir}")

    # Aplicar política GFS
    result = apply_gfs_retention(backup_files, policy)

    to_keep = result['keep']
    to_delete = result['delete']

    print(f"[INFO] Política GFS: manter {len(to_keep)}, deletar {len(to_delete)}")

    # Deletar arquivos
    deleted_count = 0
    if not dry_run:
        for file_path in to_delete:
            try:
                file_path.unlink()
                deleted_count += 1
            except Exception as e:
                print(f"[ERRO] Erro ao deletar {file_path.name}: {e}")
    else:
        print(f"[DRY-RUN] Seriam deletados {len(to_delete)} arquivos:")
        for file_path in to_delete[:10]:  # Mostrar apenas primeiros 10
            print(f"  - {file_path.name}")
        if len(to_delete) > 10:
            print(f"  ... e mais {len(to_delete) - 10} arquivos")
        deleted_count = len(to_delete)

    return {
        'total': len(backup_files),
        'kept': len(to_keep),
        'deleted': deleted_count,
        'by_slot': {}
    }


def main():
    """Função principal"""
    parser = argparse.ArgumentParser(
        description='Aplicar política de retenção GFS a backups'
    )
    parser.add_argument('--local', action='store_true', help='Aplicar em backups locais')
    parser.add_argument('--remote', action='store_true', help='Aplicar em backups remotos')
    parser.add_argument('--dry-run', action='store_true', help='Apenas simular, não deletar')
    parser.add_argument('--policy-hourly', type=int, default=None, help='Limite de backups hourly')
    parser.add_argument('--policy-daily', type=int, default=None, help='Limite de backups daily')
    parser.add_argument('--policy-weekly', type=int, default=None, help='Limite de backups weekly')
    parser.add_argument('--policy-monthly', type=int, default=None, help='Limite de backups monthly')

    args = parser.parse_args()

    # Ler política de .env ou usar padrões
    policy = GFSRetentionPolicy(
        hourly=int(os.environ.get('BACKUP_RETENTION_HOURLY', '48')),
        daily=int(os.environ.get('BACKUP_RETENTION_DAILY', '30')),
        weekly=int(os.environ.get('BACKUP_RETENTION_WEEKLY', '12')),
        monthly=int(os.environ.get('BACKUP_RETENTION_MONTHLY', '12'))
    )

    # Override via argumentos
    if args.policy_hourly is not None:
        policy.hourly = args.policy_hourly
    if args.policy_daily is not None:
        policy.daily = args.policy_daily
    if args.policy_weekly is not None:
        policy.weekly = args.policy_weekly
    if args.policy_monthly is not None:
        policy.monthly = args.policy_monthly

    print("=" * 60)
    print("LIMPEZA DE BACKUPS - Política GFS (P1.2)")
    print("=" * 60)
    print("\nPolítica:")
    print(f"  Hourly: {policy.hourly}")
    print(f"  Daily: {policy.daily}")
    print(f"  Weekly: {policy.weekly}")
    print(f"  Monthly: {policy.monthly}")

    if args.dry_run:
        print("\n[DRY-RUN] Modo simulação - nenhum arquivo será deletado")

    print()

    # Limpar local
    if args.local:
        print("[LOCAL] Aplicando limpeza GFS em backups locais...")
        local_dir = Config.INSTANCE_DIR / 'backups'
        result = cleanup_directory(local_dir, policy, dry_run=args.dry_run)
        print(f"[LOCAL] Total: {result['total']}, Mantidos: {result['kept']}, Deletados: {result['deleted']}")
        print()

    # Limpar remoto
    if args.remote:
        print("[REMOTO] Aplicando limpeza GFS em backups remotos...")
        remote_dir = Config.GDRIVE_BACKUP_DIR
        if remote_dir.exists():
            result = cleanup_directory(remote_dir, policy, dry_run=args.dry_run)
            print(f"[REMOTO] Total: {result['total']}, Mantidos: {result['kept']}, Deletados: {result['deleted']}")
        else:
            print(f"[AVISO] Diretório remoto não acessível: {remote_dir}")
        print()

    # Se não especificou nenhum, limpar ambos
    if not args.local and not args.remote:
        print("[LOCAL] Aplicando limpeza GFS em backups locais...")
        local_dir = Config.INSTANCE_DIR / 'backups'
        result = cleanup_directory(local_dir, policy, dry_run=args.dry_run)
        print(f"[LOCAL] Total: {result['total']}, Mantidos: {result['kept']}, Deletados: {result['deleted']}")
        print()

        print("[REMOTO] Aplicando limpeza GFS em backups remotos...")
        remote_dir = Config.GDRIVE_BACKUP_DIR
        if remote_dir.exists():
            result = cleanup_directory(remote_dir, policy, dry_run=args.dry_run)
            print(f"[REMOTO] Total: {result['total']}, Mantidos: {result['kept']}, Deletados: {result['deleted']}")
        else:
            print(f"[AVISO] Diretório remoto não acessível: {remote_dir}")
        print()

    # Atualizar status (P1.5)
    try:
        if not args.dry_run:
            # Verificar se houve algum erro durante cleanup
            # (por enquanto assumimos sucesso se chegou aqui)
            if STATUS_AVAILABLE:
                from datetime import datetime
                update_backup_status(last_cleanup_ok_at=datetime.now().isoformat())
    except Exception as status_error:
        print(f"[AVISO] Erro ao atualizar status de cleanup: {status_error}")
        if STATUS_AVAILABLE:
            try:
                update_backup_status(last_cleanup_error=str(status_error))
            except Exception:
                pass

    print("=" * 60)
    if args.dry_run:
        print("[DRY-RUN] Simulação concluída")
    else:
        print("[OK] Limpeza concluída")
    print("=" * 60)


if __name__ == '__main__':
    main()

