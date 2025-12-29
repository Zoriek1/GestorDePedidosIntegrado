"""
Executa backup encriptado e upload para Google Drive.
Pode rodar uma vez ou em loop (para uso com schedule ou Task Scheduler).
"""
import argparse
import logging
import sys
import time
from pathlib import Path

# Garantir que o backend esteja no path
CURRENT_DIR = Path(__file__).resolve().parent
BACKEND_DIR = CURRENT_DIR.parent.parent
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from backup import BackupManager  # noqa: E402

LOGS_DIR = BACKEND_DIR / "instance" / "logs"
LOGS_DIR.mkdir(parents=True, exist_ok=True)
LOG_FILE = LOGS_DIR / "backup_gdrive.log"


def setup_logging():
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s | %(levelname)s | %(message)s",
        handlers=[
            logging.FileHandler(LOG_FILE, encoding="utf-8"),
            logging.StreamHandler(sys.stdout),
        ],
    )


def run_backup(args) -> bool:
    mgr = BackupManager(retention_days=args.retention)
    logging.info("Iniciando backup encriptado (compress=%s, gdrive_dir=%s)", not args.no_compress, args.gdrive_dir or "padrão")
    result = mgr.create_encrypted_backup(
        compress=not args.no_compress,
        upload_drive=args.upload_drive,
        keep_remote=args.keep_remote,
        folder_id=args.folder_id,
        remove_local_after_upload=not args.keep_local,
        reason="automatic",
        gdrive_dir=args.gdrive_dir,
    )
    if result:
        logging.info("Backup concluído com sucesso.")
        return True
    logging.error("Falha ao criar/guardar backup.")
    return False


def loop_forever(args):
    try:
        import schedule
    except ImportError:
        logging.error("Dependência 'schedule' não encontrada. Instale com pip install schedule.")
        sys.exit(1)

    interval_hours = args.interval_hours or 24
    logging.info("Agendando backup a cada %s hora(s).", interval_hours)
    schedule.every(interval_hours).hours.do(run_backup, args=args)

    while True:
        schedule.run_pending()
        time.sleep(30)


def main():
    parser = argparse.ArgumentParser(description="Agendar backup encriptado para Google Drive")
    parser.add_argument("--keep-remote", type=int, default=90, help="Qtd de backups para manter no Drive")
    parser.add_argument("--keep-local", action="store_true", help="Manter backup encriptado local")
    parser.add_argument("--no-compress", action="store_true", help="Não comprimir antes de encriptar")
    parser.add_argument("--folder-id", type=str, help="ID da pasta no Google Drive (opcional, para upload via API)")
    parser.add_argument("--gdrive-dir", type=str, help="Caminho do diretório do Google Drive Desktop (opcional)")
    parser.add_argument("--retention", type=int, default=30, help="Dias de retenção local")
    parser.add_argument("--interval-hours", type=int, default=24, help="Intervalo em horas para modo loop")
    parser.add_argument("--loop", action="store_true", help="Mantém o processo em loop (schedule)")
    parser.add_argument("--upload-drive", action="store_true", help="Fazer upload via API (opcional, padrão usa Google Drive Desktop)")

    args = parser.parse_args()
    setup_logging()

    if args.loop:
        loop_forever(args)
    else:
        success = run_backup(args)
        sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()

