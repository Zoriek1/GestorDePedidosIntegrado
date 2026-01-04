# -*- coding: utf-8 -*-
"""
Sistema de Restauração de Backups
Restaura o banco de dados a partir de um backup
"""
import shutil
import sys
import zipfile
from datetime import datetime
from pathlib import Path

# Tentar importar o logger de auditoria se disponível
try:
    # Adicionar o diretório app ao path
    backend_dir = Path(__file__).parent.parent.parent
    app_utils_dir = backend_dir / 'app' / 'utils'
    sys.path.insert(0, str(app_utils_dir))

    from backup_helper import get_audit_logger
    AUDIT_LOGGER_AVAILABLE = True
except ImportError:
    AUDIT_LOGGER_AVAILABLE = False

# Adicionar scripts/backup ao path para importar validate_db
scripts_backup_dir = backend_dir / 'scripts' / 'backup'
if str(scripts_backup_dir) not in sys.path:
    sys.path.insert(0, str(scripts_backup_dir))

try:
    from validate_db import validate_restored_db
    VALIDATION_AVAILABLE = True
except ImportError:
    VALIDATION_AVAILABLE = False
    # Criar logger básico se não conseguir importar
    import logging
    logs_dir = backend_dir / 'instance' / 'logs'
    logs_dir.mkdir(parents=True, exist_ok=True)
    basic_logger = logging.getLogger('restore_basic')
    basic_logger.setLevel(logging.INFO)
    if not basic_logger.handlers:
        file_handler = logging.FileHandler(
            logs_dir / 'backup_audit.log',
            encoding='utf-8',
            mode='a'
        )
        file_handler.setFormatter(
            logging.Formatter('%(asctime)s | %(levelname)s | %(message)s', datefmt='%Y-%m-%d %H:%M:%S')
        )
        basic_logger.addHandler(file_handler)

class RestoreManager:
    """Gerenciador de restauração de backups"""

    def __init__(self, db_path=None, backup_dir=None):
        """
        Inicializa o gerenciador de restauração

        Args:
            db_path: Caminho para o database.db (padrão: backend/database.db)
            backup_dir: Diretório com os backups (padrão: backend/backups)
        """
        self.backend_dir = Path(__file__).parent.parent.parent

        # Adicionar backend_dir ao path para importar app.config
        if str(self.backend_dir) not in sys.path:
            sys.path.insert(0, str(self.backend_dir))

        try:
            from app.config import Config
            default_db_path = Config.DATABASE_PATH
            default_backup_dir = Config.INSTANCE_DIR / 'backups'
        except ImportError:
            default_db_path = self.backend_dir / 'instance' / 'database.db'
            default_backup_dir = self.backend_dir / 'instance' / 'backups'

        if db_path:
            self.db_path = Path(db_path)
        else:
            self.db_path = default_db_path

        if backup_dir:
            self.backup_dir = Path(backup_dir)
        else:
            self.backup_dir = default_backup_dir

    def list_backups(self):
        """
        Lista todos os backups disponíveis ordenados por data (mais recente primeiro)

        Returns:
            Lista de tuplas (index, path, size_mb, date)
        """
        if not self.backup_dir.exists():
            return []

        backups = []
        backup_files = sorted(
            self.backup_dir.glob('database_*.*'),
            key=lambda p: p.stat().st_mtime,
            reverse=True
        )

        for idx, backup_file in enumerate(backup_files, 1):
            try:
                size_mb = backup_file.stat().st_size / (1024 * 1024)
                mod_time = datetime.fromtimestamp(backup_file.stat().st_mtime)
                backups.append((idx, backup_file, size_mb, mod_time))
            except Exception as e:
                print(f"[AVISO] Erro ao processar {backup_file.name}: {e}")

        return backups

    def create_backup_before_restore(self):
        """
        Cria um backup do banco atual antes de restaurar

        Returns:
            Path do backup criado ou None
        """
        if not self.db_path.exists():
            print("[INFO] Banco de dados atual não existe, pulando backup preventivo")
            return None

        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        backup_name = f"database_pre_restore_{timestamp}.db"
        backup_path = self.backup_dir / backup_name

        try:
            print(f"[BACKUP] Criando backup preventivo: {backup_name}")
            shutil.copy2(self.db_path, backup_path)
            print("[BACKUP] ✓ Backup preventivo criado")
            return backup_path
        except Exception as e:
            print(f"[ERRO] Erro ao criar backup preventivo: {e}")
            return None

    def restore_backup(self, backup_path, create_backup_first=True):
        """
        Restaura o banco de dados a partir de um backup

        Args:
            backup_path: Caminho do arquivo de backup
            create_backup_first: Se True, cria backup do banco atual primeiro

        Returns:
            True se restaurado com sucesso, False caso contrário
        """
        backup_path = Path(backup_path)

        # Verificar se o arquivo de backup existe
        if not backup_path.exists():
            print(f"[ERRO] Arquivo de backup não encontrado: {backup_path}")
            return False

        # Criar backup preventivo
        preventive_backup = None
        if create_backup_first and self.db_path.exists():
            preventive_backup = self.create_backup_before_restore()
            if not preventive_backup:
                resposta = input("\n[AVISO] Não foi possível criar backup preventivo. Continuar? (s/n): ")
                if resposta.lower() != 's':
                    print("[INFO] Restauração cancelada.")
                    return False

        try:
            # Se o backup é um arquivo .zip, extrair primeiro
            if backup_path.suffix == '.zip':
                print(f"[RESTORE] Extraindo arquivo comprimido: {backup_path.name}")

                with zipfile.ZipFile(backup_path, 'r') as zipf:
                    # Listar arquivos no zip
                    files = zipf.namelist()
                    db_files = [f for f in files if f.endswith('.db')]

                    if not db_files:
                        print("[ERRO] Nenhum arquivo .db encontrado no backup comprimido")
                        return False

                    # Extrair para arquivo temporário
                    temp_dir = self.backup_dir / 'temp_restore'
                    temp_dir.mkdir(exist_ok=True)

                    db_file = db_files[0]
                    zipf.extract(db_file, temp_dir)

                    extracted_path = temp_dir / db_file

                    # Copiar para o local do banco de dados
                    print(f"[RESTORE] Restaurando: {self.db_path.name}")
                    shutil.copy2(extracted_path, self.db_path)

                    # Limpar arquivo temporário
                    extracted_path.unlink()
                    temp_dir.rmdir()

            else:
                # Backup não comprimido, copiar diretamente
                print(f"[RESTORE] Restaurando: {backup_path.name} → {self.db_path.name}")
                shutil.copy2(backup_path, self.db_path)

            # Verificar integridade básica
            restored_size = self.db_path.stat().st_size

            if restored_size == 0:
                print("[ERRO] Banco de dados restaurado está vazio!")
                return False

            # Validação padronizada (P1.1)
            if VALIDATION_AVAILABLE:
                try:
                    from app.config import Config
                    print("[RESTORE] Validando banco restaurado...")
                    validation_result = validate_restored_db(
                        db_path=self.db_path,
                        app_schema_version=Config.APP_SCHEMA_VERSION,
                        check_invariants=False,
                        verbose=False
                    )

                    if not validation_result.success:
                        print("[ERRO] Validação do banco restaurado falhou:")
                        for error in validation_result.errors:
                            print(f"  - {error}")

                        # Rollback: restaurar backup preventivo se existir
                        if preventive_backup and preventive_backup.exists():
                            print("\n[ROLLBACK] Restaurando backup preventivo...")
                            try:
                                shutil.copy2(preventive_backup, self.db_path)
                                print("[ROLLBACK] ✓ Backup preventivo restaurado")
                            except Exception as rollback_error:
                                print(f"[ERRO] Falha ao restaurar backup preventivo: {rollback_error}")

                        return False
                    else:
                        if validation_result.warnings:
                            print("[AVISO] Validação concluída com avisos:")
                            for warning in validation_result.warnings:
                                print(f"  - {warning}")
                except Exception as validation_error:
                    print(f"[AVISO] Erro ao validar banco restaurado: {validation_error}")
                    # Continuar mesmo se validação falhar (backward compatibility)

            print("[RESTORE] ✓ Banco de dados restaurado com sucesso!")
            print(f"[RESTORE]   Tamanho: {restored_size / (1024 * 1024):.2f} MB")

            return True

        except Exception as e:
            print(f"[ERRO] Erro ao restaurar backup: {e}")
            import traceback
            traceback.print_exc()
            return False


def main():
    """Função principal para executar restauração via linha de comando"""
    import argparse

    parser = argparse.ArgumentParser(description='Sistema de Restauração de Backups')
    parser.add_argument('--backup', type=str, help='Caminho do backup a restaurar')
    parser.add_argument('--no-backup', action='store_true', help='Não criar backup preventivo')
    parser.add_argument('--list', action='store_true', help='Listar backups disponíveis')

    args = parser.parse_args()

    # Criar gerenciador de restauração
    restore_mgr = RestoreManager()

    print("\n" + "="*60)
    print("SISTEMA DE RESTAURAÇÃO - Gestor de Pedidos")
    print("="*60)

    # Listar backups disponíveis
    backups = restore_mgr.list_backups()

    if not backups:
        print("\n[ERRO] Nenhum backup encontrado!")
        print(f"[INFO] Diretório de backups: {restore_mgr.backup_dir}")
        print("\n" + "="*60 + "\n")
        sys.exit(1)

    # Modo listar apenas
    if args.list:
        print(f"\nBackups disponíveis: {len(backups)}")
        print("-"*60)
        for idx, backup_path, size_mb, mod_time in backups:
            print(f"  [{idx}] {backup_path.name}")
            print(f"      Tamanho: {size_mb:.2f} MB")
            print(f"      Data: {mod_time.strftime('%Y-%m-%d %H:%M:%S')}")
            print()
        print("="*60 + "\n")
        return

    # Se especificou arquivo via --backup
    if args.backup:
        backup_to_restore = Path(args.backup)
    else:
        # Modo interativo: mostrar lista e solicitar escolha
        print(f"\nBackups disponíveis: {len(backups)}")
        print("-"*60)
        for idx, backup_path, size_mb, mod_time in backups:
            print(f"  [{idx}] {backup_path.name}")
            print(f"      Tamanho: {size_mb:.2f} MB")
            print(f"      Data: {mod_time.strftime('%Y-%m-%d %H:%M:%S')}")
            print()

        print("-"*60)

        try:
            escolha = input("\nEscolha o número do backup a restaurar (ou 'q' para sair): ").strip()

            if escolha.lower() == 'q':
                print("[INFO] Operação cancelada.")
                sys.exit(0)

            escolha_num = int(escolha)

            if escolha_num < 1 or escolha_num > len(backups):
                print(f"[ERRO] Escolha inválida! Digite um número entre 1 e {len(backups)}")
                sys.exit(1)

            # Obter backup escolhido
            backup_to_restore = backups[escolha_num - 1][1]

        except ValueError:
            print("[ERRO] Entrada inválida! Digite um número.")
            sys.exit(1)

    # Obter informações do backup selecionado
    backup_stat = backup_to_restore.stat()
    backup_date = datetime.fromtimestamp(backup_stat.st_mtime)
    backup_size_mb = backup_stat.st_size / (1024 * 1024)

    # Calcular diferença de tempo
    now = datetime.now()
    time_diff = now - backup_date
    days_old = time_diff.days
    hours_old = time_diff.seconds // 3600

    # Verificar se o backup é muito antigo
    is_old_backup = days_old > 7

    # Confirmação
    print("\n" + "="*60)
    print("ATENÇÃO: Restauração de Backup")
    print("="*60)
    print(f"\nBackup selecionado: {backup_to_restore.name}")
    print(f"Data do backup: {backup_date.strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"Tamanho: {backup_size_mb:.2f} MB")

    if days_old > 0:
        print(f"Idade: {days_old} dia(s) e {hours_old} hora(s)")
    else:
        print(f"Idade: {hours_old} hora(s)")

    if is_old_backup:
        print("\n" + "!"*60)
        print("AVISO CRÍTICO: Este backup é ANTIGO (mais de 7 dias)!")
        print("Restaurar este backup irá PERDER todos os dados criados após esta data!")
        print("!"*60)

    print(f"\nBanco atual será SUBSTITUÍDO: {restore_mgr.db_path}")

    if not args.no_backup and restore_mgr.db_path.exists():
        print("\nUm backup preventivo será criado antes da restauração.")

    print("\n" + "="*60)

    # Primeira confirmação
    confirmacao1 = input("\nTem certeza que deseja continuar? (digite 'SIM' em maiúsculas): ").strip()

    if confirmacao1 != 'SIM':
        # Registrar tentativa cancelada
        try:
            if AUDIT_LOGGER_AVAILABLE:
                get_audit_logger().log_restore_attempt(backup_to_restore, user_confirmed=False)
            else:
                basic_logger.warning(
                    f"RESTORE TENTATIVA | Arquivo: {backup_to_restore.name} | Status: CANCELADO"
                )
        except Exception:
            pass

        print("\n[INFO] Restauração cancelada.")
        sys.exit(0)

    # Segunda confirmação se backup é antigo
    if is_old_backup:
        print("\n" + "!"*60)
        print("CONFIRMAÇÃO ADICIONAL NECESSÁRIA")
        print("!"*60)
        print(f"\nEste backup é de {days_old} dia(s) atrás.")
        print("Você está prestes a PERDER todos os dados criados após:")
        print(f"  {backup_date.strftime('%d/%m/%Y %H:%M:%S')}")
        print("\nDigite 'CONFIRMO' em maiúsculas para prosseguir:")
        confirmacao2 = input("> ").strip()

        if confirmacao2 != 'CONFIRMO':
            # Registrar tentativa cancelada
            try:
                if AUDIT_LOGGER_AVAILABLE:
                    get_audit_logger().log_restore_attempt(backup_to_restore, user_confirmed=False)
                else:
                    basic_logger.warning(
                        f"RESTORE TENTATIVA | Arquivo: {backup_to_restore.name} | Status: CANCELADO (confirmação adicional)"
                    )
            except Exception:
                pass

            print("\n[INFO] Restauração cancelada na confirmação adicional.")
            sys.exit(0)

    # Registrar tentativa confirmada
    try:
        if AUDIT_LOGGER_AVAILABLE:
            get_audit_logger().log_restore_attempt(backup_to_restore, user_confirmed=True)
        else:
            basic_logger.warning(
                f"RESTORE TENTATIVA | Arquivo: {backup_to_restore.name} | Status: CONFIRMADO"
            )
    except Exception:
        pass

    # Executar restauração
    print()
    sucesso = restore_mgr.restore_backup(
        backup_to_restore,
        create_backup_first=not args.no_backup
    )

    print("="*60)

    if sucesso:
        # Registrar restauração bem-sucedida
        try:
            if AUDIT_LOGGER_AVAILABLE:
                get_audit_logger().log_restore_completed(backup_to_restore, success=True)
            else:
                basic_logger.warning(
                    f"RESTORE SUCESSO | Arquivo: {backup_to_restore.name}"
                )
        except Exception:
            pass

        print("\n[OK] Restauração concluída com sucesso!")
        print(f"[INFO] Backup restaurado: {backup_to_restore.name}")
        print(f"[INFO] Data do backup: {backup_date.strftime('%Y-%m-%d %H:%M:%S')}")
        print("\n[PRÓXIMO PASSO] Reinicie o servidor Flask para usar o banco restaurado.")
    else:
        # Registrar falha na restauração
        try:
            if AUDIT_LOGGER_AVAILABLE:
                get_audit_logger().log_restore_completed(backup_to_restore, success=False)
            else:
                basic_logger.error(
                    f"RESTORE FALHA | Arquivo: {backup_to_restore.name}"
                )
        except Exception:
            pass

        print("\n[ERRO] Falha na restauração!")
        sys.exit(1)

    print("\n" + "="*60 + "\n")


if __name__ == '__main__':
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

