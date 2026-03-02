# -*- coding: utf-8 -*-
"""
WSGI entry point para produção com Waitress
"""
import os
import sys
from pathlib import Path

# Configurar encoding UTF-8 e desabilitar buffering para evitar erros no Windows
if sys.platform == "win32":
    import io

    # Desabilitar buffering para output aparecer imediatamente
    sys.stdout = io.TextIOWrapper(
        sys.stdout.buffer, encoding="utf-8", errors="replace", line_buffering=True
    )
    sys.stderr = io.TextIOWrapper(
        sys.stderr.buffer, encoding="utf-8", errors="replace", line_buffering=True
    )

# Carregar variáveis de ambiente do arquivo .env
from dotenv import load_dotenv

env_path = Path(__file__).parent / ".env"
load_dotenv(env_path)

from app import create_app  # noqa: E402
from app.config import config  # noqa: E402

# Determinar ambiente (padrão: production)
env = os.environ.get("FLASK_ENV", "production")

# Obter configuração apropriada
app_config = config.get(env, config["default"])

# Criar aplicação Flask
app = create_app(
    config={
        "SECRET_KEY": app_config.SECRET_KEY,
        "SQLALCHEMY_DATABASE_URI": app_config.SQLALCHEMY_DATABASE_URI,
        "SQLALCHEMY_TRACK_MODIFICATIONS": app_config.SQLALCHEMY_TRACK_MODIFICATIONS,
        "JSON_AS_ASCII": app_config.JSON_AS_ASCII,
        "JSON_SORT_KEYS": app_config.JSON_SORT_KEYS,
    }
)

# --- Scheduler Meta CAPI (23:00 BRT) ---
import threading
import time as _time
import datetime as _datetime

try:
    from zoneinfo import ZoneInfo as _ZI
except ImportError:
    from backports.zoneinfo import ZoneInfo as _ZI

_BRAZIL_TZ = _ZI("America/Sao_Paulo")
_meta_last_run: dict = {"date": None}


def _run_meta_daily_send() -> None:
    """Executa SendDailyPurchasesToMetaCommand com contexto Flask."""
    try:
        with app.app_context():
            from app.commands.send_daily_purchases_to_meta_command import (
                SendDailyPurchasesToMetaCommand,
            )
            result = SendDailyPurchasesToMetaCommand().execute()
            print(f"[META_SCHEDULER] Envio concluído: {result}", flush=True)
    except Exception as exc:
        print(f"[META_SCHEDULER] Erro no envio diário: {exc}", flush=True)


def _meta_scheduler_loop() -> None:
    """Loop que verifica às 23:00 BRT e dispara o envio diário."""
    print("[META_SCHEDULER] Iniciado — aguardando 23:00 BRT.", flush=True)
    while True:
        now_brt = _datetime.datetime.now(_BRAZIL_TZ)
        today = now_brt.date()
        if now_brt.hour == 23 and now_brt.minute == 0 and _meta_last_run["date"] != today:
            _meta_last_run["date"] = today
            print(f"[META_SCHEDULER] Disparando envio às {now_brt.strftime('%H:%M')} BRT", flush=True)
            _run_meta_daily_send()
        _time.sleep(30)


_meta_thread = threading.Thread(
    target=_meta_scheduler_loop,
    daemon=True,
    name="MetaCAPIScheduler",
)
_meta_thread.start()
# --- Fim Scheduler ---


# Para execução direta (python wsgi.py)
if __name__ == "__main__":
    try:
        from waitress import serve

        host = os.environ.get("HOST", "0.0.0.0")
        port = int(os.environ.get("PORT", 5000))
        threads = int(os.environ.get("THREADS", 4))

        # Parâmetros otimizados para produção
        channel_timeout = int(
            os.environ.get("CHANNEL_TIMEOUT", 120)
        )  # Timeout para conexões (segundos)
        cleanup_interval = int(
            os.environ.get("CLEANUP_INTERVAL", 30)
        )  # Intervalo de limpeza (segundos)

        # Forçar flush do stdout para garantir que as mensagens apareçam
        sys.stdout.flush()

        print("\n" + "=" * 60, flush=True)
        print("PLANTE UMA FLOR - PWA v3.0 (PRODUÇÃO)", flush=True)
        print("=" * 60, flush=True)
        print(f"Ambiente: {env}", flush=True)
        print("Servidor: Waitress (WSGI)", flush=True)
        print(f"Host: {host}", flush=True)
        print(f"Porta: {port}", flush=True)
        print(f"Threads: {threads}", flush=True)
        print(f"Channel Timeout: {channel_timeout}s", flush=True)
        print(f"Cleanup Interval: {cleanup_interval}s", flush=True)
        print(f"Banco de dados: {app_config.DATABASE_PATH}", flush=True)
        print("\nServidor acessível em:", flush=True)
        print(f"   Local:    http://localhost:{port}", flush=True)
        print(f"   Rede:     http://{host}:{port}", flush=True)
        print("\n[OK] Servidor de produção iniciado!", flush=True)
        print("=" * 60 + "\n", flush=True)
        print("[INFO] Iniciando Waitress...", flush=True)
        print(f"[INFO] Escutando em {host}:{port}", flush=True)
        print("[INFO] Pressione Ctrl+C para parar o servidor\n", flush=True)
        sys.stdout.flush()

        try:
            serve(
                app,
                host=host,
                port=port,
                threads=threads,
                channel_timeout=channel_timeout,
                cleanup_interval=cleanup_interval,
            )
        except Exception as e:
            print(f"\n[ERRO CRÍTICO] Falha ao iniciar Waitress: {e}")
            import traceback

            traceback.print_exc()
            sys.exit(1)
    except ImportError:
        print("\n[ERRO] Waitress não está instalado!")
        print("   Execute: pip install waitress\n")
        sys.exit(1)
    except KeyboardInterrupt:
        print("\n\n[INFO] Servidor encerrado pelo usuário")
        print("[OK] Obrigado por usar Plante Uma Flor!\n")
