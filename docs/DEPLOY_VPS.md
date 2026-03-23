# Deploy em VPS

Guia para rodar o Gestor de Pedidos em uma VPS. Inclui Docker com PostgreSQL, exemplos de proxy e checklist.

---

## 1. Docker

**Implementado:** `Dockerfile` (multi-stage, targets `backend` e `scheduler`) e `docker-compose.yml` na raiz.

**Deploy via GitHub Actions (push `main`):** o job de frontend gera `dist/` e o deploy copia para `docker/prebuilt-dist/` na VPS e sobe os containers com `USE_PREBUILT_DIST=1` (sem rodar Vite de novo na VPS). Configure o secret opcional `VITE_GOOGLE_MAPS_API_KEY` no repositório se o build precisar da mesma chave que em produção.

**Diagnóstico de picos RAM/CPU:** [DEPLOY_DIAGNOSTICS.md](./DEPLOY_DIAGNOSTICS.md).

**Onde usar:**
- **`Dockerfile`** — na raiz do repositório ou em `backend/` (se o build do frontend for em estágio separado).
- **`docker-compose.yml`** — na raiz do repositório (orquestra backend + volumes + env).

**Como usar:**
```bash
cp .env.example .env   # Ajuste POSTGRES_PASSWORD, SECRET_KEY, ADMIN_PASSWORD
docker compose up -d
```
- Frontend: build automático no estágio 1 do Dockerfile.
- Backend: Waitress via `wsgi.py`; entrypoint roda `flask db upgrade` antes de iniciar.
- PostgreSQL: serviço `db` com volume persistente.

**Referência no projeto:** `backend/wsgi.py`, `backend/requirements.txt`, `frontend_v2/package.json` (script `build`).

---

## 2. Reverse proxy e HTTPS

**Implementado:** Exemplos em `deploy/nginx.conf.example` e `deploy/Caddyfile.example`.

**Onde usar:**
- **Config do proxy** — fora do repo, no servidor (ex.: `/etc/nginx/sites-available/gestor` ou Caddyfile em `/etc/caddy/`).
- **Opcional no repo:** pasta `deploy/` ou `docs/deploy/` com exemplos (ex.: `deploy/nginx.conf.example`, `deploy/Caddyfile.example`) para copiar e ajustar na VPS.

**Como usar:**
- Proxy reverso apontando para o backend (ex.: `http://127.0.0.1:5000`).
- Terminar SSL (ex.: Let's Encrypt) no proxy.
- Definir no backend `USE_HTTPS=true` quando o tráfego externo for HTTPS.
- O backend já lê `X-Forwarded-*` em um ponto (ex.: IP real em `backend/app/middleware.py`).

**Referência no projeto:** `backend/app/middleware.py` (proxy), `backend/app/config.py` (`USE_HTTPS`), `docs/configuration.md` (produção).

### Tunnel (Cloudflare Tunnel, ngrok, etc.)

Quando o acesso é por domínio via tunnel (ex.: `https://gestaopedidos.planteumaflor.online` apontando para `http://VPS:5000`):

1. **Backend:** no `.env` da raiz (ou do Compose), defina `USE_HTTPS=true` para o backend gerar links/redirects em HTTPS quando necessário.
2. **Frontend:** o build em Docker já usa API relativa (`/api`), então o login e as chamadas à API vão para o mesmo host que a página (o tunnel encaminha tudo para o backend). Não use `VITE_API_BASE_URL` absoluta (ex.: `http://IP:5000/api`) no build de produção.
3. **Tunnel:** configure o tunnel para encaminhar **todo** o host (incluindo `/api/*`) para `http://127.0.0.1:5000` (ou o IP/porta do backend). Assim tanto a SPA quanto a API são servidas pelo mesmo backend.

Se o login não funcionar pelo domínio e funcionar por IP:5000, confira que o tunnel encaminha `/api` e que não há bloqueio de headers (ex.: `Authorization`).

---

## 3. Process manager (quando não usar Docker)

**Implementado:** Exemplo em `deploy/gestor-pedidos.service.example`.

**Onde usar:**
- **Unit systemd** — no servidor, ex.: `/etc/systemd/system/gestor-pedidos.service`.
- **Opcional no repo:** exemplo em `deploy/gestor-pedidos.service.example` ou em `docs/deploy/`.

**Como usar:**
- Comando de start: `python wsgi.py` (ou `gunicorn`) com `FLASK_ENV=production` e `PORT`/`HOST` definidos.
- Working directory: raiz do backend ou do repositório (conforme onde estiver `frontend_v2/dist`).
- Reinício em falha e após reboot: `Restart=on-failure`, `WantedBy=multi-user.target`.

**Referência no projeto:** `backend/wsgi.py`, `backend/main.py` (comando `flask cli start`).

---

## 4. Variáveis de ambiente do backend (produção)

**Implementado:** `backend/.env.example` com variáveis do backend; `.env.example` na raiz para docker-compose.

**Onde usar:**
- **`.env` de produção** — na VPS (ou no container), em `backend/.env` ou no diretório de onde o processo é iniciado, **nunca versionado**.
- **Template** — pode existir `backend/.env.example` com variáveis do backend (lista completa em `docs/configuration.md`).

**Variáveis mínimas recomendadas para produção:**

| Variável | Onde usar | Exemplo / Nota |
|----------|------------|-----------------|
| `FLASK_ENV` ou `APP_ENV` | .env do backend | `production` |
| `SECRET_KEY` | .env do backend | Gerar com `python -c "import secrets; print(secrets.token_hex(32))"` |
| `ADMIN_PASSWORD` | .env do backend | Senha forte do admin |
| `USE_HTTPS` | .env do backend | `true` se o proxy terminar SSL |
| `PORT` | .env do backend | Ex.: `5000` (mesmo que o proxy use) |
| `HOST` | .env do backend | Ex.: `127.0.0.1` se só o proxy acessar |
| `DATABASE_URL` (PostgreSQL) | .env do backend | `postgresql://user:pass@host:5432/dbname` |
| `FRONTEND_DIST_PATH` (opcional) | .env do backend | Caminho absoluto para `dist` (ex.: `/app/frontend_v2/dist`) |
| `ENABLE_DEBUG_ENDPOINTS` | .env do backend | `false` em produção |

**Referência no projeto:** `backend/app/config.py`, `docs/configuration.md`.

---

## 5. Build do frontend no deploy

**Implementado:** Três caminhos possíveis:

1. **CI + VPS (padrão):** GitHub Actions faz `npm run build` no runner, envia o `dist/` para `docker/prebuilt-dist/` na VPS e o Docker usa `USE_PREBUILT_DIST=1` (sem segundo Vite na VPS).
2. **Só Docker na VPS:** `USE_PREBUILT_DIST=0` (default): o estágio `frontend-assets` do `Dockerfile` roda `npm ci` + `npm run build` no build da imagem.
3. **Script manual:** na raiz, `./deploy.sh` — build local do frontend, copia para `docker/prebuilt-dist/` e `docker compose` com `USE_PREBUILT_DIST=1`.

**Onde usar:**
- **CI:** [.github/workflows/ci.yml](../.github/workflows/ci.yml).
- **Docker:** `docker/prebuilt-dist/` (conteúdo do `dist/`; só `.gitkeep` versionado) + arg `USE_PREBUILT_DIST`.
- **Sem Docker:** `cd frontend_v2 && npm ci && npm run build` e servir `dist/` conforme [PRODUCTION.md](../frontend_v2/docs/PRODUCTION.md).

**Como usar:**
- O backend serve o SPA de `Path(__file__).parent.parent.parent / "frontend_v2" / "dist"` (em `backend/app/static.py`). Ou seja, a estrutura esperada é: repositório contém `backend/` e `frontend_v2/dist/` na mesma raiz.
- Garantir que `frontend_v2/dist` exista antes de subir o backend (ou que a imagem Docker já inclua esse diretório).

**Referência no projeto:** `backend/app/static.py`, `frontend_v2/package.json` (`build`), `frontend_v2/docs/PRODUCTION.md`.

---

## 6. Caminho do frontend (dist) configurável

**Implementado:** Variável `FRONTEND_DIST_PATH` em `config.py`; `static.py` usa quando definida.

**Onde usar:**
- **Variável de ambiente:** `FRONTEND_DIST_PATH` — caminho absoluto para o diretório `dist` (ex.: `/app/frontend_v2/dist`).
- **Padrão:** se não definida, usa `{raiz_repo}/frontend_v2/dist`.

**Referência no projeto:** `backend/app/static.py` (linhas em torno de 127 e 172).

---

## 7. Banco de dados: PostgreSQL

O projeto suporta **SQLite** (dev) e **PostgreSQL** (produção/VPS). Use `DATABASE_URL` para PostgreSQL:

```env
DATABASE_URL=postgresql://user:pass@host:5432/dbname
```

- **Backup PostgreSQL:** usa `pg_dump`; arquivos `.sql` ou `.sql.gz`.
- **Backup SQLite:** mantém lógica atual (`.db`/`.zip`).
- **fonte_helper:** detecta dialect e usa `information_schema` (PostgreSQL) ou `sqlite_master` (SQLite).

---

## 8. Banco de dados e migrations no primeiro deploy

**Implementado:** Entrypoint do Docker roda `flask db upgrade` antes de iniciar.

**Onde usar:**
- **Script de deploy ou Docker** — antes de iniciar o app: `cd backend && flask db upgrade` (ou com variáveis de ambiente já carregadas).
- **Documentação** — este doc ou um "Deploy checklist" na mesma pasta.

**Como usar:**
- **SQLite:** diretório default `~/var/lib/database`; rodar `flask db upgrade`.
- **PostgreSQL:** `flask db upgrade` no entrypoint do container.

**Referência no projeto:** `backend/app/extensions.py` (Flask-Migrate), `backend/app/config.py` (`DATABASE_PATH`), `docs/configuration.md`.

---

## 9. Backups na VPS

**Implementado:** `backend/.env.example` inclui `GDRIVE_BACKUP_DIR=/var/backups/gestor-pedidos` para VPS. Backup no startup; PostgreSQL usa `pg_dump`.

**Variáveis:**
- `GDRIVE_BACKUP_DIR` — diretório local para backups (ex.: `/var/backups/gestor-pedidos`).
- `BACKUP_SECONDARY_DIR` — cópia secundária (opcional).

**Backup agendado (cron):** para backups diários, adicione ao crontab:
```bash
# Backup diário às 3h (ajuste /opt/gestor-pedidos conforme seu deploy)
0 3 * * * cd /opt/gestor-pedidos/backend && python scripts/backup/backup.py --no-encrypt >> /var/log/gestor-backup.log 2>&1
```

**Referência no projeto:** `backend/app/config.py`, `backend/app/utils/backup_helper.py`, `docs/configuration.md`.

---

## 10. Firewall

Abra as portas na VPS para HTTP/HTTPS:
```bash
# UFW (Ubuntu/Debian)
ufw allow 80/tcp
ufw allow 443/tcp
ufw allow 22/tcp   # SSH
ufw enable
```

---

## 11. Deploy sem Docker

Para rodar direto na host (PostgreSQL instalado na VPS):

1. Instale PostgreSQL, Python 3.11+, Node 20.
2. Crie o banco: `createdb gestor_pedidos`.
3. Clone o repo, configure `backend/.env` com `DATABASE_URL=postgresql://...`.
4. `cd frontend_v2 && npm ci && npm run build`.
5. `cd backend && pip install -r requirements.txt && flask db upgrade && python wsgi.py`.
6. Copie `deploy/gestor-pedidos.service.example` para `/etc/systemd/system/`, ajuste paths e `systemctl enable --now gestor-pedidos`.

---

## Resumo — Onde colocar cada coisa

| O que | Onde (no repo ou na VPS) |
|-------|---------------------------|
| Dockerfile | Raiz do repo ou `backend/` |
| docker-compose.yml | Raiz do repo |
| Exemplo Nginx/Caddy | `deploy/*.example` ou `docs/deploy/` |
| Exemplo systemd | `deploy/*.service.example` ou `docs/deploy/` |
| .env produção | Só na VPS (ou no container), nunca versionado |
| .env.example backend | `backend/.env.example` (conteúdo de backend) |
| Build frontend | Script de deploy ou estágio Docker |
| Migrations | Comando no script de deploy ou no entrypoint Docker |
| Config backups | Variáveis no .env da VPS |
| Nuvemshop (puxar pedidos) | NUVEMSHOP_* no .env + reconectar loja; ver backend/docs/NUVEMSHOP_CREDENTIALS.md §9 |

---

---

## Checklist — Primeiro deploy com Docker

1. Clone o repositório na VPS.
2. `cp .env.example .env` e edite: `POSTGRES_PASSWORD`, `SECRET_KEY`, `ADMIN_PASSWORD`.
3. `docker compose up -d`.
4. Aguarde o healthcheck do PostgreSQL e a subida do backend.
5. Configure Nginx ou Caddy (copie `deploy/nginx.conf.example` ou `deploy/Caddyfile.example`).
6. Aponte o domínio e obtenha SSL (certbot ou Caddy automático).
7. Defina `USE_HTTPS=true` no `.env` se o proxy terminar SSL.
8. Abra portas 80/443 no firewall (seção 11).
9. (Opcional) Google Sheets/Drive: siga [GOOGLE_CREDENTIALS_VPS.md](GOOGLE_CREDENTIALS_VPS.md).
10. (Opcional) Nuvemshop: defina no `.env` as variáveis `NUVEMSHOP_APP_ID`, `NUVEMSHOP_CLIENT_SECRET`, `NUVEMSHOP_USER_AGENT` e **`NUVEMSHOP_PUBLIC_BASE_URL`** (URL pública da VPS, ex.: `https://gestaopedidos.planteumaflor.online`); atualize a Redirect URL no painel do app Nuvemshop; reconecte a loja em Integrações > Nuvemshop. Ver [backend/docs/NUVEMSHOP_CREDENTIALS.md](../backend/docs/NUVEMSHOP_CREDENTIALS.md) §9.
