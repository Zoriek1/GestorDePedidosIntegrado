"""
Migra o database.db do local antigo (backend/instance/database.db)
para o novo local externo: %USERPROFILE%/var/lib/database/database.db

Uso:
    python migrar_database_path.py
    python migrar_database_path.py --force      # sobrescreve destino
    python migrar_database_path.py --no-backup  # não cria cópia do antigo
"""
import argparse
import shutil
import sqlite3
import sys
from datetime import datetime
from pathlib import Path

# Garantir que o backend esteja no sys.path quando executado de subpasta
CURRENT_DIR = Path(__file__).resolve().parent
BACKEND_DIR = CURRENT_DIR.parent.parent  # backend/
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from app.config import Config  # noqa: E402


def integrity_check(db_path: Path) -> bool:
    """Executa PRAGMA integrity_check para validar o arquivo SQLite."""
    try:
        with sqlite3.connect(str(db_path)) as conn:
            row = conn.execute("PRAGMA integrity_check;").fetchone()
            return bool(row) and row[0] == "ok"
    except Exception:
        return False


def migrate(force: bool, backup_old: bool) -> None:
    old_path = Config.BASE_DIR / "instance" / "database.db"
    new_path = Config.DATABASE_PATH

    print(f"[INFO] Origem (antigo): {old_path}")
    print(f"[INFO] Destino (novo):  {new_path}")

    if not old_path.exists():
        print("[ERRO] Banco antigo não encontrado. Nada a migrar.")
        return

    # Criar diretório destino
    new_path.parent.mkdir(parents=True, exist_ok=True)

    # Se já existe destino e não for force, abortar
    if new_path.exists() and not force:
        print("[AVISO] Destino já existe. Use --force para sobrescrever.")
        return

    # Opcionalmente criar backup do antigo
    backup_path = None
    if backup_old:
        backup_dir = Config.INSTANCE_DIR / "backups"
        backup_dir.mkdir(parents=True, exist_ok=True)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_path = backup_dir / f"database_antigo_{timestamp}.db"
        shutil.copy2(old_path, backup_path)
        print(f"[OK] Backup do antigo criado em: {backup_path}")

    # Copiar para o novo local
    shutil.copy2(old_path, new_path)
    print(f"[OK] Copiado para novo local: {new_path}")

    # Validar integridade no novo local
    if integrity_check(new_path):
        size_mb = new_path.stat().st_size / (1024 * 1024)
        print(f"[OK] Integridade verificada. Tamanho: {size_mb:.2f} MB")
    else:
        print("[ERRO] Integrity check falhou no arquivo migrado! Mantendo backup.")
        return

    # Se force, opcionalmente sobrescreveu; mantemos o antigo no lugar
    print("\nMigração concluída.")
    if backup_path:
        print(f"Cópia de segurança do antigo: {backup_path}")
    print(f"Novo database em uso: {new_path}")


def main():
    parser = argparse.ArgumentParser(description="Migrar database.db para novo local externo.")
    parser.add_argument("--force", action="store_true", help="Sobrescreve o destino se existir.")
    parser.add_argument(
        "--no-backup",
        dest="backup_old",
        action="store_false",
        help="Não cria backup do banco antigo.",
    )
    args = parser.parse_args()

    migrate(force=args.force, backup_old=args.backup_old)


if __name__ == "__main__":
    main()

