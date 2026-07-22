# Especificações — Multi-tenant e Integrações por Loja

## Objetivo

Transformar o `GestorDePedidosIntegrado` em uma aplicação de deploy compartilhado na qual cada loja tenha dados, usuários, pedidos, credenciais e filas isolados. As integrações que hoje dependem de valores globais no `.env` devem ser administráveis por loja em uma tela frontend, com segredos criptografados e nunca devolvidos em texto puro.

## Regra de trabalho

Estas especificações devem ser revisadas antes da continuação da implementação. Mudanças no código precisam corresponder a uma spec aprovada, ter migration idempotente e incluir testes de isolamento.

O primeiro incremento foi revisado e consolidado no commit `00c3cfb` (`feat(integrations): add per-store settings foundation`). Ele entrega a fundação de lojas, configurações cifradas e a tela administrativa para o tenant `default`, mas ainda não fornece isolamento multi-tenant de dados.

As **Fases A, B, C, D, E e F** foram entregues no branch `multi-tenant`: identidade autenticada, OAuth, domínio isolado (C.1–C.4), workers por empresa (D), hardening (F), frontend/offline por tenant (E), validação de integrações e grid de UI. O **Gate 0 (PostgreSQL)** também foi concluído com backup/restore de dados reais de produção, smoke de isolamento e teste de concorrência de `numero_pedido`.

**Status 2026-07-22.** A implementação das fases A–F segue completa, mas a revisão de 22/07 encontrou quatro defeitos que só se manifestam a partir da **segunda loja** — corrigidos em `ae78c4e`..`a5e3e9c` e detalhados no topo de [11-proximos-passos.md](11-proximos-passos.md). Resta uma lacuna que bloqueia a operação multiempresa: **leads públicos ainda caem sempre na loja `default`** (§6 do spec 11).

A próxima ação continua sendo o **deploy em produção com 1 loja** (Fase 1 do runbook [10-rollout-fases-0-2.md](10-rollout-fases-0-2.md)), seguido da verificação de `store_settings` (Fase 2). Ver [08-estado-atual-e-proximos-passos.md](08-estado-atual-e-proximos-passos.md) para o panorama completo e [11-proximos-passos.md](11-proximos-passos.md) para o roadmap.

> **Regra aprendida em 22/07:** trabalho multi-tenant não pode ser dado como concluído com testes de uma loja só — todos os quatro defeitos passavam na suíte de 786 testes. `backend/tests/test_tenant_isolation.py`, que exercita duas lojas, é o piso mínimo para novos incrementos.

## Índice

1. [Banco, models e migrations](01-banco-models-migrations.md)
2. [Backend, criptografia e API de configurações](02-backend-configuracoes-api.md)
3. [Frontend da tela de Integrações](03-frontend-integracoes.md)
4. [Resolução de tenant e autenticação](04-tenant-auth.md)
5. [Isolamento dos dados de negócio](05-isolamento-dados.md)
6. [Workers e integrações externas](06-workers-integracoes.md)
7. [Segurança, testes, rollout e operação](07-seguranca-testes-rollout.md)
8. [Estado atual e plano de continuação](08-estado-atual-e-proximos-passos.md)
9. [Blueprint executável das Fases C, D, E e F](09-blueprint-fases-c-d.md)
10. [Runbook — Rollout Fases 0–2](10-rollout-fases-0-2.md)
11. [Próximos passos — roadmap pós-implementação](11-proximos-passos.md)

O blueprint 09 é um checklist vivo: após cada incremento, deve registrar status, commit realizado,
testes executados e desvios aprovados. As specs 01–08 continuam sendo a referência temática e
guardam as decisões permanentes do sistema.

## Sequência concluída

1. Aprovar identidade e resolução do tenant. ✅
2. Consolidar a fundação `stores` e executar a migration em ambiente de teste. ✅
3. Criar `store_settings`, criptografia e API administrativa. ✅
4. Criar a tela de Integrações. ✅
5. Associar usuários e sessões a uma loja. ✅ (Fase A)
5.1 Resolver tenant em OAuth/callbacks sem sessão. ✅ (Fase B)
6. Propagar `store_ref_id` para dados de negócio em quatro incrementos. ✅ C.1 → C.2 → C.3 → C.4
7. Propagar tenant para filas e adaptar os workers para configuração por loja. ✅ (Fase D)
8. Gate PostgreSQL (migrations, concorrência, isolamento com 2 lojas, backup/restore). ✅ (Gate 0)
9. Hardening fail-closed das bordas de compatibilidade. ✅ (Fase F parcial, `99e5945`)
10. Frontend/offline por tenant (React Query keys, Dexie, cache purge). ✅ (Fase E, `8c4747f`)
11. Hardening final (NOT NULL 19 tabelas, env fallback flag, Nuvemshop token criptografado). ✅ (Fase F restante, `dccfdee`)
12. Validação de integrações (dispatcher por canal, IntegrationValidationLog, UI grid). ✅
13. Correção das lacunas de 2ª loja: `store_ref_id` nos diagnósticos/dispatcher, índice de nome por loja, tenant resolvido no login por `stores.email_domain`, `flask cli create-store`, `default_store()` fail-closed. ✅ (`ae78c4e`..`a5e3e9c`)
14. Consolidação da aba Integrações em card + modais. ✅ (`181350c`)
15. Deploy em produção com 1 loja. ⬅ Próxima ação
16. Verificar `store_settings` e `uses_environment_fallback = false`. ⬅ Após deploy
17. Mapear leads públicos → loja (hoje sempre `default`). ⬅ Bloqueia a 2ª loja se ela captar leads
18. Ativar 2ª loja via `flask cli create-store` — `is_multi_store()` liga sozinho, sem flag. ⬅ Após verificação
19. Métricas/alertas por tenant, rate limit por tenant, `tsc --noEmit`. ⬅ Roadmap

## Critério global de conclusão

- Duas lojas podem operar simultaneamente no mesmo banco sem ler, alterar ou processar dados uma da outra.
- Nenhuma credencial pertencente ao lojista depende do `.env` global.
- Segredos são cifrados em repouso e mascarados nas APIs.
- Callbacks, workers e tarefas assíncronas resolvem o tenant sem depender de estado global de request.
- Todas as queries de negócio têm escopo de tenant comprovado por testes negativos de vazamento.
- Frontend escopa cache, queries e armazenamento offline por tenant.
- Migrations funcionam em PostgreSQL e no fallback SQLite definido pelo projeto.

## Fora do escopo inicial

- Cobrança, planos e limites comerciais do SaaS.
- Domínios personalizados por lojista.
- Envelope encryption ou KMS por loja; isso deve ser reavaliado antes de clientes externos reais.
- Transformar configurações técnicas da plataforma em configurações do lojista. `SECRET_KEY`, banco, JWT, VAPID e credenciais do app OAuth continuam no secret manager do deploy.