# AGENTS.md

Referência rápida para agentes IA trabalhando neste repositório.

---

## Stack real

- **Banco**: PostgreSQL 16 Alpine (Docker, service `db`). SQLite só como fallback em testes/dev local sem Docker (ver [docs/database.md](docs/database.md)).
- **Backend**: Flask 3 + SQLAlchemy 2, JWT seletivo via `@require_auth`.
- **Frontend**: React 19 + Vite + MUI + React Query + Zustand (auth) + Dexie (PWA offline).
- **Deploy**: Docker Compose. Comandos backend rodam via `docker compose exec backend ...`.

## Comandos canônicos

```bash
docker compose up -d
docker compose exec backend pytest
docker compose exec backend ruff check . --fix
docker compose exec backend black .
docker compose exec backend python scripts/migrations/<arquivo>.py
docker compose exec backend flask create-admin       # primeiro admin
docker compose exec backend python scripts/dump_routes.py

cd frontend && npm run dev      # Vite :5173 (dev sem Docker)
cd frontend && npm run build && npm run lint
```

---

## Backend — arquitetura

Camadas: `routes/` → `services/` → `repositories/` → `models/`. Routes validam input e chamam service; service contém lógica de negócio; repository faz queries; model é SQLAlchemy.

### Blueprints registrados ([backend/app/factory.py](backend/app/factory.py))

- `pedidos_bp` — `/api/pedidos/*`
- `rotas_bp` — `/api/pedidos/rota-otimizada` (otimização)
- `clientes_bp` — `/api/clientes/*`
- `fontes_bp` — `/api/fontes-pedido/*` e `/api/pedidos/fonte/<id>/*`
- `core_bp` — `/api/health`, `/api/cep/<cep>`, `/api/stats`, `/api/backup/status`, `/api/cleanup`, `/api/pedidos/overdue`, `/api/pedidos/<id>/distancia`, `/api/pedidos/calcular-distancias`, `/api/pedidos/<id>/calcular-taxa`, `/api/exportar-planilha-leads`
- `auth_bp` — `/api/auth/*` (JWT)
- `config_bp` — `/api/config/*` (taxa entrega, taxa cartão, meta faturamento)
- `backup_admin_bp` — `/api/admin/backup/*`
- `nuvemshop_bp` — `/api/integrations/nuvemshop/*`
- `notifications_bp` — `/api/notifications/*` (VAPID push)
- `leads_bp` — `/api/leads/*`
- `users_bp` — `/api/users/*` (CRUD + payroll + commission configs)
- `ledger_bp` — `/api/ledger/*` (recebíveis)
- `meta_gateway_bp` — `/capig/*` e `/meta-gateway/<pixel_id>/events`
- `storefront_bp` — `/storefront/*` (público, scripts Nuvemshop)
- `debug_bp` — `/api/debug/*` — **só registrado se `ENABLE_DEBUG_ENDPOINTS=true`**

Não existe mais `api_bp` legado (foi quebrado em `fontes_bp` + `core_bp` + `debug_bp`).

### Roles

`admin | vendedor | atendente | entregador | viewer` — definido em [backend/app/models/user.py:35](backend/app/models/user.py#L35). Auth global está OFF; só rotas decoradas com `@require_auth` exigem JWT.

### Money & timestamps

- `Pedido.valor` é `String` no formato BR. Use `parse_brl_money()` em [backend/app/utils/money.py](backend/app/utils/money.py).
- `LedgerEntry.amount` é `Numeric(12,2)` positivo. Sempre `float(entry.amount)` ao serializar.
- Timestamps usam `datetime_now_brazil()` (TZ `America/Sao_Paulo`). Existe duplicado em [models/pedido.py](backend/app/models/pedido.py), [models/ledger_entry.py](backend/app/models/ledger_entry.py), [models/user.py](backend/app/models/user.py).

### Migrations

Scripts Python idempotentes em [backend/scripts/migrations/](backend/scripts/migrations/) — **não** Alembic/Flask-Migrate. Template em [docs/database.md](docs/database.md). [backend/entrypoint.sh](backend/entrypoint.sh) roda os essenciais no boot do container.

## Frontend — arquitetura

Feature-based em [frontend/src/features/](frontend/src/features/). Cada feature: `components/`, `services/<feature>Api.ts`, `useCases/`, `schemas.ts`.

- `pedidos/` — wizard de criação, edição, lista, mapa do entregador
- `ledger/` — recebíveis (admin vê todos, vendedor vê próprio, entregador vê `Recebíveis Hoje`)
- `customers`, `leads`, `sales`, `rotas`, `entregas`, `fontes`, `integrations` (Nuvemshop), `notifications`, `offline`, `auth`, `config`

API client em [frontend/src/api/http.ts](frontend/src/api/http.ts) injeta JWT do Zustand auth store. Router em [frontend/src/app/router.tsx](frontend/src/app/router.tsx) com `<RequireAuth>` wrapper.

## Convenções

- Routes retornam via `success_response()` / `error_response()` de [backend/app/schemas/common.py](backend/app/schemas/common.py).
- Auth: `@require_auth(roles=["admin"])` injeta `request.current_user = {user_id, role, name, email}`.
- Frontend: validação de form com Zod, formulários do wizard em [frontend/src/features/pedidos/schemas.ts](frontend/src/features/pedidos/schemas.ts), transformações form↔API em [frontend/src/features/pedidos/useCases/](frontend/src/features/pedidos/useCases/).

## Recebíveis (resumo)

Ver detalhes em [docs/recebiveis.md](docs/recebiveis.md). Pontos chave:

- Transição `status_pagamento → Pago` chama `commission_service.generate_commission()` → CREDIT `comissao_<source>` com `pedido_id`. Taxa de cartão desconta da base.
- `POST /api/ledger/generate-weekly` cria CREDITs `fixo_semanal`, `almoco`, `transporte` para todos os vendedores ativos (idempotente por `(user_id, week_ref, category)`).
- `POST /api/ledger/settle` cria um DEBIT `pagamento` que quita todos os CREDITs ativos do usuário.
- Edição de pedido com regressão de status: CREDIT antigo vira `voided=true`, novo CREDIT criado ([order_commission_lifecycle.py](backend/app/services/order_commission_lifecycle.py)).
- Entregador ganha CREDIT `taxa_entrega` ao finalizar entrega ([delivery_credit_service.py](backend/app/services/delivery_credit_service.py)).

## Integrações (resumo)

Ver [docs/integrations.md](docs/integrations.md). Padrão **outbox assíncrono** para Meta CAPI: o request enfileira em `MetaCapiOutbox` / `MetaCapiLeadOutbox` e retorna; o serviço `capi-worker` ([backend/meta_capi_worker_entrypoint.py](backend/meta_capi_worker_entrypoint.py)) faz polling e envia em segundo plano (também roda safety-net diário + payroll).

Nuvemshop: webhook ACK-first; processamento em background; pedido importado fica pendente de agendamento manual.

## Testes

```bash
docker compose exec backend pytest                                   # tudo
docker compose exec backend pytest tests/test_recebiveis.py          # arquivo
docker compose exec backend pytest tests/test_recebiveis.py::test_X  # caso
```

502 testes na suite. Em dev local pode usar `./venv/Scripts/pytest.exe` direto no Windows.
