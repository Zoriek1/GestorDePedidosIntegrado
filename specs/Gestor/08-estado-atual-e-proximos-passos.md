# Spec 08 — Estado atual e próximos passos

## Referência da revisão

- Repositório: `GestorDePedidosIntegrado`.
- Branch: `multi-tenant`, publicada em `origin/multi-tenant`.
- Data da consolidação: 2026-07-20.
- Checklist operacional: [09-blueprint-fases-c-d.md](09-blueprint-fases-c-d.md).
- Runbook de rollout: [10-rollout-fases-0-2.md](10-rollout-fases-0-2.md).
- Próxima implementação: **Fase E — Frontend/offline por tenant** e **restante da Fase F — Hardening**.

## Conclusão executiva

**Todas as Fases A, B, C e D estão implementadas**, além do **Gate 0 (PostgreSQL)** e do
**hardening fail-closed (parte da Fase F, commit `99e5945`)**.
Usuários, autenticação, configurações, OAuth, pedidos, leads, clientes, endereços, fontes,
referências externas, notificações, auditoria e workers já resolvem a empresa correta em
todos os fluxos cobertos pelas Fases C e D; bordas de compatibilidade (numeração, PK lookups,
lead público, taxa de entrega, Bling) falham fechado em multi-store.

As Fases C + D foram entregues em cinco commits isolados:

| Incremento | Commit | Entrega |
|---|---|---|
| C.1 | `1bdf5db` | Pedidos, leads, numeração e dependências |
| C.2 | `9c6f46d` | Clientes, endereços e fontes |
| C.3 | `e893668` | Referências externas de pedidos |
| C.4 | `9b486a1` | Auditoria |
| D | `83fc747` | Outboxes e workers por empresa |

O **Gate 0 (PostgreSQL)** foi concluído nos commits `0ab107c`, `aabf6c1` e `388c773`:
migrations idempotentes em Postgres real, zero nulos/órfãos, teste de concorrência de
`numero_pedido`, smoke de isolamento com 2 lojas e backup/restore com dados reais de produção
(909 pedidos). O hardening fail-closed foi entregue em `99e5945`.

A operação multiempresa em produção ainda depende do deploy (Fase 1) e da verificação de
`store_settings` (Fase 2). O restante do hardening (Fase F) e o frontend/offline (Fase E) são os
próximos incrementos de implementação.

## Estado global

| Área | Estado | Entregue | Principal pendência |
|---|---|---|---|
| Fundação | ✅ Concluída | `stores`, `store_settings`, criptografia e configurações administrativas | Hardening final |
| Fase A — Auth | ✅ Concluída | `users.store_ref_id`, JWT e contexto de request | `NOT NULL` somente na Fase F |
| Fase B — OAuth | ✅ Concluída | State assinado e instalações/credenciais vinculadas à empresa | Remover fallbacks no hardening |
| Fase C — Domínio | ✅ Concluída | Isolamento C.1–C.4 e `numero_pedido` local, validado no Gate 0 | Hardening Fase F |
| Fase D — Workers | ✅ Concluída | Outboxes com `store_ref_id`, configuração por linha, falha isolada, `BLING_STORE_ID` removido | Rollout em produção pendente |
| Fase E — Frontend/offline | ⬜ Pendente | Identidade básica da loja no auth/cache | React Query, Dexie e service worker por tenant |
| Fase F — Hardening | 🚧 Parcial (fail-closed entregue em `99e5945`) | Fail-closed de bordas (numeração, PK lookups, lead público, taxa de entrega, Bling por tenant) | `NOT NULL`, uniques finais, remover fallback `.env`, cifrar token Nuvemshop, métricas/alertas |

## O que está consolidado

### Identidade, configuração e OAuth

- `stores` é a identidade interna da empresa; a instalação legada usa `slug='default'`.
- Usuários e JWT resolvem empresa no servidor; payloads comuns não escolhem `store_ref_id`.
- `g.current_store`, `g.tenant_store_id` e `g.tenant_multi` são resolvidos uma vez por request.
- HTTP Basic permanece compatível em single-store e falha fechado em multi-store.
- Configurações do lojista ficam em `store_settings`, com segredos cifrados e mascarados na API.
- OAuth Bling/Nuvemshop usa state assinado e vincula credencial/instalação à empresa correta.

### Domínio — Fase C

- O listener `Session.do_orm_execute` aplica `with_loader_criteria` aos models escopados.
- Multi-store lê somente a empresa atual; single-store tolera linhas `NULL` durante a transição.
- `execution_options(include_all_tenants=True)` é o escape hatch administrativo explícito.
- Pedidos usam `numero_pedido` sequencial por empresa; `id` continua sendo a PK global interna.
- Pedidos, leads e entidades dependentes recebem tenant derivado pelo servidor.
- Clientes, endereços e fontes possuem unicidade local à empresa quando aplicável.
- As tabelas dinâmicas antigas de fontes deixaram de participar dos fluxos operacionais.
- Referências externas são únicas por empresa, provedor, loja externa e pedido externo.
- Nuvemshop preserva tenant em criação, atualização, deduplicação e retry.
- Bling deriva o tenant da referência a partir do Pedido; credencial por empresa resolvida na Fase D
  e passada explicitamente por tenant no service/token service (hardening `99e5945`).
- Auditoria resolve tenant por valor explícito, entidade, request e fallback single-store.
- IDs da outra empresa se comportam como recursos inexistentes nos fluxos cobertos; lookups por PK
  usam `filter(id==...).first()` para o filtro de tenant se aplicar (hardening `99e5945`).
- O frontend exibe `numero_pedido ?? id`, mantendo `id` nos identificadores internos.

## Verificações realizadas

- Suíte backend completa: **786/786 testes aprovados** (vs. 726 da fundação).
- Testes direcionados: C.1 (135), C.2 (52), C.3 (67), C.4 (16), D/workers (5), smoke PostgreSQL (4), concorrência numero_pedido (2), hardening fail-closed (`test_tenant_auth.py`, `test_tenant_domain_c1.py`, `test_tenant_oauth.py`, `test_bling_service.py`).
- Build de produção: Vite 7.3.0, 14.819 módulos transformados.
- Novos arquivos e núcleo de tenancy aprovados no Ruff e Black.
- UTF-8 e links relativos do blueprint verificados.
- `.claude/settings.local.json` permaneceu fora dos commits.

Débitos preexistentes não incorporados às Fases C/D:

- Ruff global: 25 ocorrências.
- Black global: 62 arquivos fora do formato.
- `tsc --noEmit` global ainda falha em erros anteriores; o build Vite passa.

## Limites atuais e bloqueadores de produção

### Fase D implementada, Gate 0 concluído, hardening parcial

A Fase D, o Gate 0 (PostgreSQL) e o hardening fail-closed (Fase F parcial) já foram implementados
e validados. Os bloqueadores de produção atuais são:

- **Deploy (Fase 1):** aplicar o branch `multi-tenant` em produção com 1 loja.
- **Verificação `store_settings` (Fase 2):** confirmar que o import do `.env` para o banco
  está correto e que `uses_environment_fallback` é `false`.
- **Restante do Hardening (Fase F):** `NOT NULL`, uniques finais, remoção do fallback `.env` e
  cifrar token Nuvemshop antes de ativar a 2ª loja.
- **Frontend/offline (Fase E):** incluir tenant nas query keys, separar Dexie por tenant,
  auditar service worker.

## Plano de continuação

### Fase D — Filas e workers por empresa

> **Status: ✅ Concluída (commit `83fc747`).**

Implementado e validado. Detalhes no [blueprint](09-blueprint-fases-c-d.md) e na
[Spec 06](06-workers-integracoes.md).

### Hardening fail-closed (Fase F parcial) — concluído em `99e5945`

> **Status: ✅ Concluída.**

Fechou as bordas de compatibilidade das Fases C/D: numeração sem tenant, usuário sem loja, PK
lookups cross-tenant, lead público e job de taxa de entrega falham fechado em multi-store; Bling
passa a credencial por tenant explícito. Detalhes no [blueprint](09-blueprint-fases-c-d.md).

### Fase E — Frontend, cache e offline

1. Incluir tenant nas query keys que armazenem dados de negócio.
2. Limpar/inutilizar cache na troca de identidade e logout.
3. Separar drafts e tabelas Dexie por tenant.
4. Auditar o service worker para impedir reutilização de respostas autenticadas.
5. Adicionar testes de troca de sessão/empresa.

### Fase F — Hardening e liberação (restante)

1. Medir e zerar linhas sem tenant e FKs órfãs.
2. Aplicar `NOT NULL` e constraints finais aprovadas.
3. Remover fallback `.env` das credenciais do lojista.
4. Cifrar o token Nuvemshop.
5. Validar rotação de chaves, backup e restore.
6. Adicionar métricas e alertas por tenant.
7. Fazer revisão de segurança e liberar o modo multiempresa.

## Próximas entregas recomendadas

1. **Fase 1 — Deploy em produção com 1 loja:** aplicar o branch `multi-tenant` em produção
   seguindo o runbook [10-rollout-fases-0-2.md](10-rollout-fases-0-2.md).
2. **Fase 2 — Verificar `store_settings`:** confirmar import do `.env` e que
   `uses_environment_fallback` é `false`.
3. **Fase E — Frontend/offline:** incluir tenant nas query keys React Query, separar Dexie,
   auditar service worker.
4. **Restante da Fase F — Hardening:** `NOT NULL`, uniques finais, remover fallback `.env`, cifrar
   token Nuvemshop, métricas/alertas por tenant, revisão de segurança.