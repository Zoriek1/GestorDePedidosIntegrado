# -*- coding: utf-8 -*-
"""
Sincroniza backups locais para um diretório no Google Drive.

Uso:
  python scripts/backup/sync_backups_to_gdrive.py --dest "G:\\Meu Drive\\Backups\\GestorPedidos"
ou
  python scripts/backup/sync_backups_to_gdrive.py --dest "C:\\Users\\Caio\\Google Drive\\Backups\\GestorPedidos"

Dica: rode isso como tarefa separada, com seu usuário.
"""

import argparse
import getpass
import os
import shutil
import sys
from datetime import datetime, timedelta
from pathlib import Path

BACKEND_DIR = Path(__file__).parent.parent.parent
SRC_DIR = BACKEND_DIR / "instance" / "backups"
LOG_DIR = BACKEND_DIR / "instance" / "logs"
LOG_DIR.mkdir(parents=True, exist_ok=True)
LOG_FILE = LOG_DIR / "gdrive_sync.log"


def log(level: str, msg: str):
    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    line = f"{ts} | {level} | {msg}\n"
    try:
        with open(LOG_FILE, "a", encoding="utf-8") as f:
            f.write(line)
    except Exception:
        pass
    print(f"[{level}] {msg}")


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--dest", required=True, help="Pasta de destino no Google Drive")
    p.add_argument("--hours", type=int, default=48, help="Copiar apenas backups das últimas N horas")
    args = p.parse_args()

    log("INFO", f"Start | user={getpass.getuser()} | cwd={os.getcwd()} | python={sys.executable}")
    log("INFO", f"src={SRC_DIR}")

    if not SRC_DIR.exists():
        log("ERROR", "Diretório de backups não existe ainda (src)")
        return 1

    dest_dir = Path(args.dest)
    try:
        dest_dir.mkdir(parents=True, exist_ok=True)
    except Exception as e:
        log("ERROR", f"Não foi possível criar/acessar destino: {dest_dir} | erro={e}")
        log("ERROR", "Isso costuma acontecer por permissão/Drive virtual. Rode este script no SEU usuário.")
        return 1

    # Teste de permissão real (escrita)
    probe = dest_dir / ".write_test.tmp"
    try:
        probe.write_text("ok", encoding="utf-8")
        probe.unlink(missing_ok=True)
    except Exception as e:
        log("ERROR", f"Sem permissão de escrita no destino: {dest_dir} | erro={e}")
        log("ERROR", "Rode este script no seu usuário (não SYSTEM) e confirme o caminho do Google Drive.")
        return 1

    cutoff = datetime.now() - timedelta(hours=args.hours)
    copied = 0
    skipped = 0

    # copia tudo relacionado a database_*.*
    for f in SRC_DIR.glob("database_*.*"):
        try:
            mtime = datetime.fromtimestamp(f.stat().st_mtime)
        except Exception:
            continue
        if mtime < cutoff:
            continue

        target = dest_dir / f.name
        if target.exists() and target.stat().st_size == f.stat().st_size:
            skipped += 1
            continue

        try:
            shutil.copy2(f, target)
            copied += 1
        except Exception as e:
            log("ERROR", f"Falha copiando {f.name} -> {target}: {e}")

    log("INFO", f"Done | copied={copied} | skipped={skipped} | dest={dest_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
