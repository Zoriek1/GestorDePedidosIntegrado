# -*- coding: utf-8 -*-
"""
Sistema de Backup Automático do Banco de Dados
Faz backup do database.db com timestamp e gerencia retenção
"""
import os
import sys
import zipfile
from datetime import datetime, timedelta
from pathlib import Path

# Tentar importar o logger de auditoria se disponível
try:
    # Adicionar o diretório app ao path
    backend_dir = Path(__file__).parent.parent.parent
    app_utils_dir = backend_dir / "app" / "utils"
    sys.path.insert(0, str(app_utils_dir))

    from backup_helper import get_audit_logger
    from encryption import encrypt_file  # noqa: F401
    from gdrive_backup import GoogleDriveBackup, GoogleDriveBackupError  # noqa: F401

    from app.config import Config  # noqa: F401

    AUDIT_LOGGER_AVAILABLE = True
except ImportError:
    AUDIT_LOGGER_AVAILABLE = False


def _get_basic_logger():
    """Retorna logger básico quando audit não disponível"""
    import logging

    logger = logging.getLogger("backup_basic")
    if not logger.handlers:
        backend_dir = Path(__file__).parent.parent.parent
        logs_dir = backend_dir / "instance" / "logs"
        logs_dir.mkdir(parents=True, exist_ok=True)
        handler = logging.FileHandler(logs_dir / "backup_audit.log", encoding="utf-8", mode="a")
        handler.setFormatter(
            logging.Formatter(
                "%(asctime)s | %(levelname)s | %(message)s", datefmt="%Y-%m-%d %H:%M:%S"
            )
        )
        logger.addHandler(handler)
        logger.setLevel(logging.INFO)
    return logger


# Importar módulos P1 (com fallback silencioso)
STATUS_AVAILABLE = False
REMOTE_VERIFY_AVAILABLE = False
DRIVE_UTILS_AVAILABLE = False

try:
    from scripts.backup.status import update_backup_status

    STATUS_AVAILABLE = True
except ImportError:
    pass

try:
    from scripts.backup.remote_verify import copy_and_verify_remote  # noqa: F401

    REMOTE_VERIFY_AVAILABLE = True
except ImportError:
    pass

try:
    from scripts.backup.drive_utils import check_drive_separation

    DRIVE_UTILS_AVAILABLE = True
except ImportError:
    pass


class BackupManager:
    """Gerenciador de backups do banco de dados"""

    def __init__(self, db_path=None, backup_dir=None, retention_days=30):
        """
        Inicializa o gerenciador de backups

        Args:
            db_path: Caminho para o database.db (padrão: backend/database.db)
            backup_dir: Diretório para salvar backups (padrão: backend/backups)
            retention_days: Número de dias para manter backups
        """
        # Definir diretórios
        self.backend_dir = Path(__file__).parent.parent.parent

        # Adicionar backend_dir ao path para importar app.config
        if str(self.backend_dir) not in sys.path:
            sys.path.insert(0, str(self.backend_dir))

        try:
            from app.config import Config

            default_db_path = Config.DATABASE_PATH
            default_backup_dir = Config.INSTANCE_DIR / "backups"
            self.database_uri = Config.SQLALCHEMY_DATABASE_URI
        except ImportError:
            default_db_path = self.backend_dir / "instance" / "database.db"
            default_backup_dir = self.backend_dir / "instance" / "backups"
            self.database_uri = os.environ.get("DATABASE_URL", "")

        self._is_postgres = self.database_uri and "postgresql" in self.database_uri.split(":")[0]

        if db_path and not self._is_postgres:
            self.db_path = Path(db_path)
        elif self._is_postgres:
            self.db_path = None
        else:
            self.db_path = default_db_path

        if backup_dir:
            self.backup_dir = Path(backup_dir)
        else:
            self.backup_dir = default_backup_dir

        self.retention_days = retention_days

        # Criar diretório de backups se não existir
        self.backup_dir.mkdir(exist_ok=True)

    def _get_gdrive_backup_dir(self, gdrive_dir=None):
        """
        Obtém o diretório do Google Drive Desktop para backups encriptados.

        Args:
            gdrive_dir: Caminho customizado (opcional)

        Returns:
            Path do diretório do Google Drive Desktop
        """
        if gdrive_dir:
            return Path(gdrive_dir)

        try:
            from app.config import Config

            return Config.GDRIVE_BACKUP_DIR
        except ImportError:
            # Fallback se não conseguir importar Config
            _HOME_DIR = Path(os.path.expanduser("~"))
            return (
                _HOME_DIR
                / "Meu Drive"
                / "Plante Uma Flor Confidential"
                / "Database - Pedidos Gestor"
            )

    def create_backup(self, compress=True, reason="manual"):
        """
        Cria um backup do banco de dados.
        SQLite: sqlite3.Connection.backup() + PRAGMA integrity_check
        PostgreSQL: pg_dump (subprocess)

        Args:
            compress: Se True, comprime o backup (.zip para SQLite, .gz para PostgreSQL)

        Returns:
            Path do arquivo de backup criado ou None em caso de erro
        """
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

        if self._is_postgres:
            return self._create_backup_postgres(timestamp, compress, reason)
        return self._create_backup_sqlite(timestamp, compress, reason)

    def _create_backup_postgres(self, timestamp, compress, reason):
        """Backup PostgreSQL via pg_dump"""
        import subprocess

        backup_name = f"database_{timestamp}.sql"
        backup_path = self.backup_dir / backup_name

        try:
            print(f"[BACKUP] Criando backup PostgreSQL: {backup_name}")
            result = subprocess.run(
                ["pg_dump", self.database_uri, "--file", str(backup_path)],
                capture_output=True,
                text=True,
                timeout=300,
            )
            if result.returncode != 0:
                print(f"[ERRO] pg_dump falhou: {result.stderr}")
                if backup_path.exists():
                    backup_path.unlink()
                return None

            abs_path = backup_path.resolve()
            size_mb = abs_path.stat().st_size / (1024 * 1024)
            print(f"[BACKUP] Backup criado: {abs_path} ({size_mb:.2f} MB)")

            if compress:
                import gzip

                gz_path = self.backup_dir / f"database_{timestamp}.sql.gz"
                with open(backup_path, "rb") as f_in:
                    with gzip.open(gz_path, "wb") as f_out:
                        f_out.writelines(f_in)
                backup_path.unlink()
                backup_path = gz_path
                size_mb = backup_path.stat().st_size / (1024 * 1024)
                print(f"[BACKUP] Backup compactado: {backup_path} ({size_mb:.2f} MB)")

            return self._finalize_backup(backup_path, reason, size_mb)
        except FileNotFoundError:
            print("[ERRO] pg_dump não encontrado. Instale postgresql-client.")
            return None
        except Exception as e:
            print(f"[ERRO] Erro ao criar backup PostgreSQL: {e}")
            if backup_path.exists():
                try:
                    backup_path.unlink()
                except Exception:
                    pass
            return None

    def _finalize_backup(self, backup_path, reason, size_mb):
        """Registra backup no audit log, status e cópia secundária"""
        try:
            if AUDIT_LOGGER_AVAILABLE:
                get_audit_logger().log_backup_created(backup_path, reason=reason, size_mb=size_mb)
            else:
                _get_basic_logger().info(
                    f"BACKUP CRIADO | Arquivo: {backup_path.name} | "
                    f"Motivo: {reason} | Tamanho: {size_mb:.2f} MB"
                )
        except Exception as log_error:
            print(f"[AVISO] Erro ao registrar no log de auditoria: {log_error}")

        if STATUS_AVAILABLE:
            try:
                update_backup_status(last_backup_ok_at=datetime.now().isoformat())
                backups_count = len(list(self.backup_dir.glob("database_*.*")))
                update_backup_status(backups_local_count=backups_count)
            except Exception as status_error:
                print(f"[AVISO] Erro ao atualizar status de backup: {status_error}")

        try:
            from app.config import Config as BackupConfig

            if BackupConfig.BACKUP_SECONDARY_DIR:
                try:
                    import shutil

                    secondary_dir = Path(BackupConfig.BACKUP_SECONDARY_DIR)
                    secondary_dir.mkdir(parents=True, exist_ok=True)
                    secondary_backup = secondary_dir / backup_path.name
                    shutil.copy2(backup_path, secondary_backup)
                    if secondary_backup.exists():
                        if backup_path.stat().st_size == secondary_backup.stat().st_size:
                            print(
                                f"[BACKUP] Cópia para diretório secundário: OK ({secondary_backup})"
                            )
                        else:
                            print("[AVISO] Tamanho diferente no diretório secundário")
                    else:
                        print("[AVISO] Cópia para diretório secundário falhou")
                except Exception as secondary_error:
                    print(f"[AVISO] Erro ao copiar para diretório secundário: {secondary_error}")

            if DRIVE_UTILS_AVAILABLE and BackupConfig.BACKUP_SECONDARY_DIR and self.db_path:
                try:
                    warnings = check_drive_separation(
                        db_path=self.db_path,
                        backup_dir=self.backup_dir,
                        secondary_dir=Path(BackupConfig.BACKUP_SECONDARY_DIR),
                    )
                    for warning in warnings:
                        print(f"[AVISO] {warning}")
                except Exception as drive_check_error:
                    print(f"[AVISO] Erro ao verificar separação de drives: {drive_check_error}")
        except ImportError:
            pass

        return backup_path

    def _create_backup_sqlite(self, timestamp, compress, reason):
        """Backup SQLite via sqlite3.Connection.backup()"""
        import sqlite3

        if not self.db_path or not self.db_path.exists():
            print(f"[ERRO] Banco de dados não encontrado: {self.db_path}")
            return None

        backup_name = f"database_{timestamp}.db"
        backup_path = self.backup_dir / backup_name

        try:
            print(f"[BACKUP] Criando backup: {backup_name}")
            with sqlite3.connect(str(self.db_path)) as source_conn:
                with sqlite3.connect(str(backup_path)) as backup_conn:
                    source_conn.backup(backup_conn)

            with sqlite3.connect(str(backup_path)) as check_conn:
                cursor = check_conn.cursor()
                cursor.execute("PRAGMA integrity_check;")
                result = cursor.fetchone()
                if result[0] != "ok":
                    print(f"[ERRO] Integrity check falhou: {result[0]}")
                    backup_path.unlink()
                    return None

            abs_path = backup_path.resolve()
            size_mb = abs_path.stat().st_size / (1024 * 1024)
            print(f"[BACKUP] Backup criado: {abs_path} ({size_mb:.2f} MB)")

            if compress:
                try:
                    zip_path = self.backup_dir / f"database_{timestamp}.zip"
                    print(f"[BACKUP] Comprimindo: {zip_path.name}")
                    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zipf:
                        zipf.write(backup_path, backup_name)
                    backup_path.unlink()
                    backup_path = zip_path
                    size_mb = backup_path.stat().st_size / (1024 * 1024)
                    print(f"[BACKUP] Backup compactado: {backup_path} ({size_mb:.2f} MB)")
                except Exception as exc:
                    print(f"[AVISO] Falha ao comprimir; mantendo .db: {exc}")

            return self._finalize_backup(backup_path, reason, size_mb)

        except Exception as e:
            error_msg = str(e)
            print(f"[ERRO] Erro ao criar backup: {error_msg}")

            # Registrar falha no log de auditoria
            try:
                if AUDIT_LOGGER_AVAILABLE:
                    get_audit_logger().log_backup_failed(reason, error_msg)
                else:
                    _get_basic_logger().error(
                        f"BACKUP FALHOU | Motivo: {reason} | Erro: {error_msg}"
                    )
            except Exception as log_error:
                print(f"[AVISO] Erro ao registrar falha no log: {log_error}")

            # Atualizar status (P1.5)
            if STATUS_AVAILABLE:
                try:
                    update_backup_status(last_backup_error=error_msg)
                except Exception as status_error:
                    print(f"[AVISO] Erro ao atualizar status de backup: {status_error}")

            # Tentar limpar arquivo de backup parcial
            if backup_path.exists():
                try:
                    backup_path.unlink()
                except Exception:
                    pass
            return None

    def create_encrypted_backup(
        self,
        compress=True,
        upload_drive=False,
        keep_remote=90,
        folder_id=None,
        remove_local_after_upload=True,
        reason="automatic",
        gdrive_dir=None,
    ):
        """
        Cria backup não encriptado localmente, encripta cópia e salva no Google Drive Desktop.

        Fluxo:
        1. Cria backup não encriptado localmente (mantém)
        2. Encripta cópia do backup
        3. Salva backup encriptado no Google Drive Desktop
        4. Remove backup encriptado local (após copiar para Drive)
        """
        try:
            from encryption import (
                encrypt_file,
            )
        except ImportError as exc:
            print(f"[ERRO] Não foi possível importar encryption.encrypt_file: {exc}")
            return None

        # 1. Criar backup não encriptado localmente (mantém este)
        backup_path = self.create_backup(compress=compress, reason=reason)
        if not backup_path:
            return None

        print(f"[BACKUP] Backup local não encriptado mantido: {backup_path.name}")

        # 2. Encriptar cópia do backup
        try:
            # Obter diretório do Google Drive Desktop
            gdrive_backup_dir = self._get_gdrive_backup_dir(gdrive_dir)
            gdrive_backup_dir.mkdir(parents=True, exist_ok=True)

            # Definir destino do arquivo encriptado no Google Drive Desktop
            encrypted_filename = backup_path.name + ".enc"
            encrypted_path = gdrive_backup_dir / encrypted_filename

            # Encriptar e salvar diretamente no Google Drive Desktop
            encrypted_path = encrypt_file(backup_path, dst=encrypted_path)
            print(f"[BACKUP] Arquivo encriptado salvo no Google Drive Desktop: {encrypted_path}")

            # Verificação remota (P1.3) - verificar que arquivo foi recebido
            remote_ok = False
            if encrypted_path.exists():
                # Verificação básica: arquivo existe e tem tamanho > 0
                encrypted_size = encrypted_path.stat().st_size
                if encrypted_size > 0:
                    remote_ok = True
                    print(
                        f"[BACKUP] Verificação remota: OK (arquivo existe, {encrypted_size / (1024*1024):.2f} MB)"
                    )

                    # Stability check: re-verificar após alguns segundos
                    try:
                        import time

                        time.sleep(3)  # Esperar 3 segundos
                        encrypted_size_after = encrypted_path.stat().st_size
                        if encrypted_size_after != encrypted_size:
                            print(
                                "[AVISO] Tamanho do arquivo mudou após stability check - arquivo ainda sendo escrito?"
                            )
                            remote_ok = False
                    except Exception as stability_error:
                        print(f"[AVISO] Erro no stability check: {stability_error}")

                    if remote_ok:
                        # Atualizar status (P1.5)
                        if STATUS_AVAILABLE:
                            try:
                                # datetime já foi importado no topo do arquivo
                                update_backup_status(last_remote_ok_at=datetime.now().isoformat())
                                # Contar backups remotos
                                remote_count = len(list(gdrive_backup_dir.glob("*.enc")))
                                update_backup_status(backups_remote_count=remote_count)
                            except Exception as status_error:
                                print(f"[AVISO] Erro ao atualizar status remoto: {status_error}")
                else:
                    print("[AVISO] Arquivo remoto existe mas está vazio")
                    if STATUS_AVAILABLE:
                        try:
                            update_backup_status(last_remote_error="Arquivo remoto vazio")
                        except Exception:
                            pass
            else:
                print("[AVISO] Arquivo remoto não encontrado após encriptação")
                if STATUS_AVAILABLE:
                    try:
                        update_backup_status(last_remote_error="Arquivo não encontrado no destino")
                    except Exception:
                        pass

            # 3. Remover backup encriptado local (já está no Drive, será sincronizado)
            # O arquivo encriptado já foi salvo diretamente no Drive, não precisa remover local
            # pois não foi criado localmente primeiro

        except Exception as exc:
            print(f"[ERRO] Falha ao encriptar e salvar no Google Drive Desktop: {exc}")
            import traceback

            traceback.print_exc()
            # Atualizar status remoto (P1.5)
            if STATUS_AVAILABLE:
                try:
                    update_backup_status(last_remote_error=str(exc))
                except Exception:
                    pass
            return backup_path  # Retorna backup local não encriptado

        # Upload via API (opcional, mantido para compatibilidade)
        if upload_drive:
            try:
                try:
                    from gdrive_backup import (  # noqa: F401
                        GoogleDriveBackup,
                        GoogleDriveBackupError,
                    )
                except ImportError as exc:
                    print(f"[AVISO] Upload via API não disponível: {exc}")
                    print(
                        f"[INFO] Backup encriptado já está no Google Drive Desktop: {encrypted_path}"
                    )
                    return backup_path

                gdrive = GoogleDriveBackup(folder_id=folder_id)
                file_id = gdrive.upload_backup(encrypted_path)
                print(f"[GDRIVE] Upload via API concluído. File ID: {file_id}")

                # Limpeza remota
                if keep_remote and keep_remote > 0:
                    removed = gdrive.delete_old_backups(keep_count=keep_remote)
                    if removed:
                        print(f"[GDRIVE] Backups antigos removidos: {removed}")

                # Remover local se solicitado
                if remove_local_after_upload:
                    try:
                        encrypted_path.unlink(missing_ok=True)
                        print("[BACKUP] Backup encriptado local removido após upload via API.")
                    except Exception:
                        pass
            except Exception as exc:
                print(f"[AVISO] Upload via API falhou: {exc}")
                print(f"[INFO] Backup encriptado já está no Google Drive Desktop: {encrypted_path}")

        # Retorna o backup local não encriptado (mantido)
        return backup_path

    def cleanup_old_backups(self):
        """
        Remove backups antigos baseado no retention_days

        Returns:
            Número de backups removidos
        """
        if self.retention_days <= 0:
            print("[INFO] Retenção ilimitada - nenhum backup será removido")
            return 0

        cutoff_date = datetime.now() - timedelta(days=self.retention_days)
        removed_count = 0

        print(f"[LIMPEZA] Removendo backups anteriores a {cutoff_date.strftime('%Y-%m-%d')}")

        patterns = [
            "database_*.db",
            "database_*.zip",
            "database_*.sql",
            "database_*.sql.gz",
            "database_*.enc",
            "database_*.zip.enc",
        ]
        for pattern in patterns:
            for backup_file in self.backup_dir.glob(pattern):
                try:
                    # Obter data de modificação do arquivo
                    file_time = datetime.fromtimestamp(backup_file.stat().st_mtime)

                    if file_time < cutoff_date:
                        print(f"[LIMPEZA] Removendo: {backup_file.name}")
                        backup_file.unlink()
                        removed_count += 1

                except Exception as e:
                    print(f"[AVISO] Erro ao processar {backup_file.name}: {e}")

        if removed_count > 0:
            print(f"[LIMPEZA] {removed_count} backup(s) antigo(s) removido(s)")
        else:
            print("[LIMPEZA] Nenhum backup antigo para remover")

        return removed_count

    def list_backups(self):
        """
        Lista todos os backups disponíveis

        Returns:
            Lista de tuplas (path, size_mb, date)
        """
        backups = []

        for backup_file in sorted(self.backup_dir.glob("database_*.*"), reverse=True):
            try:
                size_mb = backup_file.stat().st_size / (1024 * 1024)
                mod_time = datetime.fromtimestamp(backup_file.stat().st_mtime)
                backups.append((backup_file, size_mb, mod_time))
            except Exception as e:
                print(f"[AVISO] Erro ao processar {backup_file.name}: {e}")

        return backups

    def get_backup_stats(self):
        """
        Retorna estatísticas dos backups

        Returns:
            Dicionário com estatísticas
        """
        backups = self.list_backups()

        if not backups:
            return {"count": 0, "total_size_mb": 0, "oldest": None, "newest": None}

        total_size = sum(b[1] for b in backups)

        return {
            "count": len(backups),
            "total_size_mb": total_size,
            "oldest": backups[-1][2] if backups else None,
            "newest": backups[0][2] if backups else None,
        }


def main():
    """Função principal para executar backup via linha de comando"""
    import argparse

    parser = argparse.ArgumentParser(description="Sistema de Backup do Banco de Dados")
    parser.add_argument("--no-compress", action="store_true", help="Não comprimir backup")
    parser.add_argument("--no-cleanup", action="store_true", help="Não remover backups antigos")
    parser.add_argument(
        "--retention", type=int, default=30, help="Dias de retenção local (padrão: 30)"
    )
    parser.add_argument("--list", action="store_true", help="Listar backups existentes")
    parser.add_argument("--stats", action="store_true", help="Mostrar estatísticas de backups")
    parser.add_argument(
        "--upload-drive",
        action="store_true",
        help="Fazer upload para Google Drive via API",
    )
    parser.add_argument(
        "--keep-remote",
        type=int,
        default=90,
        help="Qtd de backups para manter no Drive (padrão: 90)",
    )
    parser.add_argument(
        "--keep-local",
        action="store_true",
        help="Manter arquivo encriptado local mesmo após upload",
    )
    parser.add_argument(
        "--no-encrypt", action="store_true", help="Não encriptar (apenas backup local)"
    )
    parser.add_argument(
        "--folder-id",
        type=str,
        help="ID da pasta no Google Drive (opcional, para upload via API)",
    )
    parser.add_argument(
        "--gdrive-dir",
        type=str,
        help="Caminho do diretório do Google Drive Desktop para backups encriptados (padrão: Config.GDRIVE_BACKUP_DIR)",
    )

    args = parser.parse_args()

    # Criar gerenciador de backups
    backup_mgr = BackupManager(retention_days=args.retention)

    print("\n" + "=" * 60)
    print("SISTEMA DE BACKUP - Gestor de Pedidos")
    print("=" * 60)

    # Modo listar
    if args.list:
        backups = backup_mgr.list_backups()
        print(f"\nBackups disponíveis: {len(backups)}")
        print("-" * 60)
        for backup_path, size_mb, mod_time in backups:
            print(f"  {backup_path.name}")
            print(f"    Tamanho: {size_mb:.2f} MB")
            print(f"    Data: {mod_time.strftime('%Y-%m-%d %H:%M:%S')}")
            print()
        return

    # Modo estatísticas
    if args.stats:
        stats = backup_mgr.get_backup_stats()
        print("\nEstatísticas de Backups:")
        print("-" * 60)
        print(f"  Total de backups: {stats['count']}")
        print(f"  Tamanho total: {stats['total_size_mb']:.2f} MB")
        if stats["oldest"]:
            print(f"  Mais antigo: {stats['oldest'].strftime('%Y-%m-%d %H:%M:%S')}")
        if stats["newest"]:
            print(f"  Mais recente: {stats['newest'].strftime('%Y-%m-%d %H:%M:%S')}")
        print()
        return

    # Criar backup (com encriptação e Drive se solicitado)
    if args.upload_drive or not args.no_encrypt:
        backup_path = backup_mgr.create_encrypted_backup(
            compress=not args.no_compress,
            upload_drive=args.upload_drive,
            keep_remote=args.keep_remote,
            folder_id=args.folder_id,
            remove_local_after_upload=not args.keep_local,
            reason="automatic",
            gdrive_dir=args.gdrive_dir,
        )
    else:
        backup_path = backup_mgr.create_backup(compress=not args.no_compress, reason="manual")

    if not backup_path:
        print("\n[ERRO] Falha ao criar backup!")
        print("=" * 60 + "\n")
        sys.exit(1)

    # Limpar backups antigos
    if not args.no_cleanup:
        print()
        backup_mgr.cleanup_old_backups()

    # Mostrar estatísticas finais
    print()
    stats = backup_mgr.get_backup_stats()
    print(f"[INFO] Total de backups: {stats['count']} ({stats['total_size_mb']:.2f} MB)")

    print("=" * 60 + "\n")
    print("[OK] Backup concluído com sucesso!")
    print()


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n[INFO] Operação cancelada pelo usuário.")
        sys.exit(1)
    except Exception as e:
        print(f"\n[ERRO] Erro inesperado: {e}")
        import traceback

        traceback.print_exc()
        sys.exit(1)
