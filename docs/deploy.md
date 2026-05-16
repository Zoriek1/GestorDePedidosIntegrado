# Deploy e Operação

## Local (Docker Compose)

```bash
cp .env.example .env       # preencher segredos
docker compose up -d        # sobe db (Postgres 16 Alpine) + backend + scheduler (Meta CAPI)
docker compose logs -f backend
```

Serviços ([docker-compose.yml](../docker-compose.yml)):

| Serviço | Imagem | Função |
|---|---|---|
| `db` | `postgres:16-alpine` | Banco principal. Volume `pg_data`. |
| `backend` | build local (target `backend` em [Dockerfile](../Dockerfile)) | API Flask + SPA Vite servido como estático. Porta 5000. |
| `scheduler` | build local (target `scheduler`) | Flush do outbox Meta CAPI. Sem Node. Entrypoint: `python meta_scheduler_entrypoint.py`. |

O `frontend-assets` (stage do Dockerfile) faz `npm ci && npm run build` no container; se `USE_PREBUILT_DIST=1` e `docker/prebuilt-dist/index.html` existir, copia direto (CI pré-builda e injeta).

## VPS

Repo clonado, `cp backend/.env.example .env`, `docker compose up -d`. Atrás de reverse proxy (Caddy ou Nginx) — exemplos em [deploy/](../deploy/):

- `deploy/Caddyfile.example` — terminação TLS automática via Let's Encrypt
- `deploy/nginx.conf.example` — alternativa com cert manual
- `deploy/gestor-pedidos.service.example` — systemd unit (se não usar docker compose direto)

Script `deploy.sh` na raiz: pull + rebuild + restart com `USE_PREBUILT_DIST=1` se o CI já tiver subido o dist.

### Cloudflare Tunnel (Meta Gateway)

A integração Meta CAPI Gateway exige domínio público para `/capig/*`. Use Cloudflare Tunnel para expor `gestaopedidos.planteumaflor.online` → backend:5000.

Variável crítica:
```env
META_CAPI_USE_GATEWAY=true
META_CAPI_GATEWAY_DOMAIN=gestaopedidos.planteumaflor.online
```

## Comandos operacionais úteis

```bash
# Logs
docker compose logs -f backend
docker compose logs -f scheduler

# Migration custom
docker compose exec backend python scripts/migrations/<arquivo>.py

# Criar primeiro admin
docker compose exec backend flask create-admin

# Pytest
docker compose exec backend pytest

# Lint/format
docker compose exec backend ruff check . --fix
docker compose exec backend black .

# Listar todas as rotas registradas
docker compose exec backend python scripts/dump_routes.py
```

## Backup

Scripts em [backend/scripts/backup/](../backend/scripts/backup/) — backup local + upload para Google Drive (pasta encriptada). Configurar `GOOGLE_APPLICATION_CREDENTIALS` apontando para `backend/user/config/google_credentials.json` no container.

## Variáveis de ambiente

Mínimas para subir:
- `POSTGRES_USER`, `POSTGRES_PASSWORD`, `POSTGRES_DB`
- `SECRET_KEY`, `JWT_SECRET_KEY`
- `ADMIN_PASSWORD` (para `flask create-admin`)

Integrações: ver [integrations.md](integrations.md).

Flags úteis:
- `ENABLE_DEBUG_ENDPOINTS=true` — habilita `/api/debug/*` (off por padrão em prod)
- `ENABLE_RATE_LIMIT=false` — desliga rate limit (default ligado: 60/min, 1000/h)
- `USE_PREBUILT_DIST=1` — não roda Vite no build do container
