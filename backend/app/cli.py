# -*- coding: utf-8 -*-
"""
CLI Unificado - Plante Uma Flor
Comandos Flask CLI + Click para operações do sistema
"""
import os
import socket
import subprocess
from pathlib import Path

import click
from flask import Flask
from flask.cli import AppGroup

# Criar grupo de comandos
cli = AppGroup("cli")


def get_app():
    """Retorna instância da aplicação Flask"""
    from app import create_app

    return create_app()


@cli.command("start")
@click.option("--https", is_flag=True, help="Iniciar servidor em modo HTTPS")
@click.option("--port", type=int, default=None, help="Porta do servidor (padrão: 5000)")
@click.option("--host", type=str, default=None, help="Host do servidor (padrão: 0.0.0.0)")
@click.option("--no-reload", is_flag=True, help="Desativar reloader (modo estável)")
def start_server(https, port, host, no_reload):
    """Inicia o servidor Flask"""
    app = get_app()

    # Configurar porta e host
    server_port = port or int(os.environ.get("PORT", 5000))
    server_host = host or os.environ.get("HOST", "0.0.0.0")

    # Verificar porta
    if check_port_in_use(server_port):
        click.echo(f"[AVISO] Porta {server_port} já está em uso!", err=True)
        if not os.environ.get("FORCE_START", "").lower() == "true":
            if not click.confirm("Deseja tentar iniciar mesmo assim?"):
                return

    # Configurar SSL se necessário
    ssl_context = None
    if https:
        ssl_context = check_ssl_certificates()
        if not ssl_context:
            click.echo("[AVISO] Certificados SSL não encontrados!", err=True)
            click.echo("Execute: flask cli ssl generate")
            https = False

    # Configurar opções de execução
    debug = not no_reload and (os.environ.get("DEBUG", "False").lower() == "true")
    use_reloader = not no_reload

    click.echo("\n[OK] Iniciando servidor...")
    click.echo(f"  Host: {server_host}")
    click.echo(f"  Porta: {server_port}")
    click.echo(f'  Protocolo: {"HTTPS" if https else "HTTP"}')
    click.echo(f"  Debug: {debug}")
    click.echo()

    try:
        # Usar run_simple do Werkzeug diretamente para evitar bloqueio do Flask CLI
        from werkzeug.serving import run_simple

        run_simple(
            hostname=server_host,
            port=server_port,
            application=app,
            use_debugger=debug,
            use_reloader=use_reloader,
            ssl_context=ssl_context,
            threaded=True,  # Habilitar threads para melhor concorrência
        )
    except KeyboardInterrupt:
        click.echo("\n[INFO] Servidor encerrado pelo usuário")


@cli.command("backup")
@click.option("--restore", type=str, default=None, help="Caminho do backup para restaurar")
@click.option("--list", "list_backups", is_flag=True, help="Listar backups disponíveis")
@click.option("--stats", is_flag=True, help="Mostrar estatísticas de backups")
def backup_command(restore, list_backups, stats):
    """Gerencia backups do banco de dados"""
    from app.utils.backup_helper import create_backup, get_backup_stats

    app = get_app()

    with app.app_context():
        if restore:
            # Restaurar backup
            from scripts.backup.restore import RestoreManager

            backend_dir = Path(__file__).parent.parent
            instance_dir = backend_dir / "instance"
            restore_mgr = RestoreManager(
                db_path=instance_dir / "database.db",
                backup_dir=instance_dir / "backups",
            )

            backup_path = Path(restore)
            if not backup_path.exists():
                click.echo(f"[ERRO] Backup não encontrado: {backup_path}", err=True)
                return

            if not click.confirm(
                f"Restaurar backup {backup_path.name}? Isso substituirá o banco atual!"
            ):
                return

            try:
                restore_mgr.restore_backup(str(backup_path))
                click.echo("[OK] Backup restaurado com sucesso!")
            except Exception as e:
                click.echo(f"[ERRO] Falha ao restaurar: {e}", err=True)

        elif list_backups:
            # Listar backups
            from scripts.backup.backup import BackupManager

            backend_dir = Path(__file__).parent.parent
            instance_dir = backend_dir / "instance"
            backup_mgr = BackupManager(
                db_path=instance_dir / "database.db",
                backup_dir=instance_dir / "backups",
            )

            backups = backup_mgr.list_backups()
            if not backups:
                click.echo("[INFO] Nenhum backup encontrado")
                return

            click.echo(f"\nBackups disponíveis ({len(backups)}):")
            for i, (backup_path, size_mb, mod_time) in enumerate(backups, 1):
                click.echo(
                    f'  {i}. {backup_path.name} ({size_mb:.2f} MB) - {mod_time.strftime("%Y-%m-%d %H:%M:%S")}'
                )

        elif stats:
            # Estatísticas
            backup_stats = get_backup_stats()
            click.echo("\nEstatísticas de Backups:")
            click.echo(f'  Total: {backup_stats["count"]} backups')
            click.echo(f'  Tamanho total: {backup_stats["total_size_mb"]:.2f} MB')
            if backup_stats["oldest"]:
                click.echo(f'  Mais antigo: {backup_stats["oldest"].strftime("%Y-%m-%d %H:%M:%S")}')
            if backup_stats["newest"]:
                click.echo(
                    f'  Mais recente: {backup_stats["newest"].strftime("%Y-%m-%d %H:%M:%S")}'
                )

        else:
            # Criar backup
            click.echo("[INFO] Criando backup...")
            backup_path = create_backup(reason="manual", silent=False)
            if backup_path:
                click.echo(f"[OK] Backup criado: {backup_path.name}")
            else:
                click.echo("[ERRO] Falha ao criar backup", err=True)


@cli.command("ssl")
@click.argument("action", type=click.Choice(["generate", "check"]))
@click.option("--hostname", type=str, default=None, help="Hostname para o certificado")
def ssl_command(action, hostname):
    """Gerencia certificados SSL"""
    if action == "generate":
        generate_ssl_certificates(hostname)
    elif action == "check":
        check_ssl_status()


@cli.command("cache")
@click.argument("action", type=click.Choice(["update"]))
def cache_command(action):
    """
    (LEGADO) Gerenciamento de cache do service worker.

    O frontend atual (React/Vite PWA em frontend) já faz versionamento por hash e autoUpdate.
    Este comando existia apenas para o service worker do frontend legado (diretório frontend/),
    que foi removido.
    """
    raise click.ClickException(
        "Comando legado removido: o frontend atual (frontend) não usa este workflow."
    )


@cli.command("check")
@click.argument("resource", type=click.Choice(["port"]))
@click.option("--port", type=int, default=5000, help="Porta para verificar")
def check_command(resource, port):
    """Verifica recursos do sistema"""
    if resource == "port":
        if check_port_in_use(port):
            click.echo(f"[INFO] Porta {port} está em uso")
            # Tentar identificar processo
            try:
                import psutil

                for conn in psutil.net_connections():
                    if conn.laddr.port == port:
                        proc = psutil.Process(conn.pid)
                        click.echo(f"  Processo: {proc.name()} (PID: {conn.pid})")
            except ImportError:
                pass
        else:
            click.echo(f"[OK] Porta {port} está livre")


# Comandos Flask-Migrate (db)
@cli.command("db")
@click.argument(
    "action",
    type=click.Choice(["init", "migrate", "upgrade", "downgrade", "current", "history"]),
)
@click.option("--message", "-m", type=str, default=None, help="Mensagem para migração")
@click.option("--revision", type=str, default=None, help="Revisão para upgrade/downgrade")
def db_command(action, message, revision):
    """Comandos de migração do banco de dados (Flask-Migrate)"""
    from flask_migrate import current, downgrade, history, init, migrate, upgrade

    app = get_app()

    with app.app_context():
        if action == "init":
            if message:
                click.echo("[AVISO] --message não é usado com init")
            init()
            click.echo("[OK] Migrações inicializadas")

        elif action == "migrate":
            if not message:
                message = click.prompt("Mensagem da migração", default="Auto migration")
            migrate(message=message)
            click.echo("[OK] Migração criada")

        elif action == "upgrade":
            if revision:
                upgrade(revision=revision)
            else:
                upgrade()
            click.echo("[OK] Migrações aplicadas")

        elif action == "downgrade":
            if not revision:
                revision = click.prompt("Revisão para downgrade")
            downgrade(revision=revision)
            click.echo("[OK] Downgrade aplicado")

        elif action == "current":
            current()

        elif action == "history":
            history()


# Funções auxiliares


def check_port_in_use(port):
    """Verifica se uma porta está em uso"""
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(1)
        result = sock.connect_ex(("localhost", port))
        sock.close()
        return result == 0
    except Exception:
        return False


def check_ssl_certificates():
    """Verifica se os certificados SSL existem e retorna tupla (cert, key) ou None"""
    from app.config import Config

    ssl_dir = Config.INSTANCE_DIR / "ssl"

    if not ssl_dir.exists():
        ssl_dir.mkdir(parents=True, exist_ok=True)

    cert_file = ssl_dir / "cert.pem"
    key_file = ssl_dir / "key.pem"

    if cert_file.exists() and key_file.exists():
        return (str(cert_file), str(key_file))
    return None


def generate_ssl_certificates(hostname=None):
    """Gera certificados SSL usando mkcert"""
    import configparser

    # Obter hostname
    if not hostname:
        config_file = Path(__file__).parent.parent / "config" / "config_servidor.ini"
        if config_file.exists():
            try:
                parser = configparser.ConfigParser()
                parser.read(config_file, encoding="utf-8")
                hostname = parser.get("SERVIDOR", "hostname", fallback="Gestor-pedidos.local")
            except Exception:
                hostname = "Gestor-pedidos.local"
        else:
            hostname = "Gestor-pedidos.local"

    # Descobrir IPs
    ip_list = ["localhost", "127.0.0.1", "::1"]
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        local_ip = s.getsockname()[0]
        s.close()
        if local_ip not in ip_list:
            ip_list.append(local_ip)
    except Exception:
        pass

    # Verificar mkcert
    scripts_dir = Path(__file__).parent.parent / "scripts" / "ssl"
    mkcert_exe = scripts_dir / "mkcert.exe"

    if not mkcert_exe.exists():
        click.echo("[ERRO] mkcert.exe não encontrado!", err=True)
        click.echo("Execute primeiro: scripts\\ssl\\INSTALAR_MKCERT_SIMPLES.bat")
        return

    # Criar diretório SSL
    from app.config import Config

    ssl_dir = Config.INSTANCE_DIR / "ssl"
    ssl_dir.mkdir(parents=True, exist_ok=True)

    # Instalar CA (pode falhar se já estiver instalado)
    click.echo("[INFO] Instalando CA raiz...")
    subprocess.run([str(mkcert_exe), "-install"], check=False)

    # Gerar certificados
    click.echo(f"[INFO] Gerando certificados para {hostname} e IPs...")
    cert_file = ssl_dir / "cert.pem"
    key_file = ssl_dir / "key.pem"

    cmd = [
        str(mkcert_exe),
        "-cert-file",
        str(cert_file),
        "-key-file",
        str(key_file),
        hostname,
    ] + ip_list

    try:
        subprocess.run(cmd, check=True)
        click.echo(f"[OK] Certificados gerados em {ssl_dir}")
        click.echo(f"  Certificado: {cert_file}")
        click.echo(f"  Chave: {key_file}")
    except subprocess.CalledProcessError:
        click.echo("[ERRO] Falha ao gerar certificados", err=True)


def check_ssl_status():
    """Verifica status dos certificados SSL"""
    ssl_context = check_ssl_certificates()
    if ssl_context:
        click.echo("[OK] Certificados SSL encontrados:")
        click.echo(f"  Certificado: {ssl_context[0]}")
        click.echo(f"  Chave: {ssl_context[1]}")
    else:
        click.echo("[AVISO] Certificados SSL não encontrados")
        click.echo("Execute: flask cli ssl generate")


@cli.command("hash-password")
@click.argument("password")
def hash_password_command(password):
    """Gera hash bcrypt para uso em ADMIN_PASSWORD_HASH.

    Exemplo: flask cli hash-password minha_senha
    """
    try:
        import bcrypt as _bcrypt

        hashed = _bcrypt.hashpw(password.encode("utf-8"), _bcrypt.gensalt())
        click.echo("\nHash gerado (copie para ADMIN_PASSWORD_HASH no .env):")
        click.echo(hashed.decode("utf-8"))
        click.echo()
    except ImportError:
        click.echo("[ERRO] bcrypt não instalado. Execute: pip install bcrypt", err=True)


@cli.command("create-admin")
@click.option("--email", prompt="Email do admin", help="Email do usuário admin")
@click.option(
    "--password",
    prompt="Senha",
    hide_input=True,
    confirmation_prompt=True,
    help="Senha do admin (mín. 8 chars)",
)
@click.option("--name", default="Admin", help="Nome de exibição (padrão: Admin)")
def create_admin_command(email, password, name):
    """Cria o primeiro usuário admin no banco de dados.

    Exemplo: flask cli create-admin --email admin@puf.com --password senha_forte
    """
    if len(password) < 8:
        raise click.ClickException("Senha deve ter pelo menos 8 caracteres.")

    from app import create_app

    app = create_app()
    with app.app_context():
        try:
            from app import db
            from app.models.store import Store
            from app.models.user import User
            from app.services.auth_service import hash_password

            existing = User.query.filter_by(email=email).first()
            if existing:
                raise click.ClickException(f"Usuário com email '{email}' já existe.")

            # Bootstrap usa a loja default (resolvida por slug, nunca por ID).
            default_store = Store.query.filter_by(slug="default").first()
            if not default_store:
                raise click.ClickException(
                    "Loja default ausente. Rode as migrations "
                    "(scripts/migrations/add_store_foundation.py) antes de criar o admin."
                )

            admin = User(
                name=name,
                email=email,
                password_hash=hash_password(password),
                role="admin",
                is_active=True,
                store_ref_id=default_store.id,
            )
            db.session.add(admin)
            db.session.commit()
            click.echo(f"\n[OK] Admin criado: {email} (id={admin.id})")
        except click.ClickException:
            raise
        except Exception as e:
            raise click.ClickException(f"Erro ao criar admin: {e}") from e


@cli.command("create-store")
@click.option("--name", prompt="Nome da loja", help="Nome de exibição da loja")
@click.option("--slug", prompt="Slug", help="Identificador único, ex: floricultura-x")
@click.option(
    "--email-domain",
    prompt="Domínio de e-mail",
    help="Domínio que resolve o tenant no login, ex: floriculturax.com",
)
@click.option("--admin-email", prompt="E-mail do admin", help="Login do admin da loja")
@click.option(
    "--admin-password",
    prompt="Senha do admin",
    hide_input=True,
    confirmation_prompt=True,
    help="Senha do admin (mín. 8 chars)",
)
@click.option("--admin-name", default="Admin", help="Nome de exibição do admin (padrão: Admin)")
def create_store_command(name, slug, email_domain, admin_email, admin_password, admin_name):
    """Provisiona um tenant novo: loja + configurações + usuário admin.

    Tudo numa transação: se qualquer etapa falhar, nada é gravado.

    Exemplo:
      flask cli create-store --name "Floricultura X" --slug floricultura-x \\
        --email-domain floriculturax.com --admin-email dono@floriculturax.com
    """
    slug = (slug or "").strip().lower()
    email_domain = (email_domain or "").strip().lower().lstrip("@")
    admin_email = (admin_email or "").strip().lower()

    if len(admin_password) < 8:
        raise click.ClickException("Senha deve ter pelo menos 8 caracteres.")
    if "@" not in admin_email:
        raise click.ClickException("--admin-email deve ser um e-mail válido.")
    # O login resolve a loja pelo domínio; um admin fora do domínio da própria
    # loja cairia na busca global e não conseguiria entrar de forma previsível.
    if admin_email.rsplit("@", 1)[-1] != email_domain:
        raise click.ClickException(
            f"--admin-email deve pertencer ao domínio da loja (@{email_domain})."
        )

    from app import create_app

    app = create_app()
    with app.app_context():
        from app import db
        from app.models.store import Store
        from app.models.user import User
        from app.services.auth_service import hash_password
        from app.services.integration_settings_service import get_or_create_settings

        if Store.query.filter_by(slug=slug).first():
            raise click.ClickException(f"Já existe loja com slug '{slug}'.")
        if Store.query.filter_by(email_domain=email_domain).first():
            raise click.ClickException(f"Já existe loja com domínio '{email_domain}'.")
        if User.query.filter_by(email=admin_email).first():
            raise click.ClickException(f"Já existe usuário com e-mail '{admin_email}'.")

        try:
            store = Store(name=name, slug=slug, email_domain=email_domain, active=True)
            db.session.add(store)
            db.session.flush()  # precisa do store.id para settings e admin

            get_or_create_settings(store.id)

            admin = User(
                name=admin_name,
                email=admin_email,
                password_hash=hash_password(admin_password),
                role="admin",
                is_active=True,
                store_ref_id=store.id,
            )
            db.session.add(admin)
            db.session.commit()
        except Exception as e:
            db.session.rollback()
            raise click.ClickException(f"Erro ao criar loja: {e}") from e

        click.echo(f"\n[OK] Loja criada: {name} (id={store.id}, slug={slug})")
        click.echo(f"[OK] Admin: {admin_email} (id={admin.id})")
        click.echo(f"[INFO] Logins desta loja usam e-mails @{email_domain}")


# Registrar comandos no Flask CLI
def register_commands(app: Flask):
    """Registra comandos CLI na aplicação"""
    app.cli.add_command(cli)
