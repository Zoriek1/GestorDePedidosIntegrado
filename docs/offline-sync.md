# Offline/Sync Documentation
## Phase 1.3 / 1.3.1 - PWA/Offline Implementation

**Data:** Dezembro 2024  
**Versão:** 1.1

---

## Visão Geral

O sistema implementa capacidades offline usando duas camadas principais:

1. **Workbox (Service Worker)**: Cache de assets estáticos e respostas de API via service worker
2. **Dexie (IndexedDB)**: Cache de dados de API e fila de sincronização (outbox pattern)

---

## Estratégia de Cache

### Workbox Caching Rules

O service worker gerencia cache de assets e algumas respostas de API:

1. **App shell/assets**: Precache automático (default do plugin)
   - Todos os assets estáticos (JS, CSS, HTML)
   - Ícones e imagens do app

2. **GET /api/health**: Network-first, 3s timeout
   - Fallback para cache se network falhar
   - Expiração: 5 minutos
   - Max entries: 1

3. **GET /api/pedidos?***: Network-first, 5s timeout
   - Fallback para cache se network falhar
   - Expiração: 24 horas
   - Max entries: 50

4. **GET /api/stats**: Network-first, 5s timeout
   - Fallback para cache se network falhar
   - Expiração: 24 horas
   - Max entries: 10

5. **Images**: Cache-first, 30 dias
   - Qualquer imagem (png, jpg, jpeg, svg, gif, webp)
   - Max entries: 50

6. **Outras chamadas de API**: Network-only
   - Mutations (POST, PUT, DELETE)
   - Autenticação
   - Não são cacheadas

### Dexie Cache Layer

Cache adicional em IndexedDB para respostas de API:

- **Quando escreve**: Após sucesso de requisição GET
- **Quando lê**: Quando network falha (offline/timeout)
- **Chaves**: Serialização de React Query query keys (`JSON.stringify(['pedidos', filters])`)
- **Tags**: Cada entrada é marcada com `tag` para aplicar políticas diferentes (`health`, `stats`, `pedidos`, `default`)
- **TTL por tag (Phase 1.3.1)**:
  - `health`: 5 minutos
  - `stats`: 1 hora
  - `pedidos`: 24 horas
  - `default`: 24 horas
- **Cap global (Phase 1.3.1)**: `MAX_CACHE_ENTRIES = 200`
- **Cleanup (Phase 1.3.1)**: roda no startup e best-effort 1x/dia (remove expirados e corta excedente por mais antigos)
- **Fallback stale (Phase 1.3.1)**: dado expirado só é retornado quando **offline** e não existe dado “fresco”

**Integração com React Query:**
- `queryFnWithCache`: Wrapper que tenta network, fallback para cache
- `placeholderData`: Carrega do cache no render inicial (melhora UX)

---

## Outbox Pattern

### Como Funciona

O outbox pattern permite que mutations sejam executadas offline e sincronizadas quando a conexão retornar.

**Fluxo:**

1. **Offline**: Mutation é enfileirada no outbox (IndexedDB)
2. **Online**: `flush()` processa a fila FIFO
3. **Sucesso**: Item é removido do outbox
4. **Falha**: Item permanece, tentativas incrementadas

### Tipos de Outbox

- `'create_order'`: POST `/api/pedidos`
- `'update_order'`: PUT `/api/pedidos/:id`

### Estrutura de Dados

```typescript
interface OutboxEntry {
  id?: number;                    // Auto-increment
  type: 'create_order' | 'update_order';
  payload: any;                   // Dados da mutation
  createdAt: number;              // Timestamp
  attempts: number;               // Número de tentativas
  status: 'PENDING' | 'PROCESSING' | 'FAILED' | 'DONE';
  lastError?: string;             // Último erro (se houver)
  lastStatus?: number;            // Último status HTTP (se houver)
  blocked?: boolean;              // Se true, não faz auto-retry (requer intervenção)
  clientTimestamp?: number;       // Para resolução de conflitos
}
```

### Política de Retry

- **Max tentativas**: 3
- **401/403**: vira `FAILED` + `blocked=true` (não remove). Usuário precisa fazer login novamente
- **Outros 4xx**: vira `FAILED` + `blocked=true` (não remove). Deve ser reprocessado manualmente via Diagnósticos
- **5xx/network/timeout**: auto-retry (mantém `PENDING`, incrementa `attempts`); ao atingir max tentativas vira `FAILED` (não bloqueado)
- **Nada some silenciosamente**: itens com falha permanecem visíveis no outbox

### Quando Flush é Executado

1. **On app start**: Se online, `flush()` é chamado automaticamente
2. **On online event**: Quando `window.online` é disparado
3. **Manual**: Botão "Forçar Sincronização" na página de diagnósticos

### Resolução de Conflitos

- **Política**: Last-write-wins usando `clientTimestamp`
- **Status atual**: Backend não usa `clientTimestamp` (documentado como "best-effort")
- **Futuro**: Backend pode implementar suporte a `clientTimestamp` para resolução de conflitos

---

## Gating de Diagnósticos (Phase 1.3.1)

As rotas e ações de diagnóstico/teste são **bloqueadas em produção** por padrão.

- **Flag**: `VITE_ENABLE_OFFLINE_DIAGNOSTICS=true`
- **DEV**: Em desenvolvimento, diagnósticos ficam habilitados automaticamente (`import.meta.env.DEV`).
- **Produção/Staging**: habilite via variável de ambiente **no build** (ou arquivo `.env` do Vite).

Rotas afetadas:
- `/offline-diagnostics`
- `/test-offline`

Sem a flag, essas rotas redirecionam para `/` (não expõem ferramentas perigosas).

---

## UX de Autenticação Offline (Phase 1.3.1)

Regras:
1. **Com credenciais salvas**: o app abre offline e rotas protegidas continuam acessíveis.
2. **Sem credenciais salvas**: offline mostra tela “Sem conexão para login” (não redireciona em loop).
3. **401/403 online**: força logout e redireciona para login.

---

## Limitações

### O que NÃO funciona offline

1. **Autenticação**: Login/logout requer conexão
2. **Busca de clientes**: Não há cache de resultados de busca
3. **Detalhes de pedido individual**: `usePedido(id)` não usa cache (opcional para v1)
4. **Mutations complexas**: Apenas create/update order são suportadas no outbox

### Problemas Conhecidos

1. **Dados stale**: Cache pode conter dados desatualizados (até 24h para pedidos/stats)
2. **Conflitos**: Sem resolução automática de conflitos (backend não suporta `clientTimestamp`)
3. **Cache duplicado**: Workbox e Dexie podem ter dados diferentes (intencional: Workbox para assets, Dexie para API)

---

## Troubleshooting

### App não instala como PWA

- Verificar se service worker está registrado (DevTools > Application > Service Workers)
- Verificar se manifest.json é gerado corretamente
- Verificar se ícones existem em `public/pwa-192x192.png` e `public/pwa-512x512.png`
- Verificar se app está sendo servido via HTTPS (ou localhost)

### Dados não aparecem offline

- Verificar se dados foram carregados pelo menos uma vez online
- Verificar IndexedDB (DevTools > Application > IndexedDB > `puf_offline` > `cache`)
- Verificar se query keys estão corretas (devem corresponder entre cache e React Query)

### Mutations não sincronizam

- Verificar se app detecta que está online (`navigator.onLine`)
- Verificar outbox (DevTools > Application > IndexedDB > `puf_offline` > `outbox`)
- Verificar erros no console
- Verificar se backend está acessível
- Verificar se `flush()` está sendo chamado (logs no console ou página de diagnósticos)

### Cache não limpa

- Limpar manualmente via página de diagnósticos
- Limpar IndexedDB manualmente (DevTools > Application > IndexedDB > Delete database)
- Limpar Cache Storage (DevTools > Application > Cache Storage)

---

## Guia de Integração

### Adicionar Nova Mutation com Outbox

1. **Adicionar tipo ao OutboxEntry:**
   ```typescript
   // src/lib/offline/db.ts
   type: 'create_order' | 'update_order' | 'delete_order' // novo tipo
   ```

2. **Adicionar handler no flush:**
   ```typescript
   // src/lib/offline/outbox.ts
   else if (item.type === 'delete_order') {
     const { id } = item.payload;
     response = await apiRequest(`/pedidos/${id}`, {
       method: 'DELETE'
     });
   }
   ```

3. **Criar mutation hook:**
   ```typescript
   // src/api/endpoints/pedidos.ts
   export function useDeletePedido() {
     const { isOnline } = useOffline();
     const { info } = useToast();
     
     return useMutation({
       mutationFn: async (id: number) => {
         if (isOnline) {
           // chamada direta
         } else {
           await enqueue('delete_order', { id });
           info('Salvo offline; será sincronizado quando online');
           throw new Error('OFFLINE_ENQUEUED');
         }
       }
     });
   }
   ```

### Adicionar Cache para Nova Query

1. **Modificar query hook:**
   ```typescript
   import { queryFnWithCache } from '../../lib/offline/queryWithCache';
   import { getCached } from '../../lib/offline/cache';
   
   export function useNovaQuery() {
     const queryKey: readonly unknown[] = ['nova-query'];
     
     return useQuery({
       queryKey,
       queryFn: () => queryFnWithCache(queryKey, async () => {
         // network logic
       }),
       placeholderData: async () => {
         const cached = await getCached(JSON.stringify(queryKey));
         return cached ? cached.value : undefined;
       }
     });
   }
   ```

---

## Arquitetura

### Fluxo de Dados

```
┌─────────────┐
│   React     │
│   Query     │
└──────┬──────┘
       │
       ▼
┌──────────────────┐
│ queryFnWithCache │
└──────┬───────────┘
       │
       ├──► Network ──► API ──► setCached (sucesso)
       │
       └──► getCached (falha) ──► Retorna cache ou throw
```

### Fluxo de Mutations

```
┌─────────────┐
│  Mutation   │
└──────┬──────┘
       │
       ├──► Online ──► API diretamente
       │
       └──► Offline ──► enqueue ──► Outbox (IndexedDB)
                              │
                              ▼
                         On reconnect ──► flush() ──► API
```

---

## Referências

- [Workbox Documentation](https://developers.google.com/web/tools/workbox)
- [Dexie Documentation](https://dexie.org/)
- [React Query Documentation](https://tanstack.com/query/latest)
- [PWA Best Practices](https://web.dev/progressive-web-apps/)

