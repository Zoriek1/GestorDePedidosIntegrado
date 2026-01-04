# -*- coding: utf-8 -*-
"""
Script para migrar backups do diretório antigo (backups/) para o novo (instance/backups/)
e criar um backup atual do banco de dados
"""
import shutil
import sys
from datetime import datetime
from pathlib import Path

# Adicionar backend ao path
backend_dir = Path(__file__).parent.parent.parent
sys.path.insert(0, str(backend_dir))

try:
    from scripts.backup.backup import BackupManager  # noqa: F401
    BACKUP_MANAGER_AVAILABLE = True
except ImportError:
    BACKUP_MANAGER_AVAILABLE = False
    print("[AVISO] BackupManager não disponível, usando método manual")


def migrate_backups():
    """Migra backups do diretório antigo para o novo"""
    old_backup_dir = backend_dir / 'backups'
    new_backup_dir = backend_dir / 'instance' / 'backups'

    # Garantir que o diretório novo existe
    new_backup_dir.mkdir(parents=True, exist_ok=True)

    print("=" * 60)
    print("MIGRACAO DE BACKUPS")
    print("=" * 60)
    print()

    if not old_backup_dir.exists():
        print(f"[INFO] Diretorio de backups antigo nao existe: {old_backup_dir}")
        print("[INFO] Nenhum backup para migrar")
        return []

    # Listar arquivos no diretório antigo
    try:
        backup_files = []
        # Tentar múltiplos métodos para listar arquivos
        try:
            # Método 1: iterdir
            for item in old_backup_dir.iterdir():
                if item.is_file():
                    backup_files.append(item)
        except Exception:
            # Método 2: glob
            backup_files = list(old_backup_dir.glob('*'))
            backup_files = [f for f in backup_files if f.is_file()]

        if not backup_files:
            # Método 3: os.listdir
            import os
            try:
                for filename in os.listdir(str(old_backup_dir)):
                    filepath = old_backup_dir / filename
                    if filepath.is_file():
                        backup_files.append(filepath)
            except Exception:
                pass
    except Exception as e:
        print(f"[ERRO] Erro ao listar arquivos: {e}")
        return []

    if not backup_files:
        print(f"[INFO] Nenhum arquivo de backup encontrado em {old_backup_dir}")
        return []

    print(f"[1/2] Encontrados {len(backup_files)} arquivos de backup no diretório antigo")
    print()

    migrated_files = []
    skipped_files = []

    for backup_file in backup_files:
        dest_path = new_backup_dir / backup_file.name

        # Verificar se já existe no destino
        if dest_path.exists():
            # Comparar tamanhos e datas
            if backup_file.stat().st_size == dest_path.stat().st_size:
                print(f"[INFO] {backup_file.name} já existe no destino (mesmo tamanho), pulando...")
                skipped_files.append(backup_file.name)
                continue
            else:
                # Renomear arquivo existente com timestamp
                timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
                new_name = f"{dest_path.stem}_conflict_{timestamp}{dest_path.suffix}"
                dest_path.rename(new_backup_dir / new_name)
                print(f"[INFO] Arquivo existente renomeado: {new_name}")

        try:
            shutil.copy2(backup_file, dest_path)
            migrated_files.append(backup_file.name)
            size_mb = backup_file.stat().st_size / (1024 * 1024)
            print(f"[OK] Migrado: {backup_file.name} ({size_mb:.2f} MB)")
        except Exception as e:
            print(f"[ERRO] Falha ao migrar {backup_file.name}: {e}")

    print()
    print("[OK] Migração concluída:")
    print(f"  - Migrados: {len(migrated_files)}")
    print(f"  - Pulados: {len(skipped_files)}")
    print()

    return migrated_files


def create_current_backup():
    """Cria um backup atual do banco de dados"""
    print("[2/2] Criando backup atual do banco de dados...")
    print()

    # Usar método manual para evitar problemas de encoding
    try:
        from app.config import Config
        db_path = Config.DATABASE_PATH
        backup_dir = Config.INSTANCE_DIR / 'backups'

        if not db_path.exists():
            print(f"[ERRO] Banco de dados nao encontrado: {db_path}")
            return None

        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        backup_name = f"database_{timestamp}.db"
        backup_path = backup_dir / backup_name

        shutil.copy2(db_path, backup_path)
        size_mb = backup_path.stat().st_size / (1024 * 1024)
        print(f"[OK] Backup criado: {backup_path.name} ({size_mb:.2f} MB)")
        return backup_path
    except Exception as e:
        print(f"[ERRO] Falha ao criar backup: {e}")
        import traceback
        traceback.print_exc()
        return None


def main():
    """Função principal"""
    try:
        # Migrar backups antigos
        migrated = migrate_backups()

        # Criar backup atual
        current_backup = create_current_backup()

        print()
        print("=" * 60)
        print("MIGRAÇÃO DE BACKUPS CONCLUÍDA")
        print("=" * 60)
        print()
        print(f"Backups migrados: {len(migrated)}")
        if current_backup:
            print(f"Backup atual criado: {current_backup.name}")
        print()
        print("Todos os backups agora estão em: instance/backups/")

        return 0
    except Exception as e:
        print(f"\n[ERRO] Falha na migração de backups: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == '__main__':
    sys.exit(main())

