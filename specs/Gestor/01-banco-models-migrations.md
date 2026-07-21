# Spec 01 — Banco, models e migrations

## Status de implementação

**Fases A, B, C, D, Gate 0 e hardening fail-closed (Fase F parcial) concluídas** no branch `multi-tenant`:

- `stores`, `store_settings` e `users.store_ref_id` (Fase A) implementados com migrations
  idempotentes: `add_store_foundation.py`, `create_store_settings.py`, `add_store_ref_to_users.py`.
- `nuvemshop_stores.store_ref_id` e `bling_credentials.store_ref_id` (Fase B) como FK nullable,
  com backfill operacional concluído.
- Pedidos, leads, clientes, endereços, fontes, referências externas e auditoria (Fase C.1–C.4)
  isolados por `store_ref_id`, com filtro automático de tenant, numeração por empresa e testes
  de isolamento com duas lojas.
- Outboxes (Meta, Meta Lead, marketing, Bling) e workers (Fase D) com `store_ref_id` por linha,
  configuração resolvida por tenant, falha isolada entre lojas e política de empresa inativa.
- **Gate 0 (PostgreSQL)** concluído: migrations idempotentes em Postgres real, zero nulos/órfãos,
  teste de concorrência de `numero_pedido`, smoke de isolamento com 2 lojas e backup/restore com
  dados reais de produção.
- **Hardening fail-closed (Fase F parcial, `99e5945`)**: numeração/usuário sem tenant, PK lookups
  cross-tenant, lead público e job de taxa de entrega falham fechado em multi-store; Bling passa
  credencial por tenant explícito no service/token service.
- `NOT NULL` e uniques finais permanecem para o **restante da Fase F** (hardening).
- Total de testes: **786/786** (vs. 726 da fundação), incluindo 5 testes de workers, 4 de smoke
  PostgreSQL e 2 de concorrência de `numero_pedido`.

## Pastas afetadas

- `backend/app/models/`
- `backend/scripts/migrations/`
- `backend/entrypoint.sh`

## Identidade central

`stores` é a fonte canônica de identidade do tenant.

Campos mínimos:

- `id`: inteiro, chave primária interna.
- `name`: nome administrativo obrigatório.
- `slug`: identificador único, normalizado em minúsculas, apropriado para login e subdomínio.
- `active`: bloqueia novas sessões e processamento quando falso.
- `created_at` e `updated_at`: timestamps obrigatórios.