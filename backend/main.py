# -*- coding: utf-8 -*-
"""
Plante Uma Flor v3.0 - PWA
Inicialização do servidor Flask
"""
import configparser
import json
import os
import sys
import time
from pathlib import Path


# #region agent log
def log_debug(msg, data):
    try:
        with open(
            r"c:\Gestor de Pedidos Plante uma flor\.cursor\debug.log",
            "a",
            encoding="utf-8",
        ) as f:
            f.write(
                json.dumps(
                    {
                        "sessionId": "debug-session",
                        "timestamp": int(time.time() * 1000),
                        "location": "main.py",
                        "message": msg,
                        "data": data,
                    }
                )
                + "\n"
            )
    except Exception as e:
        print(f"Log error: {e}")


# #endregion

# Carregar variáveis de ambiente do arquivo .env
from dotenv import load_dotenv  # noqa: E402

env_path = Path(__file__).parent / ".env"
load_dotenv(env_path)

# Configurar encoding UTF-8 para evitar erros no Windows
if sys.platform == "win32":
    import io

    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")

from app import create_app  # noqa: E402
from app.config import config  # noqa: E402
from app.utils.backup_helper import create_backup  # noqa: E402


def get_local_ip():
    """Descobre o IP local da máquina"""
    import socket

    try:
        # Conecta a um endereço externo para descobrir IP local
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        local_ip = s.getsockname()[0]
        s.close()
        return local_ip
    except Exception:
        return "192.168.1.148"  # Fallback


def get_hostname():
    """Lê o hostname configurado do arquivo config_servidor.ini"""
    config_file = Path(__file__).parent / "config" / "config_servidor.ini"

    if not config_file.exists():
        return "Gestor-pedidos.local"  # Padrão

    try:
        parser = configparser.ConfigParser()
        parser.read(config_file, encoding="utf-8")
        hostname = parser.get("SERVIDOR", "hostname", fallback="Gestor-pedidos.local")
        return hostname.strip()
    except Exception:
        return "Gestor-pedidos.local"  # Fallback em caso de erro


def check_ssl_certificates():
    """Verifica se os certificados SSL existem"""
    # SSL agora fica em instance/ssl
    from app.config import Config

    ssl_dir = Config.INSTANCE_DIR / "ssl"

    # Garantir que diretório existe
    if not ssl_dir.exists():
        ssl_dir.mkdir(parents=True, exist_ok=True)

    cert_file = ssl_dir / "cert.pem"
    key_file = ssl_dir / "key.pem"

    if cert_file.exists() and key_file.exists():
        return (str(cert_file), str(key_file))
    return None


def check_port_in_use(port=5000):
    """Verifica se a porta já está em uso"""
    import socket

    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(1)
        result = sock.connect_ex(("localhost", port))
        sock.close()
        log_debug("check_port_in_use", {"port": port, "result": result, "in_use": result == 0})
        return result == 0
    except Exception as e:
        log_debug("check_port_in_use exception", {"error": str(e)})
        return False


def main():
    """Função principal para iniciar o servidor"""
    is_reloader = os.environ.get("WERKZEUG_RUN_MAIN") == "true"
    log_debug("main starting", {"args": sys.argv, "WERKZEUG_RUN_MAIN": str(is_reloader)})

    # Se --help ou comandos CLI foram passados, usar Flask CLI
    if "--help" in sys.argv or any(arg.startswith("cli ") for arg in sys.argv):
        # create_app já foi importado no topo do arquivo
        app = create_app()
        # Flask CLI vai processar os comandos
        return

    # Verificar se a porta já está em uso (SKIP if in reloader child process)
    if not is_reloader:
        if check_port_in_use(5000):
            print("\n[AVISO] A porta 5000 ja esta em uso!")
            print("   Servidor pode ja estar rodando.")
            print("   Para parar: Execute parar_servidor.bat")
            print("   Ou tente acessar: https://localhost:5000\n")

            # Verificar se foi passado --force ou --yes para pular input
            force_start = (
                "--force" in sys.argv
                or "--yes" in sys.argv
                or os.environ.get("FORCE_START", "").lower() == "true"
            )

            if not force_start:
                try:
                    resposta = input("Deseja tentar iniciar mesmo assim? (s/n): ")
                    if resposta.lower() != "s":
                        print("\n[INFO] Inicializacao cancelada.")
                        return
                except (EOFError, KeyboardInterrupt):
                    print(
                        "\n[INFO] Input nao disponivel. Use --force para iniciar automaticamente."
                    )
                    print("[INFO] Inicializacao cancelada.")
                    return
    else:
        log_debug("Skipping port check", {"reason": "Running in reloader subprocess"})

    # Determinar ambiente (development ou production)
    env = os.environ.get("FLASK_ENV", "development")

    # Verificar modo HTTPS
    use_https = "--https" in sys.argv or os.environ.get("USE_HTTPS", "").lower() == "true"

    # Verificar se deve desativar reloader (para evitar problemas)
    no_reload = "--no-reload" in sys.argv or os.environ.get("NO_RELOAD", "").lower() == "true"

    # Criar aplicação com configuração apropriada
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

    # Criar backup sempre ao iniciar servidor
    # Apenas no processo pai para evitar backup duplicado
    # IMPORTANTE: Executar em thread separada para não bloquear inicialização do servidor
    if not is_reloader:
        import threading

        def create_startup_backup(app_instance):
            """Cria backup em thread separada para não bloquear servidor"""
            import time

            # Aguardar um pouco para garantir que o servidor está totalmente inicializado
            time.sleep(2)

            try:
                # Verificar se a aplicação ainda está válida antes de criar backup
                if app_instance is None:
                    return

                with app_instance.app_context():
                    print("\n[BACKUP] Criando backup automático ao iniciar servidor...")
                    backup_path = create_backup(reason="startup", silent=False)
                    if backup_path:
                        print(f"[BACKUP] ✓ Backup criado: {backup_path.name}\n")
                    else:
                        print("[AVISO] Falha ao criar backup automático ao iniciar servidor\n")
            except RuntimeError as e:
                # Ignorar erros de contexto quando servidor está sendo finalizado
                if "application context" in str(e).lower() or "working outside" in str(e).lower():
                    return
                print(f"[AVISO] Erro ao criar backup ao iniciar servidor: {e}")
            except Exception as e:
                # Capturar erro específico de datetime se ocorrer
                error_msg = str(e)
                if "datetime" in error_msg.lower() and "not associated" in error_msg.lower():
                    print(f"[AVISO] Erro de importação ao criar backup: {e}")
                    print("[AVISO] Tentando novamente com import explícito...")
                    try:
                        with app_instance.app_context():
                            backup_path = create_backup(reason="startup", silent=False)
                            if backup_path:
                                print(f"[BACKUP] ✓ Backup criado após retry: {backup_path.name}\n")
                    except Exception as retry_error:
                        print(f"[AVISO] Falha no retry do backup: {retry_error}")
                else:
                    print(f"[AVISO] Erro ao criar backup ao iniciar servidor: {e}")
                # Continuar mesmo se backup falhar

        # Iniciar backup em thread separada (daemon = morre quando servidor fecha)
        backup_thread = threading.Thread(
            target=create_startup_backup,
            args=(app,),
            daemon=True,
            name="StartupBackupThread",
        )
        backup_thread.start()
        print("[INFO] Backup inicial iniciado em thread separada (não bloqueia servidor)")

    # Descobrir IP local e hostname
    local_ip = get_local_ip()
    hostname = get_hostname()

    # Configurar SSL
    ssl_context = None
    protocol = "http"

    if use_https:
        ssl_certs = check_ssl_certificates()
        if ssl_certs:
            ssl_context = ssl_certs
            protocol = "https"
            print("\n[HTTPS] Modo HTTPS ativado!")
        else:
            print("\n[AVISO] Modo HTTPS solicitado mas certificados nao encontrados!")
            print("   Execute: scripts/ssl/GERAR_CERTIFICADOS.bat")
            print("   Iniciando em HTTP...\n")

    # Informações de inicialização
    print("\n" + "=" * 60)
    print("PLANTE UMA FLOR - PWA v3.0")
    print("=" * 60)
    print(f"Ambiente: {env}")
    print(f"Protocolo: {protocol.upper()}")
    print(f"Host: {app_config.HOST}")
    print(f"Porta: {app_config.PORT}")

    # Mostrar status do debug baseado no que será usado
    debug_status = "OFF (estavel)" if no_reload else app_config.DEBUG
    print(f"Debug: {debug_status}")
    print(f"Banco de dados: {app_config.DATABASE_PATH}")

    if ssl_context:
        print("Certificados SSL: [OK] Configurados")

    print("\nServidor acessivel em:")
    print(f"   Local:    {protocol}://localhost:{app_config.PORT}")
    print(f"   Hostname: {protocol}://{hostname}:{app_config.PORT}")
    print(f"   IP Rede:  {protocol}://{local_ip}:{app_config.PORT}")

    if protocol == "https":
        print("\n[INFO] PWA pode ser instalado em todos os dispositivos!")
        print("   Acesse via HTTPS e clique no botao de instalar")
    else:
        print("\n[AVISO] Modo HTTP: PWA so instala em localhost")
        print("   Para instalar em outros dispositivos, use HTTPS:")
        print("   1. Execute: scripts/ssl/GERAR_CERTIFICADOS.bat")
        print("   2. Inicie com: iniciar_servidor_https.bat")

    # Configurar opções de execução
    debug_mode = app_config.DEBUG if not no_reload else False
    use_reloader_mode = not no_reload

    if no_reload:
        print("\n[INFO] Modo estavel: Debug e reloader desativados")

    print("\n[OK] Pressione Ctrl+C para parar o servidor")
    print("=" * 60 + "\n")

    # Usar run_simple do Werkzeug para melhor controle e threading
    # Isso resolve problemas de requisições não sendo processadas
    from werkzeug.serving import run_simple

    print("[SERVIDOR] Iniciando servidor Flask...")
    print(f"[SERVIDOR] Host: {app_config.HOST}, Porta: {app_config.PORT}")
    print("[SERVIDOR] Threading: HABILITADO (permite requisições simultâneas)")
    print(f"[SERVIDOR] Debug: {debug_mode}, Reloader: {use_reloader_mode}")
    print("[SERVIDOR] Servidor pronto para receber requisições!\n")

    # Adicionar hook para logar primeira requisição (diagnóstico)
    @app.before_request
    def log_first_request():
        """Log primeira requisição para confirmar que servidor está processando"""
        from flask import request

        # Apenas logar primeira requisição para não poluir logs
        if not hasattr(app, "_first_request_logged"):
            print(f"[SERVIDOR] ✓ Primeira requisição recebida: {request.method} {request.path}")
            print("[SERVIDOR] ✓ Servidor está processando requisições corretamente\n")
            app._first_request_logged = True

    # Iniciar servidor com run_simple (mais robusto que app.run())
    try:
        log_debug(
            "run_simple calling",
            {
                "host": app_config.HOST,
                "port": app_config.PORT,
                "threaded": True,
                "debug": debug_mode,
                "reloader": use_reloader_mode,
            },
        )

        run_simple(
            hostname=app_config.HOST,
            port=app_config.PORT,
            application=app,
            use_debugger=debug_mode,
            use_reloader=use_reloader_mode,
            ssl_context=ssl_context,
            threaded=True,  # CRÍTICO: Permite requisições simultâneas
            processes=1,  # Não usar processos múltiplos (SQLite não suporta)
        )
    except KeyboardInterrupt:
        print("\n\n[AVISO] Servidor encerrado pelo usuario")
        print("[OK] Obrigado por usar Plante Uma Flor!\n")
    except Exception as e:
        log_debug("app.run exception", {"error": str(e)})
        print(f"\n[ERRO] Erro ao iniciar servidor: {e}\n")
        raise


if __name__ == "__main__":
    main()
