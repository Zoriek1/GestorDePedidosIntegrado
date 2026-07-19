# -*- coding: utf-8 -*-
"""
Meta CAPI Worker — processo independente para Docker.

Faz polling contínuo do outbox (Purchase + Lead/Contact) e envia os eventos para
a Meta Conversions API em segundo plano. O request da API apenas enfileira o
outbox e responde rápido — o envio acontece aqui, de forma assíncrona.

Além do polling rápido, mantém dois jobs diários herdados do antigo scheduler:
  - Safety-net Meta às HOUR:MINUTE (busca purchases do dia que não enfileiraram).
  - Autopagamento semanal (payroll) às PAYROLL_HOUR:PAYROLL_MINUTE.

Uso: python meta_capi_worker_entrypoint.py

Variáveis de ambiente:
  META_CAPI_WORKER_INTERVAL_SECONDS — intervalo do polling (default: 5)
  META_CAPI_RETRY_BACKOFF_SECONDS   — espera mínima p/ retentar failed-retryable (default: 300)
  META_SCHEDULER_HOUR / META_SCHEDULER_MINUTE — horário do safety-net diário (default: 23:00)
  PAYROLL_AUTO_HOUR / PAYROLL_AUTO_MINUTE     — horário do payroll (default: 06:00)
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

# Polling assíncrono do outbox
INTERVAL = max(1, int(os.environ.get("META_CAPI_WORKER_INTERVAL_SECONDS", 5)))
RETRY_BACKOFF = int(os.environ.get("META_CAPI_RETRY_BACKOFF_SECONDS", 300))

# Safety-net diário do Meta (busca purchases do dia que não enfileiraram)
HOUR = int(os.environ.get("META_SCHEDULER_HOUR", 23))
MINUTE = int(os.environ.get("META_SCHEDULER_MINUTE", 0))

# Autopagamento de salário semanal — roda 1x/dia, idempotente.
PAYROLL_HOUR = int(os.environ.get("PAYROLL_AUTO_HOUR", 6))
PAYROLL_MINUTE = int(os.environ.get("PAYROLL_AUTO_MINUTE", 0))


def run_outbox_cycle() -> None:
    """Ciclo de polling: envia pendentes + failed-retryable (Purchase e Lead).

    Loga apenas quando houve atividade (envio ou processamento), para não poluir.
    """
    try:
        with app.app_context():
            from app.commands.send_daily_purchases_to_meta_command import (
                SendDailyPurchasesToMetaCommand,
            )

            stats = SendDailyPurchasesToMetaCommand().process_outbox_cycle(
                limit=50, retry_backoff_seconds=RETRY_BACKOFF, quiet=True
            )
            from app.services.marketing_conversion_dispatcher import (
                MarketingConversionDispatcher,
            )

            marketing_stats = MarketingConversionDispatcher().process_cycle(limit=50)

            touched = (
                stats.get("pending_processed", 0)
                + stats.get("failed_retryable_processed", 0)
                + stats.get("lead_pending_processed", 0)
                + stats.get("lead_failed_retryable_processed", 0)
                + marketing_stats.get("processed", 0)
            )
            if touched:
                print(
                    "[CAPI_WORKER] Ciclo — "
                    f"Purchase ok={stats.get('sent_success', 0)} falha={stats.get('sent_failed', 0)} | "
                    f"Lead ok={stats.get('lead_sent_success', 0)} "
                    f"falha={stats.get('lead_sent_failed', 0)} | "
                    f"Marketing ok={marketing_stats.get('sent', 0)} "
                    f"submetido={marketing_stats.get('submitted', 0)} "
                    f"falha={marketing_stats.get('failed', 0)}",
                    flush=True,
                )
    except Exception as exc:
        print(f"[CAPI_WORKER] Erro no ciclo de outbox: {exc}", flush=True)


def run_daily_send() -> None:
    try:
        with app.app_context():
            from app.commands.send_daily_purchases_to_meta_command import (
                SendDailyPurchasesToMetaCommand,
            )

            result = SendDailyPurchasesToMetaCommand().execute()
            print(
                "[CAPI_WORKER] Safety-net diário — "
                f"Purchase ok={result.get('sent_success', 0)} falha={result.get('sent_failed', 0)} | "
                f"Lead funil ok={result.get('lead_sent_success', 0)} "
                f"falha={result.get('lead_sent_failed', 0)}",
                flush=True,
            )
            print(f"[CAPI_WORKER] Stats completas: {result}", flush=True)
    except Exception as exc:
        print(f"[CAPI_WORKER] Erro no safety-net diário: {exc}", flush=True)


def run_payroll_auto_today() -> None:
    try:
        with app.app_context():
            from app.services.ledger_service import auto_generate_for_today

            result = auto_generate_for_today()
            print(
                "[PAYROLL] auto_generate_for_today — "
                f"date={result.get('date')} alvo={result.get('vendedores_processados', 0)} "
                f"criados={result.get('created', 0)} pulados={result.get('skipped', 0)}",
                flush=True,
            )
    except Exception as exc:
        print(f"[PAYROLL] Erro no autopagamento: {exc}", flush=True)


def main() -> None:
    now_brt = datetime.datetime.now(BRAZIL_TZ)
    print(
        f"[CAPI_WORKER] Processo ativo desde {now_brt.isoformat()} — "
        f"polling do outbox a cada {INTERVAL}s (backoff retry {RETRY_BACKOFF}s); "
        f"safety-net Meta às {HOUR:02d}:{MINUTE:02d} BRT, "
        f"payroll às {PAYROLL_HOUR:02d}:{PAYROLL_MINUTE:02d} BRT.",
        flush=True,
    )

    last_run_date = None
    last_payroll_date = None

    while True:
        # Envio assíncrono contínuo do outbox.
        run_outbox_cycle()

        now = datetime.datetime.now(BRAZIL_TZ)
        today = now.date()

        if now.hour == HOUR and now.minute == MINUTE and last_run_date != today:
            last_run_date = today
            print(
                f"[CAPI_WORKER] Disparando safety-net diário às {now.strftime('%H:%M')} BRT",
                flush=True,
            )
            run_daily_send()

        if now.hour == PAYROLL_HOUR and now.minute == PAYROLL_MINUTE and last_payroll_date != today:
            last_payroll_date = today
            print(
                f"[PAYROLL] Disparando autopagamento às {now.strftime('%H:%M')} BRT",
                flush=True,
            )
            run_payroll_auto_today()

        time.sleep(INTERVAL)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n[CAPI_WORKER] Encerrado.", flush=True)
        sys.exit(0)
