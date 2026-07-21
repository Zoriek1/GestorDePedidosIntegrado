# Brief do Grupo 1: Middleware de Métricas (3.1) + Health Endpoint (3.2)

## Tarefa 3.1 — Instrumentar taxa de erro por tenant no middleware existente

**Contexto:** O `setup_security_middleware` em `backend/app/middleware.py` já possui um `after_request` que loga latência. Falta incluir `store_ref_id` nos logs estruturados.

**O que fazer:**
- No handler `after_request` dentro de `setup_security_middleware()` em `backend/app/middleware.py`:
  - Adicionar `store_ref_id` ao log estruturado de produção (linha 734-741, o logger `request_timing`)
  - Usar `getattr(g, 'tenant_store_id', None)` para obter o ID da loja
  - Formato: incluir como extra data ou no formato da mensagem
  - Garantir que funciona tanto em single-store (None) quanto multi-store

**Importante:**
- O logger `request_timing` já existe em produção (linha 734)
- `g.tenant_store_id` é populado por `prime_request_tenant()` ou `load_request_identity()`
- Não quebrar o log de dev (linhas 726-731)
- Manter o log de acesso em arquivo (linhas 743-751)

## Tarefa 3.2 — Criar health endpoint por tenant (admin only)

**Contexto:** Já existe `GET /api/admin/debug/tenant-health` em `backend/app/routes/admin.py` que usa raw SQL. Precisamos criar **outro** endpoint ou aprimorar o existente com métricas por loja usando SQLAlchemy models.

**O que fazer:**
- Adicionar **novo** endpoint: `GET /api/admin/tenant-health` no mesmo `admin.py`
- Usar `@require_auth(roles=['admin'])` do `backend/app/decorators/auth_decorator.py`
- Retornar por loja ativa:
  - store_id, slug, name
  - pedidos_hoje (pedidos criados hoje para esta loja)
  - outbox_pendente (MetaCapiOutbox com status pending para esta loja)
- Usar SQLAlchemy model queries, NÃO raw SQL
- Exemplo de resposta:
  ```json
  {
    "stores": [
      {
        "store_id": "uuid",
        "slug": "loja-1",
        "name": "Loja 1",
        "pedidos_hoje": 42,
        "outbox_pendente": 3
      }
    ]
  }
  ```

**Models disponíveis:**
- `Store` em `backend/app/models/store.py` — campos: `id`, `slug`, `name`, `active`
- `Pedido` em `backend/app/models/pedido.py` — campo `store_ref_id`
- `MetaCapiOutbox` em `backend/app/models/meta_capi_outbox.py` — campos `store_ref_id`, `status`

**Arquivos que serão criados/modificados:**
- Modificar: `backend/app/middleware.py` (Tarefa 3.1)
- Modificar: `backend/app/routes/admin.py` (Tarefa 3.2)
- (Opcional) Testes em `backend/tests/`

**Padrões do código:**
- `from app import db` para acesso ao banco
- `db.session.query(Model).filter(...)` para queries
- `datetime_now_brazil()` para timestamps Brazil TZ (de `app.utils.time`)
- `success_response()` / `error_response()` de `app.schemas.common`