# Arquitetura do Frontend

Este documento descreve a arquitetura, estrutura de pastas e padrões do frontend.

## Visão Geral

O frontend utiliza arquitetura **Feature-Based** (organização por features/módulos), com separação clara de responsabilidades e componentes reutilizáveis.

## Estrutura de Pastas

```
frontend_v2/src/
├── features/           # Módulos organizados por feature (pedidos, clientes, etc)
│   ├── auth/          # Autenticação
│   ├── pedidos/       # Gestão de pedidos
│   ├── customers/     # Gestão de clientes (CRM)
│   ├── rotas/         # Otimização de rotas
│   ├── sales/         # Vendas e estatísticas
│   ├── fontes/        # Fontes de pedidos
│   └── offline/       # Diagnósticos offline
│
├── components/         # Componentes reutilizáveis
│   ├── common/        # Componentes comuns (Button, Loading, Error)
│   ├── form/          # Componentes de formulário (Input, Select)
│   ├── system/        # Componentes do sistema (Dialogs, etc)
│   └── uiverse/       # Componentes UI especiais
│
├── api/               # Cliente HTTP e endpoints da API
│   ├── endpoints/     # Definições de endpoints (pedidos, clientes, etc)
│   └── http.ts        # Cliente HTTP base
│
├── lib/               # Bibliotecas e utilitários
│   ├── offline/       # Funcionalidade offline (cache, outbox)
│   ├── format/        # Formatação (data, moeda)
│   └── http/          # Utilitários HTTP
│
├── hooks/             # React hooks customizados
│   ├── useDebouncedValue.ts
│   └── useAnimateOnMount.ts
│
├── layout/            # Componentes de layout
│   └── AppShell.tsx   # Shell principal da aplicação
│
├── app/               # Configuração do app
│   ├── App.tsx        # Componente raiz
│   ├── router.tsx     # Configuração de rotas
│   └── providers.tsx  # Providers (React Query, etc)
│
└── types/             # Tipos TypeScript compartilhados
```

## Padrão Feature-Based

Cada feature é um módulo completo e auto-contido:

```
features/pedidos/
├── components/        # Componentes específicos da feature
│   ├── PedidoWizard/ # Wizard de criação de pedidos
│   ├── OrderCard.tsx
│   ├── OrderList.tsx
│   └── ...
├── contexts/         # Contextos React (se necessário)
│   └── OrderFormContext.tsx
├── services/         # Serviços e interfaces
│   ├── IPedidoPrintService.ts
│   └── PedidoPrintService.ts
├── useCases/         # Casos de uso e lógica de negócio
│   ├── orderMapping.ts
│   ├── orderToForm.ts
│   └── ...
├── schemas.ts        # Schemas Zod para validação
├── OrdersPage.tsx    # Páginas principais
├── CreateOrderPage.tsx
├── EditOrderPage.tsx
└── OrderDetailsPage.tsx
```

### Estrutura de uma Feature

1. **Páginas**: Componentes de página (rotas)
2. **Components**: Componentes específicos da feature
3. **Services**: Interfaces e implementações de serviços
4. **UseCases**: Lógica de negócio e transformações
5. **Schemas**: Validação Zod
6. **Contexts**: Contextos React (se necessário)

## Convenções de Nomenclatura

### Arquivos

- **Componentes**: PascalCase (ex: `OrderCard.tsx`)
- **Hooks**: camelCase com prefixo `use` (ex: `useDebouncedValue.ts`)
- **Utilitários**: camelCase (ex: `orderMapping.ts`)
- **Types/Interfaces**: PascalCase ou sufixo `Type` (ex: `PedidoType.ts`)

### Componentes

- **Páginas**: Sufixo `Page` (ex: `OrdersPage.tsx`)
- **Componentes**: Nome descritivo (ex: `OrderCard.tsx`)
- **Hooks**: Prefixo `use` (ex: `usePedidos`)

### Pastas

- **Features**: Nome no plural (ex: `pedidos/`, `customers/`)
- **Components**: Nome no plural (ex: `components/`, `hooks/`)

## Path Aliases

Para imports mais limpos, use path aliases:

```typescript
// ✅ Bom
import { Button } from '@/components/common/AppButton'
import { usePedidos } from '@/api/endpoints/pedidos'
import { useAuth } from '@/features/auth/authStore'

// ❌ Evitar
import { Button } from '../../../components/common/AppButton'
```

Ver [TECHNOLOGY.md](TECHNOLOGY.md) para lista completa de aliases.

## Organização de Código

### Separação de Responsabilidades

- **Components**: Apenas apresentação (UI)
- **Features**: Lógica de negócio específica da feature
- **API**: Comunicação com backend
- **Lib**: Utilitários compartilhados
- **Hooks**: Lógica reutilizável de componentes

### Princípios

1. **Single Responsibility**: Cada arquivo/função tem uma única responsabilidade
2. **DRY (Don't Repeat Yourself)**: Evitar duplicação, criar utilitários compartilhados
3. **Composição sobre Herança**: Preferir composição de componentes
4. **Separação de Concerns**: Separar lógica de negócio de apresentação

## Estado Global

O projeto utiliza:

- **React Query**: Estado servidor e cache
- **Context API**: Estado local específico (ex: `OrderFormContext`)
- **Local Storage**: Persistência de dados do usuário (ex: credenciais)

**Evitar**: Redux ou outros state managers globais (React Query + Context são suficientes).

## Roteamento

Roteamento configurado em `src/app/router.tsx` usando React Router v7:

- Rotas definidas de forma declarativa
- Lazy loading de páginas (code splitting)
- Rotas protegidas com `RequireAuth`

## Providers

Providers configurados em `src/app/providers.tsx`:

- **QueryClientProvider**: React Query
- **RouterProvider**: React Router
- Outros providers conforme necessário

---

**Última atualização**: 2026-01-04  
**Ver também**: [DATA_PATTERNS.md](DATA_PATTERNS.md) para padrões de dados
