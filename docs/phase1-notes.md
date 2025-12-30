# Phase 1 - Implementation Notes

## Overview

Phase 1 implementa o Frontend v2 usando Vite + React + TypeScript, criado em paralelo ao app legado sem quebrar funcionalidade existente. A primeira tela migrada é a lista de pedidos (Dashboard/Orders).

## Arquivos Criados/Modificados

### Estrutura do Projeto

```
frontend_v2/
├── src/
│   ├── app/
│   │   ├── main.tsx              # Entry point (atualizado)
│   │   ├── App.tsx               # Root component
│   │   ├── router.tsx            # React Router setup
│   │   └── providers.tsx         # QueryClient + ThemeProvider
│   ├── layout/
│   │   └── AppShell.tsx          # Responsive layout wrapper
│   ├── api/
│   │   ├── http.ts               # Single API client
│   │   └── endpoints/
│   │       ├── pedidos.ts        # Orders API hooks
│   │       ├── stats.ts          # Stats API hook
│   │       └── health.ts         # Health check hook
│   ├── features/
│   │   ├── auth/
│   │   │   └── authStore.ts      # Auth Context + hooks
│   │   └── pedidos/
│   │       ├── OrdersPage.tsx    # Main orders page
│   │       └── components/
│   │           ├── OrderCard.tsx
│   │           └── OrderList.tsx
│   └── components/
│       └── common/
│           ├── Loading.tsx
│           └── ErrorState.tsx
├── vite.config.ts                # Vite config with proxy
├── package.json                  # Dependencies
└── tsconfig.json                 # TypeScript config
```

## Detalhes de Implementação

### 1. Auth Compatibility

**Storage Keys (idênticos ao legado):**
- `plante_uma_flor_auth` (localStorage) - para "lembrar"
- `plante_uma_flor_auth_session` (sessionStorage) - para sessão

**Formato:**
```typescript
{
  username: string;
  password: string; // Em produção, usar JWT token
  timestamp: number;
}
```

**Basic Auth Header:**
```typescript
Authorization: Basic ${btoa(username + ":" + password)}
```

**Simplified Auth Injection:**
- Anexa `Authorization` header a TODAS as requisições `/api/*`
- **EXCEÇÃO:** Não anexa a `/api/auth/login` e `/api/auth/check`
- Isso é semanticamente neutro para Basic Auth e reduz fragilidade (não precisa manter lista de rotas)

**Implementação:**
- `features/auth/authStore.ts`: React Context + hooks (sem Zustand para Phase 1)
- Cache de 5 segundos para `isAuthenticated()` (igual ao legado)

### 2. API Client Architecture

**Single API Client (`api/http.ts`):**
- Base URL: `import.meta.env.VITE_API_BASE_URL` (default: `/api`)
- Timeout: 15 segundos (AbortController)
- Error normalization: `{ok: false, status, code, message, details, requestId}`
- Request ID único para rastreamento
- Suporte a offline detection

**Endpoints (`api/endpoints/*.ts`):**
- Type-safe functions usando `http.ts`
- React Query hooks (`useQuery`, `useMutation`) no mesmo arquivo
- **CRÍTICO:** Todas as chamadas de API via hooks do React Query
- **NÃO usar `useEffect` com `fetch` manual** - previne duplicação em React 18 StrictMode

**Exemplo:**
```typescript
export function usePedidos(filters: PedidosFilters = {}) {
  const { getAuthHeader } = useAuth();
  const apiRequest = createApiRequest(getAuthHeader);

  return useQuery<PedidosResponse>({
    queryKey: ['pedidos', filters],
    queryFn: async () => {
      const response = await apiRequest<PedidosResponse>(endpoint);
      if (!response.ok) throw new Error(response.message);
      return response.data;
    },
    staleTime: 30000, // 30 segundos
  });
}
```

### 3. Bootstrap/Initialization

**Single Initialization:**
- `QueryClient` único em `providers.tsx`
- `ThemeProvider` (MUI) único
- Router setup único em `App.tsx`
- Sem duplicação de providers

**React 18 StrictMode:**
- React Query deduplica automaticamente chamadas duplicadas
- Não há necessidade de prevenir duplicação manualmente
- Todos os dados via React Query hooks (não `useEffect` com `fetch`)

### 4. Orders Page

**Componentes:**
- `OrdersPage.tsx`: Página principal com filtros e lista
- `OrderList.tsx`: Grid responsivo de cards
- `OrderCard.tsx`: Card individual com informações do pedido

**Filtros (Phase 1 - Mínimo):**
- Busca por texto (cliente, destinatário, produto)
- Filtro por status (dropdown)
- Sem filtros de data complexos ainda (Phase 1.1)

**Estados:**
- Loading: Skeleton cards
- Error: ErrorState com botão retry
- Empty: Mensagem "Nenhum pedido encontrado"
- Success: Grid de OrderCards

**Stats Cards:**
- Exibidos no topo da página
- Total, Agendados, Em Produção, Prontos, Entregues, Atrasados
- Carregados via `useStats()` hook

### 5. Responsive Design

**Layout:**
- MUI Grid: 1 coluna mobile, 2 tablet, 3 desktop
- AppBar fixo no topo
- Container com maxWidth="xl"

**Breakpoints:**
- xs: 1 coluna
- sm: 2 colunas
- md: 3 colunas

### 6. Vite Configuration

**Proxy:**
```typescript
server: {
  proxy: {
    '/api': {
      target: 'http://localhost:5000',
      changeOrigin: true,
    },
  },
}
```

**Environment Variables:**
- `.env.example` criado (mas não commitado - está no .gitignore)
- `VITE_API_BASE_URL=/api`
- `VITE_APP_VERSION=3.0.1`

## Como Usar

### Desenvolvimento

**Terminal 1: Backend**
```bash
cd backend
flask cli start
```

**Terminal 2: Frontend v2**
```bash
cd frontend_v2
npm run dev
```

Acesse `http://localhost:5173`

### Build

```bash
cd frontend_v2
npm run build
```

Output em `frontend_v2/dist/`

## Compatibilidade com Legado

### Auth
- ✅ Mesmos storage keys
- ✅ Mesmo formato de dados
- ✅ Basic Auth header idêntico
- ✅ Login/logout compatível

### API
- ✅ Mesmos endpoints
- ✅ Mesmos formatos de request/response
- ✅ Mesmos filtros (status, search, data_inicio, data_fim)

### Comportamento
- ✅ Lista de pedidos idêntica
- ✅ Stats idênticos
- ✅ Filtros funcionam igual

## Limitações Conhecidas (Phase 1)

1. **Apenas lista de pedidos migrada** - outras telas ainda no legado
2. **Sem criação/edição de pedidos** - Phase 1.1 ou 1.2
3. **Sem detalhes do pedido** - Phase 1.1
4. **Filtros de data básicos** - apenas status e busca de texto
5. **Sem autenticação UI** - assume que usuário já está autenticado no legado OU faz login manualmente (Phase 1.1)

## Phase 1.1 Preview (Próximos Passos)

### Migrar Customer Search
- Busca de clientes com autocomplete
- Correções de comportamento mobile (teclado, foco)
- Integração com formulário de pedido

### Melhorar Mobile Behavior
- Correções de UX mobile
- Melhorias de performance
- Otimizações de layout

### Adicionar Filtros de Data
- Filtro por data de entrega
- Filtro "hoje", "amanhã", "semana"
- Calendário date picker

### Migrar Order Details Modal
- Modal com detalhes completos do pedido
- Ações: editar, imprimir, deletar
- Histórico de mudanças de status

## Notas Técnicas

### React Query
- `staleTime: 30000` (30 segundos) - dados considerados frescos por 30s
- `refetchOnWindowFocus: false` - não refaz requisições ao focar janela
- `retry: 1` - tenta novamente apenas 1 vez em caso de erro

### MUI Theme
- Primary color: `#047857` (mesma do legado)
- Secondary color: `#059669`
- CssBaseline aplicado para reset de estilos

### TypeScript
- Strict mode habilitado
- Tipos explícitos para todas as APIs
- Interfaces para Pedido, Stats, etc.

## Troubleshooting

### Erro: "Cannot find module"
- Execute `npm install` em `frontend_v2/`

### Erro: "Proxy error"
- Verifique se o backend está rodando em `http://localhost:5000`
- Verifique se o proxy está configurado corretamente em `vite.config.ts`

### Erro: "401 Unauthorized"
- Verifique se as credenciais estão salvas em localStorage/sessionStorage
- Faça login no app legado primeiro OU implemente tela de login no v2

### Duplicação de requisições
- Se estiver usando `useEffect` com `fetch`, migre para React Query hooks
- React Query deduplica automaticamente, mesmo em StrictMode

