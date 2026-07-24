# AGENTS.md

Referência única para agentes IA (Claude Code, Codex, etc.) neste repositório.
Doc canônico — `CLAUDE.md` apenas aponta pra cá.

---

## Stack

- **Banco**: PostgreSQL 16 Alpine (service `db`). SQLite só como fallback em testes/dev sem Docker (ver [docs/database.md](docs/database.md)).
- **Backend**: Flask 3 + SQLAlchemy 2, JWT seletivo via `@require_auth`. Prod roda em Waitress.
- **Frontend**: React 19 + Vite + MUI + React Query + Zustand (auth) + Dexie (PWA offline).
- **Deploy**: Docker Compose.

## Comandos

### Dev (Docker com hot-reload — recomendado)

```bash
docker compose -f docker-compose.dev.yml up        # app em http://localhost:5173
docker compose -f docker-compose.dev.yml exec backend flask create-admin
docker compose -f docker-compose.dev.yml exec backend pytest
```

Vite (`:5173`) faz proxy de `/api` → `backend:5000`. Editar `./backend` ou `./frontend` recarrega sozinho (bind mount).

### Prod / operação

```bash
docker compose up -d                                       # usa docker-compose.yml (Waitress + SPA buildado)
docker compose exec backend pytest
docker compose exec backend ruff check . --fix
docker compose exec backend black .
docker compose exec backend python scripts/migrations/<arquivo>.py
docker compose exec backend flask create-admin
```

Sem Docker (Windows): `cd frontend && npm run dev` (Vite :5173) + `./venv/Scripts/pytest.exe`.

---

## Backend — arquitetura

Camadas: `routes/` → `services/` → `repositories/` → `models/`. Routes validam input e chamam service; service tem a lógica; repository faz queries; model é SQLAlchemy.

### Blueprints ([backend/app/factory.py](backend/app/factory.py))

`pedidos_bp` `/api/pedidos/*` · `rotas_bp` `/api/pedidos/rota-otimizada` · `clientes_bp` `/api/clientes/*` · `fontes_bp` `/api/fontes-pedido/*` · `core_bp` (`/api/health`, `/api/cep/<cep>`, `/api/stats`, `/api/cleanup`, distâncias/taxas, export leads) · `auth_bp` `/api/auth/*` · `config_bp` `/api/config/*` · `backup_admin_bp` `/api/admin/backup/*` · `nuvemshop_bp` `/api/integrations/nuvemshop/*` · `notifications_bp` `/api/notifications/*` (VAPID) · `leads_bp` `/api/leads/*` · `users_bp` `/api/users/*` (CRUD + payroll + comissão) · `ledger_bp` `/api/ledger/*` · `meta_gateway_bp` `/capig/*` · `storefront_bp` `/storefront/*` · `debug_bp` `/api/debug/*` (só se `ENABLE_DEBUG_ENDPOINTS=true`) · `mercado_pago_bp` `/api/integrations/mercadopago/*` (Point → Bling).

### Roles

`admin | vendedor | atendente | entregador | viewer` ([user.py:35](backend/app/models/user.py#L35)). Auth global OFF; só rotas com `@require_auth` exigem JWT.

### Money & timestamps

- `Pedido.valor` é `String` BR → use `parse_brl_money()` ([money.py](backend/app/utils/money.py)).
- `LedgerEntry.amount` é `Numeric(12,2)` positivo → `float(entry.amount)` ao serializar.
- Timestamps via `datetime_now_brazil()` (TZ `America/Sao_Paulo`).

### Migrations

Scripts Python idempotentes em [backend/scripts/migrations/](backend/scripts/migrations/) — **não** Alembic. [entrypoint.sh](backend/entrypoint.sh) roda os essenciais no boot. Template em [docs/database.md](docs/database.md).

**⚠️ Armadilha conhecida: AccessExclusiveLock deadlock em DDL loops**

Cada migration script chama `create_app()` no module level, criando pool de conexões próprio. O padrão problemático é:

1. `db.session.execute("ALTER TABLE ...")` → abre transação, segura `AccessExclusiveLock` na tabela
2. `column_exists()` → usa `db.inspect(db.engine)` (conexão **diferente** do pool) para ler `pg_catalog.pg_attribute`
3. A leitura fica bloqueada pelo lock da própria sessão → **deadlock infinito**

**Regra obrigatória:** sempre `db.session.commit()` **após cada** `ALTER TABLE`, antes de qualquer `column_exists()` ou `inspector.get_columns()`. Nunca acumular DDLs em uma única transação.

```python
# ❌ ERRADO — deadlock se column_exists() precisar ler a mesma tabela
for col_name, definition in columns:
    if column_exists("store_settings", col_name):
        continue
    db.session.execute(text(f"ALTER TABLE ... ADD COLUMN {col_name} {definition}"))
db.session.commit()  # lock mantido durante todo o loop

# ✅ CORRETO — commit libera o lock antes da próxima inspeção
for col_name, definition in columns:
    if column_exists("store_settings", col_name):
        continue
    db.session.execute(text(f"ALTER TABLE ... ADD COLUMN {col_name} {definition}"))
    db.session.commit()  # lock liberado imediatamente
```

**Dica de diagnóstico:** se o container trava no entrypoint sem erro visível, verifique locks no PG:
```sql
SELECT pid, state, query, wait_event_type, wait_event
FROM pg_stat_activity WHERE datname = current_database();
```
Procurar por `idle in transaction` com `ALTER TABLE` + outros processos em `Lock | relation` na mesma tabela.

### SPA servido pelo backend

Em runtime o Flask serve a SPA de `frontend/dist` (ou `FRONTEND_DIST_PATH`) via [static.py](backend/app/static.py). `backend/static/` **não** é usado e é gitignored.

## Frontend — arquitetura

Feature-based em [frontend/src/features/](frontend/src/features/). Cada feature: `components/`, `services/<feature>Api.ts`, `useCases/`, `schemas.ts`.

Features: `pedidos` (wizard criação, edição, lista, mapa entregador) · `ledger` (recebíveis) · `customers` · `leads` · `sales` · `rotas` · `entregas` · `fontes` · `integrations` (Nuvemshop) · `notifications` · `offline` · `auth` · `config`.

API client em [http.ts](frontend/src/api/http.ts) injeta JWT do Zustand. Router em [router.tsx](frontend/src/app/router.tsx) com `<RequireAuth>`.

## Convenções

- Respostas via `success_response()` / `error_response()` ([common.py](backend/app/schemas/common.py)).
- `@require_auth(roles=["admin"])` injeta `request.current_user`.
- Forms: Zod + react-hook-form ([schemas.ts](frontend/src/features/pedidos/schemas.ts)); transformações form↔API em [useCases/](frontend/src/features/pedidos/useCases/).

## Recebíveis (ver [docs/recebiveis.md](docs/recebiveis.md))

- `status_pagamento → Pago` gera CREDIT `comissao_<source>` (taxa de cartão desconta da base).
- `POST /api/ledger/generate-weekly` → CREDITs `fixo_semanal`/`almoco`/`transporte` (idempotente por `(user_id, week_ref, category)`).
- `POST /api/ledger/settle` → DEBIT `pagamento` quita CREDITs ativos.
- Regressão de status: CREDIT antigo vira `voided=true` + novo ([order_commission_lifecycle.py](backend/app/services/order_commission_lifecycle.py)).
- Entregador ganha CREDIT `taxa_entrega` ao finalizar ([delivery_credit_service.py](backend/app/services/delivery_credit_service.py)).

## Integrações (ver [docs/integrations.md](docs/integrations.md))

Padrão **outbox assíncrono** p/ Meta CAPI: request enfileira em `MetaCapiOutbox`/`MetaCapiLeadOutbox` e o `capi-worker` ([meta_capi_worker_entrypoint.py](backend/meta_capi_worker_entrypoint.py)) faz polling e envia (+ safety-net diário + payroll). Nuvemshop: webhook ACK-first, processamento em background.

## Testes

```bash
docker compose -f docker-compose.dev.yml exec backend pytest                     # tudo (502 testes)
docker compose -f docker-compose.dev.yml exec backend pytest tests/test_recebiveis.py::test_X
```

## Segredos

Nunca commitar `.env`, credenciais ou chaves. O `.env` real fica fora do git (ver `.env.example`). Em dev, o `docker-compose.dev.yml` já traz credenciais descartáveis — não coloque segredo real nele.
