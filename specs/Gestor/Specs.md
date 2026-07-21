# Especificações — Multi-tenant e Integrações por Loja

## Objetivo

Transformar o `GestorDePedidosIntegrado` em uma aplicação de deploy compartilhado na qual cada loja tenha dados, usuários, pedidos, credenciais e filas isolados. As integrações que hoje dependem de valores globais no `.env` devem ser administráveis por loja em uma tela frontend, com segredos criptografados e nunca devolvidos em texto puro.

## Regra de trabalho

Estas especificações devem ser revisadas antes da continuação da implementação. Mudanças no código precisam corresponder a uma spec aprovada, ter migration idempotente e incluir testes de isolamento.

O primeiro incremento foi revisado e consolidado no commit `00c3cfb` (`feat(integrations): add per-store settings foundation`). Ele entrega a fundação de lojas, configurações cifradas e a tela administrativa para o tenant `default`, mas ainda não fornece isolamento multi-tenant de dados.

As **Fases A, B, C e D** foram entregues no branch `multi-tenant`: identidade autenticada, OAuth, domínio isolado (C.1–C.4) e workers por empresa (D) já resolvem tenant. O **Gate 0 (PostgreSQL)** também foi concluído com backup/restore de dados reais de produção, smoke de isolamento e teste de concorrência de `numero_pedido`. O **hardening fail-closed (parte da Fase F, commit `99e5945`)** também foi entregue, fechando as bordas de compatibilidade em multi-store. A próxima implementação é a **Fase E — Frontend/offline** e o **restante da Fase F — Hardening** (`NOT NULL`, uniques finais, remover fallback `.env`, cifrar token Nuvemshop, métricas/alertas). O estado consolidado fica em [08-estado-atual-e-proximos-passos.md](08-estado-atual-e-proximos-passos.md), o checklist executável das Fases C/D/F fica em [09-blueprint-fases-c-d.md](09-blueprint-fases-c-d.md) e o runbook de rollout (Fases 0–2) está em [10-rollout-fases-0-2.md](10-rollout-fases-0-2.md).

## Índice

1. [Banco, models e migrations](01-banco-models-migrations.md)
2. [Backend, criptografia e API de configurações](02-backend-configuracoes-api.md)
3. [Frontend da tela de Integrações](03-frontend-integracoes.md)
4. [Resolução de tenant e autenticação](04-tenant-auth.md)
5. [Isolamento dos dados de negócio](05-isolamento-dados.md)
6. [Workers e integrações externas](06-workers-integracoes.md)
7. [Segurança, testes, rollout e operação](07-seguranca-testes-rollout.md)
8. [Estado atual e plano de continuação](08-estado-atual-e-proximos-passos.md)
9. [Blueprint executável das Fases C, D e F](09-blueprint-fases-c-d.md)
10. [Runbook — Rollout Fases 0–2](10-rollout-fases-0-2.md)

O blueprint 09 é um checklist vivo: após cada incremento, deve registrar status, commit realizado,
testes executados e desvios aprovados. As specs 01–08 continuam sendo a referência temática e
guardam as decisões permanentes do sistema.

## Sequência proposta

1. Aprovar identidade e resolução do tenant. ✅
2. Consolidar a fundação `stores` e executar a migration em ambiente de teste. ✅
3. Criar `store_settings`, criptografia e API administrativa. ✅
4. Criar a tela de Integrações. ✅
5. Associar usuários e sessões a uma loja. ✅ (Fase A)
5.1 Resolver tenant em OAuth/callbacks sem sessão. ✅ (Fase B)
6. Propagar `store_ref_id` para dados de negócio em quatro incrementos. ✅ C.1 → C.2 → C.3 → C.4
7. Propagar tenant para filas e adaptar os workers para configuração por loja. ✅ (Fase D)
8. Gate PostgreSQL (migrations, concorrência, isolamento com 2 lojas, backup/restore). ✅ (Gate 0)
9. Hardening fail-closed das bordas de compatibilidade (numeração, PK lookups, lead público, taxa de entrega, Bling por tenant). ✅ (Fase F parcial, `99e5945`)
10. Aplicar `NOT NULL` e constraints finais numa etapa separada. ⬅ Restante da Fase F
11. Remover fallback de credenciais por loja no `.env` somente após auditoria. ⬅ Restante da Fase F

## Critério global de conclusão

- Duas lojas podem operar simultaneamente no mesmo banco sem ler, alterar ou processar dados uma da outra.
- Nenhuma credencial pertencente ao lojista depende do `.env` global.
- Segredos são cifrados em repouso e mascarados nas APIs.
- Callbacks, workers e tarefas assíncronas resolvem o tenant sem depender de estado global de request.
- Todas as queries de negócio têm escopo de tenant comprovado por testes negativos de vazamento.
- Migrations funcionam em PostgreSQL e no fallback SQLite definido pelo projeto.

## Fora do escopo inicial

- Cobrança, planos e limites comerciais do SaaS.
- Domínios personalizados por lojista.
- Envelope encryption ou KMS por loja; isso deve ser reavaliado antes de clientes externos reais.
- Transformar configurações técnicas da plataforma em configurações do lojista. `SECRET_KEY`, banco, JWT, VAPID e credenciais do app OAuth continuam no secret manager do deploy.