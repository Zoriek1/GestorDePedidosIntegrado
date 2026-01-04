# Padrões de Dados

Este documento descreve os padrões de gerenciamento de dados, state management, formulários, offline e cache.

## State Management

### React Query

O projeto utiliza **React Query (TanStack Query)** para gerenciamento de estado servidor e cache.

**Localização**: `src/api/endpoints/`

**Características**:
- Cache automático de dados do servidor
- Revalidação automática
- Sincronização em background
- Gerenciamento de loading/error states

**Exemplo**:

```typescript
// src/api/endpoints/pedidos.ts
export function usePedidos(filters?: PedidoFilters) {
  return useQuery({
    queryKey: ['pedidos', filters],
    queryFn: () => apiRequest<PedidosResponse>('/pedidos', {
      method: 'GET',
      // ...
    }),
    staleTime: 5 * 60 * 1000, // 5 minutos
  });
}
```

### Context API

Para estado local específico de features, utiliza-se **Context API**:

**Exemplo**: `OrderFormContext` - Gerencia estado do formulário de pedidos durante o wizard.

### Local Storage / Session Storage

Para persistência de dados do usuário:

- **Credenciais**: Armazenadas em `localStorage` (remember) ou `sessionStorage`
- **Preferências**: Configurações do usuário

## Formulários

### React Hook Form + Zod

Formulários são gerenciados com **React Hook Form** e validados com **Zod**.

**Características**:
- Performance otimizada (re-renders mínimos)
- Validação TypeScript-first
- Integração com MUI

**Exemplo**:

```typescript
import { useForm } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import { z } from 'zod';

const schema = z.object({
  nome: z.string().min(1, 'Nome é obrigatório'),
  telefone: z.string().min(10, 'Telefone inválido'),
});

function MeuForm() {
  const { register, handleSubmit, formState: { errors } } = useForm({
    resolver: zodResolver(schema),
  });

  const onSubmit = (data) => {
    // ...
  };

  return (
    <form onSubmit={handleSubmit(onSubmit)}>
      {/* ... */}
    </form>
  );
}
```

### Schemas Zod

Schemas de validação são definidos em arquivos `schemas.ts` dentro de cada feature:

**Exemplo**: `src/features/pedidos/schemas.ts`

## Offline Support

### Dexie (IndexedDB)

O projeto utiliza **Dexie** como wrapper para IndexedDB, permitindo funcionalidade offline completa.

**Localização**: `src/lib/offline/`

**Estrutura**:
- `db.ts`: Configuração do banco Dexie
- `cache.ts`: Cache de dados da API
- `outbox.ts`: Fila de operações offline (Outbox Pattern)
- `queryWithCache.ts`: Query helpers com cache

### Outbox Pattern

Operações offline são enfileiradas no **Outbox** e sincronizadas quando a conexão é restaurada:

**Fluxo**:
1. Usuário faz ação offline (ex: criar pedido)
2. Operação é adicionada ao Outbox (IndexedDB)
3. Quando online, operações são sincronizadas automaticamente
4. Outbox é limpo após sincronização bem-sucedida

### Cache Strategies

O sistema utiliza diferentes estratégias de cache:

- **API Health**: NetworkFirst (rede primeiro, com timeout)
- **API Pedidos/Stats**: NetworkFirst com cache de 24h
- **Outras APIs**: NetworkOnly (sempre busca da rede)

Configurado em `vite.config.ts` (Workbox).

## API Client

### Cliente HTTP

Cliente HTTP centralizado em `src/api/http.ts`:

**Características**:
- Tratamento de erros unificado
- Timeout configurável
- Detecção de HTML vs JSON
- Tratamento de offline/network errors
- Injeção automática de autenticação

**Exemplo**:

```typescript
import { request } from '@/api/http';

const response = await request('/pedidos', {
  method: 'POST',
  body: JSON.stringify(data),
}, getAuthHeader);

if (response.ok) {
  // Sucesso
  console.log(response.data);
} else {
  // Erro
  console.error(response.message);
}
```

### Endpoints

Endpoints são definidos como hooks React Query em `src/api/endpoints/`:

- `pedidos.ts`: Endpoints de pedidos
- `customers.ts`: Endpoints de clientes
- `health.ts`: Health check
- `stats.ts`: Estatísticas
- `rotas.ts`: Rotas otimizadas

## Tipos TypeScript

### Type Safety

O projeto utiliza TypeScript com strict mode habilitado:

- **Interfaces**: Definidas para todos os tipos de dados
- **Type Guards**: Verificações de tipo em runtime quando necessário
- **Generics**: Uso de generics para reutilização de tipos

### Exemplo

```typescript
interface Pedido {
  id: number;
  cliente: string;
  destinatario: string;
  // ...
}

interface PedidosResponse {
  success: boolean;
  data: {
    pedidos: Pedido[];
    total: number;
  };
}
```

## Formatação de Dados

### Utilitários de Formatação

Utilitários de formatação em `src/lib/format/`:

- `currency.ts`: Formatação de moeda
- `date.ts`: Formatação de datas

**Exemplo**:

```typescript
import { formatCurrency } from '@/lib/format/currency';
import { formatDate } from '@/lib/format/date';

const valor = formatCurrency(100.50); // R$ 100,50
const data = formatDate(new Date()); // 04/01/2026
```

## Mapeamento de Dados

### Use Cases

Lógica de transformação/mapeamento de dados em `src/features/*/useCases/`:

- `orderMapping.ts`: Mapeamento entre API e formulário
- `orderToForm.ts`: Conversão de pedido para formulário
- `customerMapping.ts`: Mapeamento de clientes

**Propósito**: Separar lógica de transformação da lógica de apresentação.

---

**Última atualização**: 2026-01-04  
**Ver também**: [ARCHITECTURE.md](ARCHITECTURE.md), [PWA.md](PWA.md)
