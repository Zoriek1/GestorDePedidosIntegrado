# -*- coding: utf-8 -*-
"""
Backup agendado (P0.2)

- Janela padrão:
  - Seg-Sex: 07:00–18:00 (18:00 exatamente)
  - Sáb:     07:00–14:00 (14:00 exatamente)
  - Dom:     nunca

- Idempotência: não cria se já existe backup nos últimos N minutos (padrão 55)

Flags úteis:
  --dry-run   : não cria backup, só loga decisões
  --force     : ignora janela de horário
  --once      : ignora idempotência
  --minutes   : muda limite de idempotência
  --reason    : motivo no create_backup
  --no-compress : não compacta (se seu helper suportar)
"""

import argparse
import getpass
import os
import platform
import re
import sys
from datetime import datetime, timedelta
from pathlib import Path

# --- backend path ---
BACKEND_DIR = Path(__file__).parent.parent.parent
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from app.utils.backup_helper import create_backup  # noqa: E402


def should_run_backup_now(now: datetime) -> bool:
    weekday = now.weekday()  # 0=Segunda, 6=Domingo
    hour = now.hour
    minute = now.minute

    if weekday == 6:  # Domingo
        return False
    if weekday == 5:  # Sábado
        if hour < 7:
            return False
        if hour > 14:
            return False
        if hour == 14:
            return minute == 0
        return True
    # Seg–Sex
    if hour < 7:
        return False
    if hour > 18:
        return False
    if hour == 18:
        return minute == 0
    return True


def get_recent_backup_timestamp(backup_dir: Path, now: datetime, minutes_threshold: int) -> datetime | None:
    if not backup_dir.exists():
        return None

    cutoff_time = now - timedelta(minutes=minutes_threshold)
    most_recent_time = None

    patterns = ["database_*.db", "database_*.zip", "database_*.db-wal", "database_*.db-shm"]

    for pattern in patterns:
        for backup_file in backup_dir.glob(pattern):
            file_time = None
            # tenta extrair timestamp do nome
            m = re.search(r"(\d{8}_\d{6})", backup_file.name)
            if m:
                try:
                    file_time = datetime.strptime(m.group(1), "%Y%m%d_%H%M%S")
                except ValueError:
                    file_time = None

            # fallback: mtime
            if file_time is None:
                try:
                    file_time = datetime.fromtimestamp(backup_file.stat().st_mtime)
                except Exception:
                    continue

            if file_time >= cutoff_time:
                if most_recent_time is None or file_time > most_recent_time:
                    most_recent_time = file_time

    return most_recent_time


def acquire_lock(lock_path: Path) -> bool:
    """
    Lock simples por arquivo (evita dupla execução).
    """
    try:
        lock_path.parent.mkdir(parents=True, exist_ok=True)
        fd = os.open(str(lock_path), os.O_CREAT | os.O_EXCL | os.O_WRONLY)
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            f.write(str(os.getpid()))
        return True
    except FileExistsError:
        return False


def release_lock(lock_path: Path) -> None:
    try:
        lock_path.unlink(missing_ok=True)
    except Exception:
        pass


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--dry-run", action="store_true")
    p.add_argument("--force", action="store_true", help="Ignora janela de execução")
    p.add_argument("--once", action="store_true", help="Ignora idempotência")
    p.add_argument("--minutes", type=int, default=55, help="Limite de idempotência em minutos")
    p.add_argument("--reason", type=str, default="scheduled_hourly")
    p.add_argument("--no-compress", action="store_true")
    args = p.parse_args()

    now = datetime.now()

    logs_dir = BACKEND_DIR / "instance" / "logs"
    logs_dir.mkdir(parents=True, exist_ok=True)
    log_file = logs_dir / "scheduled_backup.log"

    def log(level: str, msg: str):
        ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        line = f"{ts} | {level} | {msg}\n"
        try:
            with open(log_file, "a", encoding="utf-8") as f:
                f.write(line)
        except Exception:
            pass
        print(f"[{level}] {msg}")

    # Diagnóstico mínimo sempre no início
    log("INFO", f"Start | user={getpass.getuser()} | host={platform.node()} | cwd={os.getcwd()}")
    log("INFO", f"python={sys.executable}")
    log("INFO", f"backend_dir={BACKEND_DIR}")

    lock_path = BACKEND_DIR / "instance" / "locks" / "scheduled_backup.lock"
    if not acquire_lock(lock_path):
        log("INFO", "Outra instância já está em execução - ignorado")
        return 0

    try:
        if not args.force and not should_run_backup_now(now):
            weekday_name = ["Segunda", "Terça", "Quarta", "Quinta", "Sexta", "Sábado", "Domingo"][now.weekday()]
            log("INFO", f"Fora da janela ({weekday_name} {now.hour:02d}:{now.minute:02d}) - ignorado")
            return 0

        backup_dir = BACKEND_DIR / "instance" / "backups"
        backup_dir.mkdir(parents=True, exist_ok=True)

        if not args.once:
            recent = get_recent_backup_timestamp(backup_dir, now=now, minutes_threshold=args.minutes)
            if recent:
                age_minutes = (now - recent).total_seconds() / 60
                log("INFO", f"Backup recente (há {age_minutes:.1f} min) - idempotência ativa, ignorado")
                return 0

        if args.dry_run:
            log("INFO", "DRY-RUN: condições ok; criaria backup agora")
            return 0

        log("INFO", f"Iniciando backup (reason={args.reason}, compress={not args.no_compress})")
        backup_path = create_backup(reason=args.reason, compress=(not args.no_compress), silent=False)

        if not backup_path:
            log("ERROR", "Falha ao criar backup (create_backup retornou None)")
            return 1

        try:
            size_mb = backup_path.stat().st_size / (1024 * 1024)
            log("SUCCESS", f"Backup criado: {backup_path.name} ({size_mb:.2f} MB)")
        except Exception:
            log("SUCCESS", f"Backup criado: {backup_path.name}")

        return 0

    except Exception as e:
        log("ERROR", f"Exceção: {e}")
        return 1

    finally:
        release_lock(lock_path)

if __name__ == "__main__":
    raise SystemExit(main())
