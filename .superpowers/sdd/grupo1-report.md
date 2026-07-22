# Relatório do Grupo 1 — Tarefas 3.1 + 3.2

## Status: DONE

## Commits

```
9220704 feat(tenant): add store_ref_id to middleware logs and create admin tenant-health endpoint
```

## O que foi implementado

### Tarefa 3.1 — store_ref_id no middleware de logging

**Arquivo:** `backend/app/middleware.py`

- No handler `after_request` (dentro de `setup_security_middleware`), no bloco de produção (logger `request_timing`):
  - Adicionado `store_ref_id = getattr(g, "tenant_store_id", None)` 
  - Incluído no formato da mensagem como `[store=%s]`
  - Incluído como `extra={"store_ref_id": store_ref_id}` para processadores de log estruturado
  - Funciona com `None` (single-store) e com valor inteiro (multi-store)
  - Log de dev (`FLASK_ENV=development`) permanece inalterado
  - Log de acesso em arquivo permanece inalterado

### Tarefa 3.2 — Health endpoint por tenant (admin only)

**Arquivo:** `backend/app/routes/admin.py`

- Novo endpoint: `GET /api/admin/tenant-health`
- Decorado com `@require_auth(roles=["admin"])` do `backend/app/decorators/auth_decorator.py` (JWT)
- Usa exclusivamente SQLAlchemy model queries (nada de raw SQL como o endpoint `/debug/tenant-health` existente)
- Para cada `Store` ativa, retorna:
  - `store_id`, `slug`, `name`
  - `pedidos_hoje`: contagem de `Pedido` com `created_at >= today_start` (Brasil timezone)
  - `outbox_pendente`: contagem de `MetaCapiOutbox` com `status == 'PENDING'`
- Usa `.execution_options(include_all_tenants=True)` para bypassar o `TenantScoped` filter global e permitir que um admin veja métricas de todas as lojas
- Formato de resposta:
  ```json
  {"success": true, "stores": [{store_id, slug, name, pedidos_hoje, outbox_pendente}, ...]}
  ```

### Testes

**Arquivo:** `backend/tests/test_tenant_health.py` (7 testes, todos passando)

- **Middleware (Tarefa 3.1):**
  - `test_middleware_logs_store_ref_id_in_production` — verifica que o log contém `[store=<id>]` e `extra['store_ref_id'] == store.id`
  - `test_middleware_logs_store_ref_id_none_when_unset` — verifica que `[store=None]` aparece quando não há tenant

- **Health endpoint (Tarefa 3.2):**
  - `test_tenant_health_requires_jwt` — 401 sem token
  - `test_tenant_health_requires_admin_role` — 403 para role não-admin
  - `test_tenant_health_returns_only_active_stores` — lojas inativas excluídas
  - `test_tenant_health_returns_metrics` — contagens corretas de pedidos_hoje (incluindo filtro de data) e outbox_pendente (apenas PENDING)
  - `test_tenant_health_bypasses_tenant_scope` — admin de loja A vê dados de loja B (bypass do TenantScoped)

### Testes relacionados (regressão)

- `tests/test_api.py` — 2/2 passando
- `tests/test_tenant_auth.py` — 12/12 passando
- `tests/test_store_foundation.py` — 5/5 passando
- **Total da suite parcial: 28/28 passando**

## Arquivos modificados

| Arquivo | Mudança |
|---------|---------|
| `backend/app/middleware.py` | +5 linhas: `store_ref_id` no log de produção |
| `backend/app/routes/admin.py` | +46 linhas: novo endpoint + imports |
| `backend/tests/test_tenant_health.py` | Novo arquivo, 190 linhas, 7 testes |

## Self-review

### Pontos fortes
- Segue padrões existentes (`from app import db`, `db.session.query(Model).filter(...)`, `datetime_now_brazil()`)
- Endpoint usa autenticação JWT (`@require_auth`), consistente com o módulo Recebíveis
- Middleware não quebra log de dev nem log de acesso em arquivo
- Queries usam `include_all_tenants=True` para evitar o filtro automático do `TenantScoped`
- Testes cobrem casos de borda: sem tenant, loja inativa, role não-admin, bypass de escopo

### Pontos de atenção
- O endpoint não inclui paginação — adequado para dezenas de lojas, mas se houver centenas pode precisar no futuro
- `pedidos_hoje` usa `created_at >= today_start` com timezone Brasil — correto para o fuso do sistema
- O filtro `include_all_tenants=True` é necessário para que o admin veja dados de todas as lojas; sem ele, o `TenantScoped` filter global restringiria à loja do admin autenticado

## Issues / Concerns

Nenhuma. Ambas as tarefas foram implementadas conforme especificado, testadas e passando.
