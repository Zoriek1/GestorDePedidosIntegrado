# -*- coding: utf-8 -*-
"""
Teste Recorrente de Restauração (P0.4)
Testa se backups podem ser restaurados corretamente em ambiente sandbox
"""
import shutil
import sys
import tempfile
from datetime import datetime
from pathlib import Path

# Adicionar backend ao path
backend_dir = Path(__file__).parent.parent.parent
if str(backend_dir) not in sys.path:
    sys.path.insert(0, str(backend_dir))

from app.config import Config  # noqa: E402
from scripts.backup.validate_db import validate_restored_db  # noqa: E402

# Importar status (P1.5) com fallback
try:
    from scripts.backup.status import update_backup_status

    STATUS_AVAILABLE = True
except ImportError:
    STATUS_AVAILABLE = False


def find_most_recent_backup(backup_dir: Path):
    """
    Encontra o backup mais recente válido

    Returns:
        Path do backup ou None se não encontrar
    """
    if not backup_dir.exists():
        return None

    # Buscar arquivos de backup (database_*.db ou database_*.zip)
    backups = []
    for pattern in ["database_*.db", "database_*.zip"]:
        backups.extend(backup_dir.glob(pattern))

    if not backups:
        return None

    # Ordenar por data de modificação (mais recente primeiro)
    backups.sort(key=lambda p: p.stat().st_mtime, reverse=True)

    return backups[0]


def extract_backup_if_needed(backup_path: Path, temp_dir: Path) -> Path:
    """
    Extrai backup se for ZIP, retorna caminho do .db

    Returns:
        Path do arquivo .db (extraído ou original)
    """
    if backup_path.suffix == ".zip":
        # Extrair ZIP
        import zipfile

        with zipfile.ZipFile(backup_path, "r") as zip_ref:
            # Procurar arquivo .db dentro do ZIP
            db_files = [f for f in zip_ref.namelist() if f.endswith(".db")]
            if not db_files:
                raise ValueError(f"Nenhum arquivo .db encontrado no ZIP: {backup_path}")

            # Extrair primeiro .db encontrado
            db_name = db_files[0]
            zip_ref.extract(db_name, temp_dir)
            return temp_dir / db_name
    else:
        # Copiar arquivo .db
        db_path = temp_dir / backup_path.name
        shutil.copy2(backup_path, db_path)
        return db_path


def main():
    """Função principal do teste de restauração"""
    now = datetime.now()
    timestamp = now.strftime("%Y-%m-%d %H:%M:%S")

    # Configurar logging
    logs_dir = backend_dir / "instance" / "logs"
    logs_dir.mkdir(parents=True, exist_ok=True)
    log_file = logs_dir / "restore_test.log"

    def log_message(level: str, message: str):
        """Loga mensagem no arquivo e no console"""
        log_entry = f"{timestamp} | {level} | {message}\n"
        try:
            with open(log_file, "a", encoding="utf-8") as f:
                f.write(log_entry)
        except Exception:
            pass
        print(f"[{level}] {message}")

    log_message("INFO", "=" * 60)
    log_message("INFO", "TESTE DE RESTAURAÇÃO (P0.4)")
    log_message("INFO", "=" * 60)

    # Encontrar backup mais recente
    backup_dir = backend_dir / "instance" / "backups"
    backup_dir.mkdir(parents=True, exist_ok=True)

    backup_path = find_most_recent_backup(backup_dir)
    if not backup_path:
        log_message("ERROR", "Nenhum backup encontrado para teste")
        sys.exit(1)

    log_message("INFO", f"Backup selecionado: {backup_path.name}")
    log_message("INFO", f"Tamanho: {backup_path.stat().st_size / (1024 * 1024):.2f} MB")

    # Criar diretório temporário para restauração
    temp_dir = None
    try:
        temp_dir = Path(tempfile.mkdtemp(prefix="restore_test_"))
        log_message("INFO", f"Diretório temporário: {temp_dir}")

        # Extrair/copiar backup
        log_message("INFO", "Extraindo backup...")
        db_path = extract_backup_if_needed(backup_path, temp_dir)
        log_message("INFO", f"Banco extraído: {db_path.name}")

        # Executar validação padronizada (P1.1)
        log_message("INFO", "Executando validação do banco restaurado...")
        validation_result = validate_restored_db(
            db_path=db_path,
            app_schema_version=Config.APP_SCHEMA_VERSION,
            check_invariants=False,
            verbose=False,
        )

        if validation_result.success:
            log_message("SUCCESS", "Validação completa: OK")
            if validation_result.warnings:
                for warning in validation_result.warnings:
                    log_message("WARNING", f"Aviso: {warning}")

            # Atualizar status (P1.5)
            if STATUS_AVAILABLE:
                try:
                    update_backup_status(last_restore_test_ok_at=datetime.now().isoformat())
                except Exception as status_error:
                    log_message("WARNING", f"Erro ao atualizar status: {status_error}")
        else:
            log_message("ERROR", "Validação falhou:")
            for error in validation_result.errors:
                log_message("ERROR", f"  - {error}")
            if validation_result.warnings:
                for warning in validation_result.warnings:
                    log_message("WARNING", f"Aviso: {warning}")

            # Atualizar status (P1.5)
            if STATUS_AVAILABLE:
                try:
                    error_msg = "; ".join(validation_result.errors)
                    update_backup_status(last_restore_test_error=error_msg)
                except Exception as status_error:
                    log_message("WARNING", f"Erro ao atualizar status: {status_error}")

            sys.exit(1)

        log_message("INFO", "=" * 60)
        log_message("SUCCESS", "TESTE DE RESTAURAÇÃO CONCLUÍDO COM SUCESSO")
        log_message("INFO", "=" * 60)
        sys.exit(0)

    except Exception as e:
        log_message("ERROR", f"Erro durante teste de restauração: {e}")
        import traceback

        traceback.print_exc()
        sys.exit(1)
    finally:
        # Limpar arquivos temporários
        if temp_dir and temp_dir.exists():
            try:
                shutil.rmtree(temp_dir)
                log_message("INFO", "Arquivos temporários removidos")
            except Exception as e:
                log_message("WARNING", f"Erro ao remover arquivos temporários: {e}")


if __name__ == "__main__":
    main()
