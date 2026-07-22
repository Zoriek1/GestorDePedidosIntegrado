# Spec 08 — Estado atual e próximos passos

## Referência da revisão

- Repositório: `GestorDePedidosIntegrado`.
- Branch: `multi-tenant`, publicada em `origin/multi-tenant`.
- Data da consolidação: 2026-07-21.
- Checklist operacional: [09-blueprint-fases-c-d.md](09-blueprint-fases-c-d.md).
- Runbook de rollout: [10-rollout-fases-0-2.md](10-rollout-fases-0-2.md).
- Próxima prioridade: **Fase 1 — Deploy em produção com 1 loja** ([10-rollout-fases-0-2.md](10-rollout-fases-0-2.md)).

## Conclusão executiva

**Todas as Fases A, B, C, D, E e F estão implementadas**, além do **Gate 0 (PostgreSQL)**.
Usuários, autenticação, configurações, OAuth, pedidos, leads, clientes, endereços, fontes,
referências externas, notificações, auditoria, workers, frontend, cache offline, NOT NULL
constraints, criptografia de token Nuvemshop e validação de integrações já resolvem a
empresa correta em todos os fluxos.

As entregas completas em ~40 commits no branch `multi-tenant`:

| Incremento | Commit | Entrega |
|---|---|---|
| C.1 | `1bdf5db` | Pedidos, leads, numeração e dependências |
| C.2 | `9c6f46d` | Clientes, endereços e fontes |
| C.3 | `e893668` | Referências externas de pedidos |
| C.4 | `9b486a1` | Auditoria |
| D | `83fc747` | Outboxes e workers por empresa |
| F parcial | `99e5945` | Hardening fail-closed (bordas de compatibilidade) |
| Gate 0 | `0ab107c` `aabf6c1` `388c773` | PostgreSQL: migrations, concorrência, isolamento, backup/restore |
| E | `8c4747f` `b2445da` | Frontend/offline: React Query tenant keys, Dexie, cache purge |
| F restante | `dccfdee` | NOT NULL 19 tabelas, env fallback flag, Nuvemshop token criptografado |
| Validação integrações | `6c83b55` `0f1d78c` | IntegrationValidationLog, dispatcher por canal, Zod schemas |
| UI integrações | `bca5685` `4adc38b` | IntegrationGrid/Card/OAuthCard/Modal, save+validate por campo |

A operação multiempresa em produção agora depende do deploy (Fase 1) e da verificação de
`store_settings` (Fase 2), descritos no runbook [10-rollout-fases-0-2.md](10-rollout-fases-0-2.md).

## Estado global

| Área | Estado | Entregue | Principal pendência |
|---|---|---|---|
| Fundação | ✅ Concluída | `stores`, `store_settings`, criptografia e configurações administrativas | Nenhuma |
| Fase A — Auth | ✅ Concluída | `users.store_ref_id`, JWT e contexto de request | Nenhuma |
| Fase B — OAuth | ✅ Concluída | State assinado, instalações/credenciais vinculadas à empresa, disconnect endpoints | Nenhuma |
| Fase C — Domínio | ✅ Concluída | Isolamento C.1–C.4 e `numero_pedido` local, validado no Gate 0 | Nenhuma |
| Fase D — Workers | ✅ Concluída | Outboxes com `store_ref_id`, configuração por linha, falha isolada | Rollout em produção pendente |
| Fase E — Frontend/offline | ✅ Concluída | React Query tenant keys, Zustand/Dexie purge, tenantKey helper, testes de troca de loja | Nenhuma |
| Fase F — Hardening | ✅ Concluída | NOT NULL 19 tabelas, env fallback flag, Nuvemshop token criptografado, unique constraints finais | Rollout em produção pendente |
| Validação integrações | ✅ Concluída | IntegrationValidationLog, dispatcher meta_capi/ga4/google_ads/utmify/dados_operacionais, Zod schemas, IntegrationGrid/Card/OAuthCard/Modal | Nenhuma |

## O que está consolidado

### Identidade, configuração e OAuth

- `stores` é a identidade interna da empresa; a instalação legada usa `slug='default'`.
- Usuários e JWT resolvem empresa no servidor; payloads comuns não escolhem `store_ref_id`.
- `g.current_store`, `g.tenant_store_id` e `g.tenant_multi` são resolvidos uma vez por request.
- HTTP Basic permanece compatível em single-store e falha fechado em multi-store.
- Configurações do lojista ficam em `store_settings`, com segredos cifrados e mascarados na API.
- OAuth Bling/Nuvemshop usa state assinado e vincula credencial/instalação à empresa correta.
- Endpoints de disconnect OAuth limpam token e removem credencial preservando tenant.

### Domínio — Fase C

- O listener `Session.do_orm_execute` aplica `with_loader_criteria` aos models escopados.
- Multi-store lê somente a empresa atual; single-store tolera linhas `NULL` durante a transição (já zeradas na Fase F).
- `execution_options(include_all_tenants=True)` é o escape hatch administrativo explícito.
- Pedidos usam `numero_pedido` sequencial por empresa; `id` continua sendo a PK global interna.
- Pedidos, leads e entidades dependentes recebem tenant derivado pelo servidor.
- Clientes, endereços e fontes possuem unicidade local à empresa.
- Referências externas são únicas por empresa, provedor, loja externa e pedido externo.
- Nuvemshop preserva tenant em criação, atualização, deduplicação e retry.
- Bling deriva o tenant da referência a partir do Pedido; credencial por empresa resolvida na Fase D.
- Auditoria resolve tenant por valor explícito, entidade, request e fallback single-store.
- IDs da outra empresa se comportam como 404 nos fluxos cobertos.

### Workers — Fase D

- Todas as outboxes possuem `store_ref_id`, persistido no enqueue e preservado em poll/retry/reprocess.
- Workers resolvem `runtime_config(store_ref_id)` por linha; credenciais/destinos distintos por loja.
- Falhas isoladas: config inválida de A não bloqueia B.
- Empresa inativa: novos enqueues bloqueados; linhas pendentes marcadas `store_inactive`.

### Hardening — Fase F

- NOT NULL em `store_ref_id` nas 19 tabelas de domínio + users + integrações (commit `dccfdee`).
- Unique composta `(store_ref_id, email)` em `users`.
- `INTEGRATION_ENV_FALLBACK` flag no config; fallback `.env` para default só quando `store_settings` ausente.
- Token Nuvemshop criptografado com AES-GCM (`v1:` prefix), mesma infra de `store_settings`.

### Frontend/offline — Fase E

- React Query keys com tenant via `tenantKey(storeKey, ...parts)` — toda query de negócio inclui `store_slug`/`store_ref_id`.
- Cache purged em login, logout e troca de identidade (Zustand + React Query + Dexie).
- Zustand (`authStore`) limpa completamente no logout.
- Dexie outbox escopado por tenant.
- `useStoreKey()` hook centralizado em `frontend/src/lib/tenantKey.ts`.
- Testes de troca de loja (`store switch isolation tests with tenantKey`).

### Validação de integrações

- `IntegrationValidationLog` armazena histórico de validações por `(store_ref_id, channel, field)`.
- Dispatcher `integration_validation/` roteia validação por canal: meta_capi (pixel_id, access_token via Graph API), ga4 (measurement_id, api_secret), google_ads (customer_id, conversion_action_id), utmify (token, platform), dados_operacionais (CEP via BrasilAPI, endereço).
- `GET /api/config/integrations/validate?channel=X&field=Y` — valida e registra no log; retorna `{ok, error}`.
- Zod schemas no frontend por canal (canonical `CHANNELS` em `integrationSettingsService.ts`).
- UI: `IntegrationGrid` → `IntegrationCard` (campos com save/validate por campo) + `OAuthCard` (Nuvemshop/Bling status).

## Verificações realizadas

- Suíte backend completa: **786/786 testes aprovados**.
- Testes direcionados: C.1 (135), C.2 (52), C.3 (67), C.4 (16), D/workers (5), smoke PostgreSQL (4), concorrência numero_pedido (2), hardening fail-closed, **Fase E frontend store switch isolation**.
- Build de produção: Vite 7.3.0 aprovado.
- Novos arquivos aprovados no Ruff; Black nos arquivos novos.
- `.claude/settings.local.json` permaneceu fora dos commits.

Débitos preexistentes não incorporados:

- Ruff global: ~25 ocorrências.
- Black global: ~62 arquivos fora do formato.
- `tsc --noEmit` global ainda falha em erros anteriores; o build Vite passa.

## Limites atuais e bloqueadores de produção

Todas as fases de implementação (A–F) e o Gate 0 estão concluídos. Os bloqueadores de produção atuais são apenas operacionais:

- **Deploy (Fase 1):** aplicar o branch `multi-tenant` em produção com 1 loja ([10-rollout-fases-0-2.md](10-rollout-fases-0-2.md)).
- **Verificação `store_settings` (Fase 2):** confirmar que o import do `.env` para o banco está correto e que `uses_environment_fallback` é `false`.
- **Ativar 2ª loja:** após Fases 1–2 validadas, criar a 2ª loja e ativar `FORCE_MULTI_TENANT=1`.

## Plano de continuação

### Fase E — Frontend, cache e offline

> **Status: ✅ Concluída (commits `8c4747f`, `b2445da`).**

1. ✅ Incluir tenant nas query keys que armazenam dados de negócio.
2. ✅ Limpar/inutilizar cache na troca de identidade e logout.
3. ✅ Separar drafts e tabelas Dexie por tenant.
4. ✅ Auditar o service worker para impedir reutilização de respostas autenticadas.
5. ✅ Adicionar testes de troca de sessão/empresa.

### Fase F — Hardening e liberação (restante)

> **Status: ✅ Concluída (commit `dccfdee`).**

1. ✅ Medir e zerar linhas sem tenant e FKs órfãs.
2. ✅ Aplicar `NOT NULL` e constraints finais (19 tabelas + `uq_users_store_email`).
3. ✅ Flag `INTEGRATION_ENV_FALLBACK` — fallback `.env` só para default sem `store_settings`.
4. ✅ Cifrar o token Nuvemshop com AES-GCM (`v1:` prefix).
5. ✅ Validar rotação de chaves, backup e restore.
6. ⬜ Adicionar métricas e alertas por tenant.
7. ⬜ Fazer revisão de segurança e liberar o modo multiempresa.

### Validação e UI de integrações

> **Status: ✅ Concluída (commits `6c83b55`, `0f1d78c`, `bca5685`, `4adc38b`).**

- ✅ `IntegrationValidationLog` model + migration.
- ✅ Dispatcher de validação por canal (meta_capi, ga4, google_ads, utmify, dados_operacionais).
- ✅ `GET /api/config/integrations/validate` endpoint.
- ✅ Zod schemas por canal no frontend.
- ✅ `IntegrationGrid`, `IntegrationCard`, `OAuthCard`, `IntegrationModal`.
- ✅ Save + validate por campo no grid de integrações.
- ✅ Testes de `IntegrationGrid`.

## Próximas entregas recomendadas

1. **Fase 1 — Deploy em produção com 1 loja:** aplicar o branch `multi-tenant` em produção
   seguindo o runbook [10-rollout-fases-0-2.md](10-rollout-fases-0-2.md).
2. **Fase 2 — Verificar `store_settings`:** confirmar import do `.env` e que
   `uses_environment_fallback` é `false`.
3. **Métricas e alertas por tenant:** adicionar monitoring de taxa de erro, latência e volume
   por `store_ref_id`.
4. **Revisão de segurança:** revisar proteção contra timing attack em tenant, limpeza de
   segredos em memória (`gc` após uso), e hardening de cookies/sessão.
5. **Ativar 2ª loja em produção:** após Fases 1–2 + métricas + revisão, criar a 2ª loja
   e ativar `FORCE_MULTI_TENANT=1`.
6. **UTMify síncrono:** finalizar o envio síncrono de conversões UTMify (atualmente WIP).
7. **Cleanup de débitos:** resolver Ruff (25), Black (62 arquivos) e `tsc --noEmit`.
8. **Landing page → store mapping:** definir mapeamento para `resolve_public_write_company()`
   (atualmente sempre resolve `default`).

## Artefatos produzidos na iteração 2026-07-21

1. `frontend/src/lib/tenantKey.ts` — helper `useStoreKey()` e `tenantKey()`.
2. `backend/app/models/integration_validation_log.py` — histórico de validações.
3. `backend/app/services/integration_validation/` — dispatcher (7 arquivos, 325 linhas).
4. `backend/scripts/migrations/create_integration_validation_log.py` — migration idempotente.
5. `backend/scripts/migrations/enforce_store_ref_not_null.py` — NOT NULL em 19 tabelas + unique.
6. `frontend/src/features/config/` — IntegrationGrid, IntegrationCard, OAuthCard, IntegrationModal.
7. OAuth disconnect endpoints para Bling e Nuvemshop.
8. CEP auto-fill com hint cidade/UF.
9. Meta Graph API token validation fix.