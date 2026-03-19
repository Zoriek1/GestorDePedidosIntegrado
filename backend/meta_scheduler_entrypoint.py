# -*- coding: utf-8 -*-
"""
Meta CAPI Scheduler — processo independente para Docker.

Roda em loop verificando o horário BRT e dispara o envio diário
de eventos Purchase para a Meta Conversions API.

Uso: python meta_scheduler_entrypoint.py

Variáveis de ambiente opcionais:
  META_SCHEDULER_HOUR  — hora do disparo (default: 23)
  META_SCHEDULER_MINUTE — minuto do disparo (default: 0)
"""
import datetime
import os
import sys
import time
from pathlib import Path

from dotenv import load_dotenv

load_dotenv(Path(__file__).parent / ".env")

try:
    from zoneinfo import ZoneInfo
except ImportError:
    from backports.zoneinfo import ZoneInfo

BRAZIL_TZ = ZoneInfo("America/Sao_Paulo")

from app import create_app  # noqa: E402
from app.config import config  # noqa: E402

env = os.environ.get("FLASK_ENV", "production")
app_config = config.get(env, config["default"])

app = create_app(
    config={
        "SECRET_KEY": app_config.SECRET_KEY,
        "SQLALCHEMY_DATABASE_URI": app_config.SQLALCHEMY_DATABASE_URI,
        "SQLALCHEMY_TRACK_MODIFICATIONS": app_config.SQLALCHEMY_TRACK_MODIFICATIONS,
        "JSON_AS_ASCII": app_config.JSON_AS_ASCII,
        "JSON_SORT_KEYS": app_config.JSON_SORT_KEYS,
    }
)

HOUR = int(os.environ.get("META_SCHEDULER_HOUR", 23))
MINUTE = int(os.environ.get("META_SCHEDULER_MINUTE", 0))


def run_daily_send() -> None:
    try:
        with app.app_context():
            from app.commands.send_daily_purchases_to_meta_command import (
                SendDailyPurchasesToMetaCommand,
            )

            result = SendDailyPurchasesToMetaCommand().execute()
            print(f"[META_SCHEDULER] Envio concluído: {result}", flush=True)
    except Exception as exc:
        print(f"[META_SCHEDULER] Erro no envio diário: {exc}", flush=True)


def main() -> None:
    now_brt = datetime.datetime.now(BRAZIL_TZ)
    print(
        f"[META_SCHEDULER] Processo ativo desde {now_brt.isoformat()} — disparo diário às {HOUR:02d}:{MINUTE:02d} BRT.",
        flush=True,
    )

    last_run_date = None

    while True:
        now = datetime.datetime.now(BRAZIL_TZ)
        today = now.date()

        if now.hour == HOUR and now.minute == MINUTE and last_run_date != today:
            last_run_date = today
            print(
                f"[META_SCHEDULER] Disparando envio às {now.strftime('%H:%M')} BRT",
                flush=True,
            )
            run_daily_send()

        time.sleep(30)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n[META_SCHEDULER] Encerrado.", flush=True)
        sys.exit(0)
