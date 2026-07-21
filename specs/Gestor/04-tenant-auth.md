# Spec 04 — Resolução de tenant e autenticação

## Status de implementação

**Fase A concluída** (branch `multi-tenant`, commit `feat(auth): bind users and requests to stores`):

- `users.store_ref_id` (FK nomeada nullable, `ON DELETE RESTRICT`, indexada) + backfill `default`.
- Login carrega a `Store` do usuário; bloqueia vínculo órfão e loja inativa.
- JWT inclui `user_id`, `role`, `store_ref_id`, `store_slug` e expiração.
- Resolução central `backend/app/services/auth_context.py` (usada por `require_auth` e pelos
  decorators de `middleware.py`): confirma usuário e loja no banco, popula `g.current_store`
  e `request.current_user`. Tenant não vem de body/query/header.
- `GET/PUT /api/config/integrations` operam sobre `g.current_store`.

**Fase B concluída** (commit `feat(integrations): tenant-aware OAuth callbacks with multi-store trigger`):

- OAuth `state` assinado (HMAC) amarrado a `store_ref_id`, com provider e expiração
  (`backend/app/services/oauth_state.py`); Bling e Nuvemshop geram o state da loja no `install`
  e validam no `callback`, vinculando credencial/instalação ao tenant.
- Trigger data-driven `backend/app/services/tenancy.py` (`is_multi_store()` = >1 loja ATIVA ou
  `FORCE_MULTI_TENANT`): no modo multi-store desliga "última loja ativa" e `BLING_STORE_ID` e
  falha fechado sem state válido; single-store mantém o comportamento atual.

**Fases C e D concluídas no código.** `store_ref_id` propagado para pedidos, leads, clientes,
endereços, fontes, referências externas, auditoria e outboxes. O seletor `BLING_STORE_ID` foi
removido do fluxo operacional do worker Bling (Fase D) — a credencial agora é resolvida pelo
`store_ref_id` da linha da outbox. Pendente apenas o hardening da Fase F (`NOT NULL`, uniques
finais e remoção do fallback `.env`).

Decisões de rollout mantidas: email **unique global** (unique composto adiado); `store_ref_id`
nullable (sem `NOT NULL`); resolução de tenant na Fase A é por **vínculo do usuário**
(`store_ref_id`, com fallback para a loja `default`) — subdomínio/host/slug no login
permanecem para uma fase futura.

## Pastas afetadas

- `backend/app/models/user.py`
- `backend/app/services/auth_service.py`
- `backend/app/routes/auth.py`
- `backend/app/middleware.py`
- `frontend/src/features/auth/`

## Modelo de associação

Decisão inicial: cada usuário comum pertence a exatamente uma loja por `users.store_ref_id`. Suporte a um usuário operar múltiplas lojas exige tabela associativa e não deve ser improvisado com header livre.

Se houver necessidade de superadmin da plataforma, criar papel e fluxo explícitos separados de `admin` do lojista.

## Login

- O login resolve a loja antes de autenticar o usuário.
- Fontes possíveis, em ordem definida: subdomínio/host, slug informado no login ou vínculo único encontrado pelo usuário.
- Email deve ser único por loja, não necessariamente global, se houver contas distintas com o mesmo email.
- Enquanto o schema ainda usa email global unique, documentar essa limitação.
- Loja inativa bloqueia login mesmo com senha válida.

## JWT

Incluir claims:

- `user_id`
- `store_ref_id`
- `store_slug`
- `role`
- expiração

O backend não confia apenas nas claims para operações sensíveis: deve confirmar usuário e loja ativos quando necessário.

## Contexto da request

Middleware autenticado popula `g.current_store` e `request.current_user`.

- Tenant não vem de query string/body em rotas administrativas comuns.
- Headers de tenant só são aceitos em fluxo de superadmin explicitamente autorizado.
- Toda service chamada por uma request recebe store ou `store_ref_id` explicitamente quando o contexto não for suficiente.

## Subdomínio e proxy

- Definir domínio base configurável.
- Validar `Host` apenas após configuração correta de proxies confiáveis.
- Não confiar cegamente em `X-Forwarded-Host`.
- Ambiente local deve suportar slug no login ou host de desenvolvimento.

## Callbacks sem sessão (Fase B — ✅ concluída)

OAuth e webhooks não têm login convencional:

- OAuth `state` deve ser assinado, ter expiração e carregar store interna.
- Callback resolve loja pelo `state`, nunca pela “última loja ativa”.
- Webhook Nuvemshop resolve a integração pelo ID externo e obtém `store_ref_id` da credencial instalada.
- Bling usa credencial explicitamente ligada à loja que iniciou o fluxo.

## Pontos de atenção

- O comportamento atual que busca a Nuvemshop ativa mais recente é proibido em multi-tenant.
- `BLING_STORE_ID=default` não pode continuar como seletor global.
- Não usar variável global ou singleton mutável para tenant.
- Jobs assíncronos devem carregar tenant do próprio registro.

## Critérios de aceite

- Tokens de duas lojas têm claims diferentes.
- Usuário da loja A recebe 404/403 para recursos da loja B.
- Loja inativa não autentica nem processa novos jobs.
- OAuth callback não pode ser trocado entre lojas.
- Webhook externo resolve tenant deterministicamente.
