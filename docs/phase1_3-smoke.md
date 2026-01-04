# Phase 1.3 - Smoke Tests
## PWA/Offline Implementation

**Data:** Dezembro 2024  
**Status:** ✅ Implementação Completa

---

## Checklist de Testes

### PWA Installation

- [ ] **Install PWA**
  - Abrir aplicação no navegador (Chrome/Edge recomendado)
  - Verificar se o prompt de instalação aparece (ícone de instalação na barra de endereços)
  - Instalar o PWA
  - Verificar se o app abre em janela standalone
  - Verificar se os ícones aparecem corretamente (192x192 e 512x512)

### Offline App Shell

- [ ] **App works offline**
  - Com internet: carregar a aplicação uma vez
  - Desativar internet (DevTools > Network > Offline ou desativar WiFi)
  - Recarregar a página (F5)
  - Verificar se o app shell carrega (layout, navegação, etc.)
  - Verificar se não há erros de console relacionados a assets estáticos

### Cached Data Display

- [ ] **Orders page shows cached data when offline**
  - Com internet: navegar para a página de pedidos
  - Aguardar carregamento completo dos dados
  - Desativar internet
  - Recarregar a página
  - Verificar se a lista de pedidos ainda aparece (dados em cache)
  - Verificar se há indicador visual de dados stale/offline

- [ ] **Stats shows cached data when offline**
  - Com internet: verificar que stats aparecem na página de pedidos
  - Desativar internet
  - Recarregar a página
  - Verificar se stats ainda aparecem (dados em cache)

### Offline Mutations

- [ ] **Enqueue mutation offline (create order)**
  - Desativar internet
  - Navegar para `/test-offline`
  - Clicar em "Criar Pedido (Teste)"
  - Verificar toast: "Salvo offline; será sincronizado quando online"
  - Verificar que o contador de outbox aumenta no AppShell
  - Verificar que o item aparece na tabela de outbox na página de testes

- [ ] **Enqueue mutation offline (update order)**
  - Desativar internet
  - Navegar para `/test-offline`
  - Digitar um ID de pedido válido
  - Clicar em "Atualizar Pedido"
  - Verificar toast: "Salvo offline; será sincronizado quando online"
  - Verificar que o contador de outbox aumenta
  - Verificar que o item aparece na tabela de outbox

### Auto Sync on Reconnect

- [ ] **Reconnect and flush (outbox syncs automatically)**
  - Com itens na fila de outbox (após testes offline)
  - Reativar internet
  - Verificar que o evento `online` é detectado
  - Verificar que `flush()` é chamado automaticamente
  - Verificar toast de sucesso: "X item(ns) sincronizado(s)"
  - Verificar que os itens são removidos da fila de outbox
  - Verificar que o contador de outbox no AppShell volta para 0
  - Verificar que os dados são atualizados na lista de pedidos

### UI Indicators

- [ ] **Offline indicator shows correct status**
  - Com internet: verificar badge "Online" (verde) no AppShell
  - Desativar internet: verificar badge muda para "Offline" (cinza)
  - Reativar internet: verificar badge volta para "Online"

- [ ] **Outbox count badge appears when > 0**
  - Com itens na fila: verificar badge com número no AppShell
  - Verificar tooltip ao passar o mouse: "X item(ns) pendente(s) de sincronização"
  - Após sincronização: verificar que badge desaparece

### Diagnostics Page

- [ ] **Diagnostics page shows cache and outbox status**
  - Navegar para `/offline-diagnostics`
  - Verificar status: Online/Offline, contador de outbox, contador de cache
  - Verificar tabela de outbox mostra itens pendentes (se houver)
  - Verificar lista de entradas de cache mostra chaves e timestamps
  - Testar botão "Forçar Sincronização" (deve funcionar apenas quando online)
  - Testar botão "Limpar Cache" (com confirmação)
  - Testar botão "Limpar Outbox" (com confirmação)
  - Testar remoção individual de itens do outbox

---

## Testes Adicionais

### Edge Cases

- [ ] **Multiple mutations offline**
  - Desativar internet
  - Criar múltiplos pedidos de teste
  - Verificar que todos são enfileirados
  - Reativar internet
  - Verificar que todos são sincronizados em ordem (FIFO)

- [ ] **Failed sync (server error)**
  - Desativar backend (ou simular erro 500)
  - Tentar sincronizar itens
  - Verificar que tentativas são incrementadas
  - Verificar que erro é armazenado em `lastError`
  - Após 3 tentativas: verificar que item permanece na fila mas não tenta mais

- [ ] **4xx errors (client error)**
  - Criar mutation com dados inválidos
  - Sincronizar quando online
  - Verificar que item vira **FAILED** e **não é removido** da fila (não retenta automaticamente)
  - Verificar que aparece no `/offline-diagnostics` com `blocked=true` e `lastStatus` 4xx
  - Verificar que o botão "Retry" exige confirmação (quando for erro 4xx de validação)
  - Verificar que erro 401/403 bloqueia sync e exige login

- [ ] **Cache expiration**
  - Carregar dados
  - Simular expiração alterando o `ts` no IndexedDB (DevTools > Application > IndexedDB > `puf_offline` > `cache`)
  - Colocar `ts` bem antigo para uma entrada `tag=pedidos` e `tag=stats`
  - Desativar internet e recarregar
  - Verificar que o app exibe **Alert de dados desatualizados** (cache expirado) na página de pedidos

- [ ] **Cache cleanup + cap (Phase 1.3.1)**
  - Criar muitas entradas no cache (alterando filtros/buscas) para ultrapassar 200 entradas
  - Recarregar a aplicação
  - Verificar no `/offline-diagnostics` que o Dexie cache não cresce indefinidamente (cap=200)
  - Verificar que entradas expiradas são removidas (best-effort no startup / 1x dia)

- [ ] **Gating de diagnósticos e testes (Phase 1.3.1)**
  - Em produção (build sem flag), acessar `/offline-diagnostics` e `/test-offline`
  - Verificar que redireciona para `/` (não expõe ferramentas)
  - Habilitar `VITE_ENABLE_OFFLINE_DIAGNOSTICS=true` e rebuild
  - Verificar que as rotas ficam acessíveis

- [ ] **Offline auth UX (Phase 1.3.1)**
  - Limpar credenciais (logout/limpar storage)
  - Desativar internet
  - Acessar `/` (rota protegida)
  - Verificar que mostra tela “Sem conexão para login” (sem loop de redirect)

---

## Notas de Teste

### Como Testar Offline

1. **Chrome DevTools:**
   - F12 > Network tab > Throttling dropdown > Offline
   - Ou: Network tab > checkbox "Offline"

2. **Firefox DevTools:**
   - F12 > Network tab > Throttling > Offline

3. **Desativar WiFi/Internet:**
   - Mais realista, mas pode ser mais difícil de reativar rapidamente

### Verificar Service Worker

1. Chrome DevTools > Application > Service Workers
2. Verificar que service worker está registrado e ativo
3. Verificar que precache está funcionando (Application > Cache Storage)

### Verificar IndexedDB (Dexie)

1. Chrome DevTools > Application > IndexedDB
2. Verificar database `puf_offline`
3. Verificar tabelas `cache` e `outbox`
4. Inspecionar dados armazenados

---

## Resultados Esperados

Após todos os testes:

- ✅ PWA instalável e funcionando
- ✅ App shell carrega offline
- ✅ Dados em cache são exibidos quando offline
- ✅ Mutations são enfileiradas quando offline
- ✅ Sincronização automática ao reconectar
- ✅ Indicadores visuais funcionando corretamente
- ✅ Página de diagnósticos mostra informações corretas

---

## Problemas Conhecidos / Limitações

- Cache de Workbox e cache de Dexie podem ter dados diferentes (Workbox para assets, Dexie para API responses)
- `clientTimestamp` não é usado pelo backend para resolução de conflitos (documentado como "best-effort")
- Página de diagnósticos e `/test-offline` são **gated** por `VITE_ENABLE_OFFLINE_DIAGNOSTICS` em produção (Phase 1.3.1)

