# Plante uma Flor — Gestor de Pedidos

Sistema full-stack para operação de floricultura: pedidos, entregas, clientes, leads, recebíveis (folha + comissão) e integrações (Meta CAPI, Nuvemshop, UTMify, Google).

- **Backend**: Flask 3 + SQLAlchemy 2 + PostgreSQL 16 Alpine
- **Frontend**: React 19 + TypeScript + Vite + MUI + React Query + Dexie (PWA offline)
- **Deploy**: Docker Compose

## Início rápido

```bash
git clone <repo>
cp .env.example .env       # preencher segredos
docker compose up -d
docker compose exec backend flask create-admin
```

Frontend em `http://localhost:5000`, backend API em `http://localhost:5000/api`. Em dev sem Docker, `cd frontend_v2 && npm run dev` levanta o Vite em `:5173`.

## Estrutura

```
backend/           Flask app (app/), tests/, scripts/ (migrations, backup, export, meta)
frontend_v2/       React 19 app (src/features/ feature-based, app/router.tsx)
docs/              Documentação principal (4 arquivos — ver abaixo)
deploy/            Exemplos Caddy/Nginx/systemd
docker/            Stage do build (prebuilt-dist) + docker-compose.yml na raiz
```

## Documentação

- [docs/database.md](docs/database.md) — Postgres em prod, SQLite só em fallback, models, money handling, migrations custom
- [docs/deploy.md](docs/deploy.md) — Docker Compose, VPS, Cloudflare Tunnel, comandos operacionais
- [docs/recebiveis.md](docs/recebiveis.md) — Ledger double-entry, comissões, créditos semanais, quitação
- [docs/integrations.md](docs/integrations.md) — Meta CAPI, Nuvemshop, UTMify, Google, GraphHopper, VAPID Push
- [CLAUDE.md](CLAUDE.md) — convenções e referência rápida para agentes IA

## Comandos

```bash
# Backend (dentro do container)
docker compose exec backend pytest
docker compose exec backend ruff check . --fix && docker compose exec backend black .
docker compose exec backend python scripts/migrations/<arquivo>.py
docker compose exec backend python scripts/dump_routes.py

# Frontend (local)
cd frontend_v2 && npm install && npm run dev
cd frontend_v2 && npm run build && npm run lint
```

## Licença

MIT.
