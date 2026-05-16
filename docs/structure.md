# Estrutura do Projeto

Monorepo com 4 áreas de topo. Mantenha cada uma no seu propósito — não misture código de aplicação com config de deploy, não espalhe docs.

```sh
.
├── backend/          # Flask API (Python 3.11)
├── frontend/         # React 19 + Vite (PWA)
├── docs/             # Documentação curta e verdadeira (4 arquivos + este)
├── deploy/           # Exemplos de config para reverse proxy / systemd
├── docker/           # prebuilt-dist (artefato de CI) — Dockerfile + compose ficam na raiz
└── .github/workflows # CI (backend + frontend + deploy condicional)
```

---

## Backend ([backend/app/](../backend/app/))

Camadas em pirâmide. Cada nível só conhece o de baixo. **Routes → Services → Repositories → Models.**

```sh
backend/app
├── factory.py         # create_app(): registra blueprints, db, CORS, middleware
├── config.py          # BaseConfig (env vars)
├── extensions.py      # init_db, PRAGMAs SQLite, etc.
├── cors.py, errors.py, middleware.py, static.py, cli.py
│
├── routes/            # Camada HTTP (Blueprints Flask)
├── services/          # Lógica de negócio (não toca request/response)
├── repositories/      # Queries SQLAlchemy isoladas
├── models/            # SQLAlchemy ORM (uma classe por tabela)
├── schemas/           # success_response/error_response + DTOs
│
├── decorators/        # @require_auth
├── integrations/      # Wrappers de APIs externas (Nuvemshop)
├── commands/          # Click CLI commands (flask create-admin, etc.)
├── openapi/           # Swagger blueprints
└── utils/             # money parsing, date, audit logger, etc.
```

### Fluxo padrão de um endpoint

```python
# routes/pedidos.py
@pedidos_bp.route("/<int:pedido_id>/status", methods=["PUT"])
@require_auth(roles=["admin", "vendedor", "atendente"])
def atualizar_status(pedido_id):
    data = request.get_json()
    pedido = pedido_repository.atualizar_status(pedido_id, data["status_pagamento"])
    return success_response(pedido.to_dict())
```

- **routes/** valida input, chama service ou repository, formata resposta. Nada de SQL aqui.
- **services/** orquestra (commission_service combina ledger + taxa_cartao + user). Não retorna `Response`, retorna objetos puros.
- **repositories/** encapsula queries (`Pedido.query.filter(...)`). Funções stateless que recebem `db.session` implicitamente.
- **models/** define schema. Inclui `to_dict()` e helpers de timezone, nada de business logic.

### Blueprints (todos em [routes/](../backend/app/routes/))

`pedidos_bp`, `rotas_bp`, `clientes_bp`, `fontes_bp`, `core_bp`, `auth_bp`, `config_bp`, `backup_admin_bp`, `nuvemshop_bp`, `notifications_bp`, `leads_bp`, `users_bp`, `ledger_bp`, `meta_gateway_bp`, `storefront_bp`, `debug_bp` (gated). Registrados em [factory.py](../backend/app/factory.py).

**Regra**: um blueprint por arquivo na raiz de `routes/`. Sem subpastas com 1 arquivo. Se um blueprint cresce demais (>2000 linhas), quebra em vários blueprints, não em uma pasta com submódulos.

### Migrations e dados de runtime

- Migrações: scripts Python idempotentes em [backend/scripts/migrations/](../backend/scripts/migrations/). Não usamos Flask-Migrate.
- Runtime data: `backend/instance/` (logs, backups, locks). Não versionado.
- Credenciais Google: `backend/user/config/` (gitignored).

---

## Frontend ([frontend/src/](../frontend/src/))

**Feature-based.** Cada feature é uma fatia vertical do produto e dona do próprio `components`, `services`, `useCases`, `schemas`.

```sh
frontend/src
├── main.tsx           # entry point
├── App.tsx, App.css, index.css
│
├── app/               # Bootstrap da aplicação
│   ├── App.tsx
│   ├── providers.tsx  # QueryClient, MUI theme, Confirm/Toast, Offline
│   └── router.tsx     # React Router v6 + <RequireAuth>
│
├── layout/            # AppShell (header + nav + speed dial)
│
├── features/          # Fatias verticais — onde fica 90% do código
│   ├── auth/
│   ├── pedidos/
│   ├── ledger/
│   ├── customers/, leads/, sales/, rotas/, entregas/,
│   ├── fontes/, integrations/, notifications/, offline/
│   ├── config/, users/
│
├── api/               # HTTP client + endpoints compartilhados
│   ├── http.ts        # axios + JWT interceptor
│   └── endpoints/     # pedidos.ts, customers.ts, leads.ts...
│
├── components/        # Componentes genéricos (não pertencem a uma feature)
│   ├── common/        # AppButton, Loading, ErrorState, CopyOnClick
│   ├── form/          # CepInput, CurrencyInput, PhoneInput
│   ├── system/        # ConfirmProvider, ToastProvider
│   └── uiverse/       # Componentes adaptados de uiverse.io
│
├── hooks/             # Hooks reusáveis (useAnimateOnMount, useDebouncedValue)
├── lib/               # Libs configuradas (format/, http/, offline/, logger)
├── types/             # Types globais (declaration files de libs)
├── assets/            # Static
└── test/              # Setup do Vitest
```

### Anatomia de uma feature

```sh
features/pedidos
├── OrdersPage.tsx          # Page (montada pelo router)
├── CreateOrderPage.tsx
├── CreateOrderWizard.tsx
├── EditOrderPage.tsx
├── OrderDetailsPage.tsx
├── schemas.ts              # Zod (pedidoFormSchema) + tipos de form
├── components/             # Sub-componentes da feature
│   ├── OrderCard.tsx
│   ├── OrderList.tsx
│   ├── PedidoWizard/...
│   └── WizardSteps/...
├── useCases/               # Lógica complexa não-trivial (não é só state)
│   ├── orderMapping.ts     # API → Form
│   ├── orderToForm.ts      # Reverso, para edição
│   └── cepLookup.ts
├── services/               # Quando precisa de service no client (raro)
├── contexts/               # React context restrito à feature
├── utils/                  # Pure functions (dateGrouping, quickEntryParser)
└── __tests__/              # Vitest, co-localizado
```

Nem toda feature tem todas as pastas. `leads/` hoje é uma página só. `pedidos/` é a maior, com wizard + edição + lista + detalhes.

### Cliente de API

- Chamadas concentradas em [src/api/endpoints/](../frontend/src/api/endpoints/) quando o recurso é compartilhado entre features (ex: `customers.ts` usado por `customers/` e `pedidos/`).
- Service específico da feature vai em `features/<X>/services/<X>Api.ts` (ex: [ledger/services/ledgerApi.ts](../frontend/src/features/ledger/services/ledgerApi.ts)).
- Sempre passar por [api/http.ts](../frontend/src/api/http.ts) — ele injeta JWT do `authStore` (Zustand) e trata 401.

### State

- **Server state**: React Query. Hooks `useXxx` exportados pelos services.
- **Auth**: Zustand store em [features/auth/authStore.tsx](../frontend/src/features/auth/authStore.tsx).
- **Offline outbox**: Dexie via [lib/offline/](../frontend/src/lib/offline/).
- **Form state**: react-hook-form + Zod schemas em `features/<X>/schemas.ts`.

Sem store global de domínio. Se uma feature precisa de state compartilhado entre componentes, use React Context dentro da feature (ex: [pedidos/contexts/OrderFormContext.tsx](../frontend/src/features/pedidos/contexts/OrderFormContext.tsx)).

---

## Regras de import

### Cross-feature: evitar

Uma feature **não deve** importar de outra. Se `pedidos/` precisa de algo de `customers/`, ou:

1. O recurso é genérico → sobe para `components/` ou `lib/`.
2. É um endpoint compartilhado → vive em `api/endpoints/`.
3. É uma composição → faça no nível do `app/router.tsx` ou em uma page que combine os dois.

Exceção atual (aceita): `useUsers` de [features/users/services/userApi.ts](../frontend/src/features/users/services/userApi.ts) é usado em `pedidos/`, `sales/` e `config/` para listar vendedores em selects. É um caso de "endpoint compartilhado" que faria mais sentido em `api/endpoints/users.ts` — refatoração futura.

### Direção unidirecional

```
shared (components, lib, hooks, types, api) ──► features ──► app
```

- `app/` pode importar de qualquer lugar.
- `features/` podem importar de `shared/`, nunca de `app/` ou de outra feature.
- `shared/` não importa de feature nem de app.

### Imports

- Use paths relativos curtos para imports na mesma feature (`./components/OrderCard`).
- Use absolutos a partir de `src/` quando atravessar áreas (`../../components/common/Loading`). Vite resolve relativos; não há alias `@/` configurado.
- **Não use barrel files** (`index.ts` re-exportando tudo). Quebra tree-shaking do Vite e cria ciclos. Importe direto do arquivo.

---

## Onde colocar uma coisa nova

| Tipo | Lugar |
|---|---|
| Nova rota HTTP de domínio existente | Adicionar à `routes/<dominio>.py` existente |
| Novo domínio HTTP | `routes/<novo>.py` + registrar em `factory.py` |
| Nova lógica de negócio | `services/<nome>.py` (ou estender existente) |
| Nova query reutilizada | `repositories/<dominio>_repository.py` |
| Novo model | `models/<nome>.py` + adicionar ao `models/__init__.py` |
| Componente React reutilizado em 2+ features | `components/common/` ou `components/form/` |
| Componente React de uma feature | `features/<X>/components/` |
| Hook reutilizável | `hooks/` |
| Hook específico da feature | `features/<X>/hooks/` |
| Utility pura reutilizada | `lib/utils/` |
| Utility específica da feature | `features/<X>/utils/` |
| Type compartilhado entre features | `types/` |
| Type da feature | dentro do arquivo que usa, ou `features/<X>/types.ts` |
| Doc de uma área | `docs/<area>.md` (mantenha sob 5 arquivos no total) |

Se está em dúvida entre "shared" e "feature-scoped" — comece em feature. Só sobe para shared quando uma 2ª feature precisa.
