# Phase 1 - Smoke Tests (Frontend v2)

Este documento contém os testes de smoke para validar a implementação do Frontend v2 (Vite + React + TypeScript).

## Pré-requisitos

1. Backend Flask rodando em `http://localhost:5000`
2. Frontend v2 rodando em `http://localhost:5173` (Vite dev server)
3. Credenciais de autenticação válidas

## Setup

### Terminal 1: Backend
```bash
cd backend
flask cli start
```

### Terminal 2: Frontend v2
```bash
cd frontend_v2
npm run dev
```

## Testes

### 1. Dev Server
- **Passos:**
  1. Execute `npm run dev` no diretório `frontend_v2`
  2. Acesse `http://localhost:5173`
  3. Verifique se a página carrega sem erros no console
- **Comportamento Esperado:** Página carrega, AppBar aparece com título "Plante Uma Flor - Gestão de Pedidos"

### 2. Orders List (GET /api/pedidos)
- **Passos:**
  1. Acesse `http://localhost:5173`
  2. Verifique se a lista de pedidos é exibida
  3. Verifique se os cards de pedidos mostram: cliente, destinatário, produto, data, horário, status
- **Comportamento Esperado:** Lista de pedidos renderizada com cards responsivos (Grid layout)

### 3. Stats (GET /api/stats)
- **Passos:**
  1. Acesse `http://localhost:5173`
  2. Verifique se os cards de estatísticas aparecem no topo da página
  3. Verifique se os valores estão corretos (Total, Agendados, Em Produção, Prontos, Entregues, Atrasados)
- **Comportamento Esperado:** Cards de stats exibidos com valores numéricos corretos

### 4. Search Filter
- **Passos:**
  1. Digite um termo de busca no campo "Buscar pedidos" (ex: nome de cliente)
  2. Verifique se a lista é filtrada
  3. Limpe o campo e verifique se todos os pedidos voltam
- **Comportamento Esperado:** Lista filtra em tempo real conforme o termo digitado

### 5. Status Filter
- **Passos:**
  1. Selecione um status no dropdown (ex: "Agendado")
  2. Verifique se apenas pedidos com aquele status são exibidos
  3. Selecione "Todos" e verifique se todos os pedidos voltam
- **Comportamento Esperado:** Lista filtra por status corretamente

### 6. Loading States
- **Passos:**
  1. Abra o DevTools > Network
  2. Defina throttling para "Slow 3G"
  3. Recarregue a página
  4. Verifique se skeletons/loading spinners aparecem durante o carregamento
- **Comportamento Esperado:** Loading states visíveis (skeleton cards ou spinner)

### 7. Error States
- **Passos:**
  1. Pare o backend Flask
  2. Recarregue a página ou tente filtrar
  3. Verifique se mensagem de erro aparece
  4. Verifique se botão "Tentar Novamente" aparece
  5. Inicie o backend novamente
  6. Clique em "Tentar Novamente"
  7. Verifique se os dados são carregados
- **Comportamento Esperado:** Mensagem de erro clara com botão de retry funcional

### 8. Empty State
- **Passos:**
  1. Aplique um filtro que não retorne resultados (ex: status inexistente)
  2. Verifique se mensagem "Nenhum pedido encontrado" aparece
- **Comportamento Esperado:** Mensagem de estado vazio exibida quando não há resultados

### 9. Responsive Design
- **Passos:**
  1. Abra o DevTools > Toggle device toolbar
  2. Teste em diferentes tamanhos: Mobile (375px), Tablet (768px), Desktop (1920px)
  3. Verifique se o layout se adapta corretamente
  4. Verifique se os cards de pedidos se reorganizam (1 coluna mobile, 2 tablet, 3 desktop)
- **Comportamento Esperado:** Layout responsivo em todos os tamanhos de tela

### 10. Auth Compatibility (Legacy Storage)
- **Passos:**
  1. Faça login no app legado (`http://localhost:5000`)
  2. Verifique no DevTools > Application > Local Storage se existe `plante_uma_flor_auth`
  3. Acesse `http://localhost:5173` (v2)
  4. Verifique se os pedidos são carregados (auth header deve ser anexado automaticamente)
  5. Se não funcionar, faça login no v2 e verifique se usa os mesmos storage keys
- **Comportamento Esperado:** v2 reconhece credenciais do legado OU permite login independente com mesmos storage keys

### 11. No Duplicate API Calls
- **Passos:**
  1. Abra DevTools > Network
  2. Recarregue a página
  3. Verifique quantas requisições para `/api/pedidos` foram feitas
  4. Verifique quantas requisições para `/api/stats` foram feitas
- **Comportamento Esperado:** Apenas 1 requisição para cada endpoint (React Query deduplica automaticamente, mesmo em StrictMode)

### 12. React Query Caching
- **Passos:**
  1. Carregue a página e aguarde os dados
  2. Navegue para outra rota (se houver) e volte
  3. Verifique no DevTools > Network se novas requisições foram feitas
- **Comportamento Esperado:** Dados são servidos do cache do React Query (sem novas requisições se dentro do staleTime de 30s)

## Notas

- **Auth:** v2 deve usar os mesmos storage keys que o legado (`plante_uma_flor_auth`, `plante_uma_flor_auth_session`)
- **Proxy:** Vite proxy `/api` para `http://localhost:5000` automaticamente
- **React Query:** Todas as chamadas de API devem passar por hooks do React Query (não `useEffect` com `fetch`)
- **StrictMode:** React 18 StrictMode pode duplicar renders, mas React Query previne chamadas duplicadas

## Problemas Conhecidos

- Nenhum no momento (Phase 1 MVP)

