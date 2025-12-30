# Phase 0: Freeze Behavior - Notas de Implementação

## Resumo

A Phase 0 implementa observabilidade e diagnóstico no PWA vanilla JS **sem alterar comportamento funcional**. O objetivo é estabelecer uma baseline de instrumentação antes de qualquer refatoração/migração futura.

## Arquivos Adicionados

### 1. `frontend/assets/js/telemetry.js`

**Responsabilidades:**
- Coleta eventos padronizados: `{ts, level, area, action, message, context, requestId?}`
- Persiste últimos 200 eventos em IndexedDB separado (`puf_telemetry`)
- Buffer em memória com flush periódico (750ms) para performance
- Sanitização agressiva de dados sensíveis (senhas, tokens, dados pessoais)
- Fallback para localStorage (máx 50 eventos) se IndexedDB falhar

**Métodos principais:**
- `init()` - Inicializa sistema de telemetria
- `log(level, area, action, message, context, requestId)` - Core logging
- `logInfo()`, `logWarn()`, `logError()` - Helpers
- `getLogs(limit)` - Recupera logs
- `clearLogs()` - Limpa logs
- `exportLogs()` - Exporta JSON para download

**Sanitização:**
- Remove campos: `password`, `token`, `auth`, `authorization`, `bearer`, `cookie`, `session`, `secret`, `key`, `credential`
- Trunca strings longas (>200 chars)
- Não registra dados pessoais óbvios (nomes completos, telefones, endereços)

### 2. `frontend/assets/js/diagnostics.js`

**Responsabilidades:**
- UI de diagnóstico acessível via `Ctrl+Shift+D` (ou `Cmd+Shift+D` no Mac)
- Exibe informações do sistema (versão, online/offline, SW status, DB health)
- Tabela com últimos 50 logs
- Botões para exportar e limpar logs

**Métodos principais:**
- `show()` - Mostra modal de diagnóstico
- `gatherInfo()` - Coleta informações do sistema
- `getServiceWorkerStatus()` - Obtém status do SW
- `createModalContent()` - Gera HTML do modal

## Arquivos Modificados

### 1. `frontend/index.html`

**Mudanças:**
- Adicionado script `telemetry.js` (antes de `api.js`)
- Adicionado script `diagnostics.js` (após `router.js`)

**Ordem de carregamento:**
```html
utils.js → telemetry.js → api.js → db.js → auth.js → router.js → diagnostics.js → app.js
```

### 2. `frontend/assets/js/app.js`

**Mudanças:**

1. **Inicialização do Telemetry:**
   - `Telemetry.init()` chamado no início de `App.init()`
   - DB health check logado no startup

2. **Handlers globais de erro:**
   - `window.onerror` → loga em telemetry
   - `window.onunhandledrejection` → loga em telemetry

3. **Atalho de diagnóstico:**
   - `Ctrl+Shift+D` (ou `Cmd+Shift+D`) abre modal de diagnóstico

4. **Service Worker message listener:**
   - Escuta mensagens do SW e loga em telemetry

5. **Logging de erros de registro do SW:**
   - Erros ao registrar SW são logados

### 3. `frontend/assets/js/api.js`

**Mudanças:**

1. **Geração de requestId:**
   - Método `generateRequestId()` adicionado
   - Cada requisição recebe ID único para rastreamento

2. **Logging de requests/responses:**
   - Log de início: `api/request` (method, url, requestId)
   - Log de resposta: `api/response` (requestId, status, durationMs)
   - Log de erro: `api/error` (requestId, url, status, errorType)

3. **Timeout ajustado:**
   - Default alterado de 10s para 15s (se não especificado)

4. **Normalização de erros:**
   - Erros retornam formato padronizado:
     ```javascript
     {
       ok: false,
       success: false,
       status: number,
       code: string,
       message: string,
       details?: any,
       requestId: string
     }
     ```

5. **Interceptor de unhandledrejection:**
   - Estendido para também logar em telemetry

### 4. `frontend/assets/js/db.js`

**Mudanças:**

1. **Logging de operações:**
   - `init()` - loga sucesso/falha
   - `onupgradeneeded` - loga upgrades de schema
   - `savePendingPedido()` - loga writes
   - `getPendingPedidos()` - loga reads
   - `syncPendingPedidos()` - loga início e resultado de sync
   - `cachePedidos()` - loga operações de cache

2. **Método `dbHealthCheck()`:**
   - Retorna `{ok, dbName, version, lastError?}`
   - Testa operação de leitura para validar saúde do DB
   - Chamado no startup e exibido no modal de diagnóstico

## Como Usar

### Abrir Diagnóstico

**Desktop:**
- Pressione `Ctrl+Shift+D` (Windows/Linux) ou `Cmd+Shift+D` (Mac)

**Mobile:**
- Adicione botão discreto em menu/ajuda (implementação futura se necessário)

### Exportar Logs

1. Abra diagnóstico (`Ctrl+Shift+D`)
2. Clique em "Exportar Logs"
3. Arquivo JSON será baixado: `puf-telemetry-{timestamp}.json`
4. Arquivo contém:
   - `exportedAt` - Data/hora da exportação
   - `appVersion` - Versão do app
   - `logCount` - Número de logs
   - `logs` - Array de eventos

### Limpar Logs

1. Abra diagnóstico
2. Clique em "Limpar Logs"
3. Confirme ação
4. Todos os logs serão removidos

### Verificar Logs no Console

Logs também aparecem no console do navegador (DevTools) com prefixo `[Telemetry]`.

## Limitações Conhecidas

### Service Worker

- `sw.js` é código compilado (Workbox)
- **Não modificamos** handlers principais de fetch
- Apenas observamos status do SW (registered, controlling, waiting)
- Se houver canal seguro de `postMessage`, mensagens são capturadas e logadas
- Limitação: não podemos logar eventos internos do SW sem modificar código compilado

### Sanitização

- Sanitização é agressiva, mas pode não capturar todos os casos
- Dados pessoais podem aparecer em mensagens de erro (limitado a 200 chars)
- Stack traces são truncados (500 chars)

### Performance

- Buffer/flush reduz impacto, mas ainda há overhead mínimo
- IndexedDB separado evita conflitos, mas usa espaço adicional
- Flush periódico (750ms) pode atrasar logs em caso de crash imediato

### Mobile

- Diagnóstico via atalho pode não ser prático em mobile
- Botão discreto pode ser adicionado em versão futura se necessário

### Offline (Limitação Conhecida)

- **Pedidos criados offline podem se perder** - Este é um bug pré-existente, não introduzido pela Phase 0
- Causa: IDs hard-coded em pedidos offline podem causar conflitos
- Status: Documentado, não é regressão da Phase 0
- Ação futura: Resolver em fase de refatoração (não Phase 0)

## Estrutura de Logs

Cada log contém:

```javascript
{
  ts: number,              // Timestamp (Date.now())
  level: string,           // 'info' | 'warn' | 'error'
  area: string,            // 'api' | 'db' | 'global' | 'sw' | 'telemetry'
  action: string,          // 'request' | 'response' | 'error' | 'init' | etc.
  message: string,         // Mensagem descritiva (truncada)
  context: object,        // Contexto sanitizado (sem dados sensíveis)
  requestId: string|null  // ID da requisição (se aplicável)
}
```

## Testes

Ver `docs/phase0-smoke.md` para checklist completo de fluxos críticos.

## Próximos Passos (Pós-Phase 0)

1. Analisar logs coletados para identificar padrões de erro
2. Usar baseline para validar refatorações futuras
3. Expandir instrumentação conforme necessário
4. Considerar métricas de performance (se necessário)

---

**Versão:** Phase 0 - Freeze Behavior  
**Data:** 2024-12-XX  
**Branch:** develop

