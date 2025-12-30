# Phase 1 - Melhorias de Refetch e Performance

## Resumo

Implementadas melhorias no sistema de refetch do React Query, adicionado botão de atualização manual, indicador visual de atualização, e melhorias no backend para monitoramento de performance.

**Data:** 30/12/2025

---

## 1. Configuração de Refetch do React Query

### 1.1. `useStats()` - Refetch a cada 8 segundos

**Arquivo:** `frontend_v2/src/api/endpoints/stats.ts`

**Mudanças:**
```typescript
return useQuery<StatsResponse>({
  queryKey: ['stats'],
  queryFn: async () => { /* ... */ },
  staleTime: 30000, // 30 seconds
  refetchInterval: 8000, // 8 seconds ✅ NOVO
  refetchOnWindowFocus: true, // ✅ NOVO
});
```

**Justificativa:**
- Stats mudam frequentemente (pedidos sendo criados, status mudando)
- 8 segundos garante dados atualizados sem sobrecarregar o servidor

### 1.2. `usePedidos()` - Refetch a cada 15 segundos

**Arquivo:** `frontend_v2/src/api/endpoints/pedidos.ts`

**Mudanças:**
```typescript
return useQuery<PedidosResponse>({
  queryKey: ['pedidos', filters],
  queryFn: async () => { /* ... */ },
  staleTime: 30000, // 30 seconds
  refetchInterval: 15000, // 15 seconds ✅ NOVO
  refetchOnWindowFocus: true, // ✅ NOVO
});
```

**Justificativa:**
- Lista de pedidos é maior e pode ser mais pesada
- 15 segundos é um bom equilíbrio entre atualização e performance
- Filtros mudando invalidam a query automaticamente (queryKey inclui `filters`)

### 1.3. Configuração Global - `refetchOnWindowFocus: true`

**Arquivo:** `frontend_v2/src/app/providers.tsx`

**Mudanças:**
```typescript
const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      refetchOnWindowFocus: true, // ✅ MUDADO de false para true
      retry: 1,
      staleTime: 30000,
    },
  },
});
```

**Justificativa:**
- Quando usuário volta para a aba, dados são atualizados automaticamente
- Melhora UX ao garantir dados frescos

---

## 2. Invalidação Automática de Queries por Filtros

### 2.1. Como Funciona

**Arquivo:** `frontend_v2/src/api/endpoints/pedidos.ts`

A `queryKey` inclui os filtros:
```typescript
queryKey: ['pedidos', filters]
```

**Comportamento:**
- Quando `filters` muda, a `queryKey` muda
- React Query trata como uma nova query
- Automaticamente faz refetch com os novos filtros
- Cache é separado por combinação de filtros

**Exemplo:**
- `['pedidos', { status: 'agendado' }]` → Query separada
- `['pedidos', { status: 'pronto' }]` → Query separada
- `['pedidos', { search: 'João' }]` → Query separada

**Status:** ✅ Funcionando corretamente

---

## 3. Botão "Atualizar" Manual

### 3.1. Implementação

**Arquivo:** `frontend_v2/src/features/pedidos/OrdersPage.tsx`

**Mudanças:**
```typescript
import { useQueryClient } from '@tanstack/react-query';
import { Refresh } from '@mui/icons-material';

const queryClient = useQueryClient();

const handleRefresh = () => {
  queryClient.invalidateQueries({ queryKey: ['pedidos'] });
  queryClient.invalidateQueries({ queryKey: ['stats'] });
};
```

**UI:**
- Botão com ícone `Refresh` no topo da página
- Tooltip: "Atualizar dados"
- Desabilitado durante `isFetching`
- Posicionado ao lado do título "Pedidos"

**Comportamento:**
- Invalida todas as queries de `pedidos` (independente de filtros)
- Invalida query de `stats`
- React Query automaticamente faz refetch

---

## 4. Indicador Visual de "Atualizando..."

### 4.1. Implementação

**Arquivo:** `frontend_v2/src/features/pedidos/OrdersPage.tsx`

**Mudanças:**
```typescript
const { 
  isFetching: isFetchingPedidos 
} = usePedidos(filters);
const { 
  isFetching: isFetchingStats 
} = useStats();

const isFetching = isFetchingPedidos || isFetchingStats;
```

**UI:**
- Spinner pequeno (16px) no canto superior direito
- Texto "Atualizando..." ao lado
- Posição fixa (`position: fixed`)
- Aparece apenas quando `isFetching === true`
- Estilo discreto (fundo branco, sombra sutil)

**Características:**
- Não bloqueia interação do usuário
- Visual discreto mas visível
- Aparece durante refetch automático e manual

---

## 5. Melhorias no Backend

### 5.1. Threading Habilitado

**Arquivo:** `backend/app/cli.py`

**Mudanças:**
```python
run_simple(
    hostname=server_host,
    port=server_port,
    application=app,
    use_debugger=debug,
    use_reloader=use_reloader,
    ssl_context=ssl_context,
    threaded=True  # ✅ NOVO - Habilitar threads para melhor concorrência
)
```

**Justificativa:**
- Permite processar múltiplas requisições simultaneamente
- Melhora performance quando há múltiplas requisições concorrentes
- Reduz fila de espera

### 5.2. Logging de Tempo por Request

**Arquivo:** `backend/app/middleware.py`

**Mudanças:**

**before_request:**
```python
@app.before_request
def before_request():
    from flask import g
    # Registrar tempo de início para medir duração da requisição
    g.start_time = datetime.now()
    # ... resto do código ...
```

**after_request:**
```python
@app.after_request
def after_request(response):
    from flask import g
    
    # Calcular duração da requisição
    if hasattr(g, 'start_time'):
        duration_ms = (datetime.now() - g.start_time).total_seconds() * 1000
        # Logar tempo de request (método, path, ms)
        print(f'[{datetime.now().strftime("%H:%M:%S")}] {request.method:6s} {request.path:30s} {duration_ms:7.2f} ms')
    
    # ... resto do código ...
    return response
```

**Formato do Log:**
```
[14:30:45] GET    /api/pedidos                   123.45 ms
[14:30:46] GET    /api/stats                      45.67 ms
[14:30:47] GET    /api/pedidos?status=pronto     234.56 ms
```

**Justificativa:**
- Permite identificar requisições lentas
- Facilita diagnóstico de problemas de performance
- Comparar antes/depois de mudanças

---

## 6. Validação com Telemetria

### 6.1. Como Validar

**Pré-requisitos:**
- Telemetria já implementada na Phase 0
- Logs de API já capturam `durationMs`

**Passos:**

1. **Antes das mudanças:**
   - Exportar logs da telemetria
   - Filtrar por `/api/pedidos` e `/api/stats`
   - Calcular distribuição de `durationMs`

2. **Depois das mudanças:**
   - Exportar logs novamente
   - Comparar distribuição de `durationMs`
   - Verificar se há melhoria

3. **Métricas a observar:**
   - Tempo médio de resposta
   - Tempo p95 (95% das requisições)
   - Tempo p99 (99% das requisições)
   - Requisições que excedem timeout (15s)

### 6.2. Logs do Backend

**Formato:**
```
[14:30:45] GET    /api/pedidos                   123.45 ms
```

**Análise:**
- Identificar requisições > 500ms (lentas)
- Identificar requisições > 1000ms (muito lentas)
- Comparar com logs da telemetria (frontend)

**Ferramentas:**
- `grep` para filtrar logs
- Script Python para análise estatística
- Comparação antes/depois

---

## 7. Checklist de Validação

### 7.1. Frontend

- [x] `useStats()` com `refetchInterval: 8000`
- [x] `usePedidos()` com `refetchInterval: 15000`
- [x] `refetchOnWindowFocus: true` global
- [x] Filtros invalidam query automaticamente
- [x] Botão "Atualizar" implementado
- [x] Indicador "Atualizando..." implementado
- [ ] Testar refetch automático (aguardar 8s e 15s)
- [ ] Testar refetch ao voltar para aba
- [ ] Testar botão "Atualizar"
- [ ] Verificar indicador visual

### 7.2. Backend

- [x] `threaded=True` no `run_simple()`
- [x] Logging de tempo em `before_request`
- [x] Logging de tempo em `after_request`
- [ ] Verificar logs no console do Flask
- [ ] Validar que threads estão funcionando (múltiplas requisições simultâneas)
- [ ] Comparar tempos antes/depois

### 7.3. Telemetria

- [ ] Exportar logs antes das mudanças
- [ ] Exportar logs depois das mudanças
- [ ] Comparar distribuição de `durationMs`
- [ ] Identificar melhorias ou regressões

---

## 8. Próximos Passos

### 8.1. Monitoramento Contínuo

- Configurar alertas para requisições > 1s
- Dashboard de performance (opcional)
- Análise periódica de logs

### 8.2. Otimizações Futuras

- Cache de queries mais agressivo
- Debounce em filtros de busca
- Paginação se lista crescer muito
- Lazy loading de dados

---

## 9. Arquivos Modificados

### Frontend

1. `frontend_v2/src/app/providers.tsx`
   - Mudado `refetchOnWindowFocus: false` → `true`

2. `frontend_v2/src/api/endpoints/stats.ts`
   - Adicionado `refetchInterval: 8000`
   - Adicionado `refetchOnWindowFocus: true`

3. `frontend_v2/src/api/endpoints/pedidos.ts`
   - Adicionado `refetchInterval: 15000`
   - Adicionado `refetchOnWindowFocus: true`

4. `frontend_v2/src/features/pedidos/OrdersPage.tsx`
   - Adicionado `useQueryClient`
   - Adicionado `isFetching` de ambas queries
   - Adicionado botão "Atualizar"
   - Adicionado indicador "Atualizando..."

### Backend

1. `backend/app/cli.py`
   - Adicionado `threaded=True` no `run_simple()`

2. `backend/app/middleware.py`
   - Adicionado `g.start_time` em `before_request`
   - Adicionado logging de tempo em `after_request`

---

## 10. Notas Técnicas

### 10.1. React Query e Filtros

**Importante:** A invalidação automática por filtros funciona porque:
- `queryKey` inclui `filters` como dependência
- Quando `filters` muda, React Query trata como nova query
- Cache é separado por combinação de filtros
- Não é necessário invalidar manualmente quando filtros mudam

### 10.2. Threading no Werkzeug

**Nota:** `threaded=True` no `run_simple()`:
- Cria uma thread por requisição
- Adequado para desenvolvimento e pequena escala
- Para produção, considere usar Gunicorn ou uWSGI com workers

### 10.3. Logging de Performance

**Nota:** O logging no console pode ser verboso em produção:
- Considere usar nível de log configurável
- Ou redirecionar para arquivo
- Ou usar biblioteca de logging estruturado

---

**Última atualização:** 30/12/2025
**Versão:** 1.0

