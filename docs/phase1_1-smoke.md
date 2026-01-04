# Phase 1.1 - Smoke Tests (Auth Parity + Gradual Migration)

Este documento contém os testes de smoke para validar a implementação da Phase 1.1: autenticação com paridade ao legado, rotas protegidas, e melhorias de refresh.

## Pré-requisitos

1. Backend Flask rodando em `http://localhost:5000`
2. Frontend v2 rodando em `http://localhost:5173` (Vite dev server)
3. Credenciais de autenticação válidas (mesmas do app legado)

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

### 1. Login Success
- **Passos:**
  1. Acesse `http://localhost:5173` (deve redirecionar para `/login` se não autenticado)
  2. Preencha usuário e senha válidos
  3. Marque "Lembrar-me" (opcional)
  4. Clique em "Entrar"
  5. Verifique se redireciona para `/` (home)
  6. Verifique se a lista de pedidos carrega
- **Comportamento Esperado:** Login bem-sucedido, redirecionamento para home, dados carregados

### 2. Login Failure
- **Passos:**
  1. Acesse `http://localhost:5173/login`
  2. Preencha credenciais inválidas
  3. Clique em "Entrar"
  4. Verifique se mensagem de erro aparece
  5. Verifique se não redireciona
- **Comportamento Esperado:** Mensagem de erro clara ("Credenciais inválidas"), permanece na página de login

### 3. Protected Routes - Redirect to Login
- **Passos:**
  1. Limpe localStorage e sessionStorage (DevTools > Application > Clear storage)
  2. Acesse `http://localhost:5173/` diretamente
  3. Verifique se redireciona para `/login`
  4. Verifique se `state.from` está preservado (opcional: verificar no DevTools)
  5. Faça login
  6. Verifique se redireciona de volta para `/` após login
- **Comportamento Esperado:** Rotas protegidas redirecionam para `/login`, após login retorna à rota original

### 4. Protected Routes - Stub Pages
- **Passos:**
  1. Faça login
  2. Navegue para `/clientes` (via menu ou URL)
  3. Verifique se a página "Em breve" aparece
  4. Navegue para `/pedidos/novo`
  5. Verifique se a página "Em breve" aparece
  6. Navegue para `/pedidos/123` (ID qualquer)
  7. Verifique se a página "Em breve" aparece
  8. Limpe storage e tente acessar `/clientes` diretamente
  9. Verifique se redireciona para `/login`
- **Comportamento Esperado:** Páginas stub renderizam corretamente quando autenticado, redirecionam quando não autenticado

### 5. Orders List Loads After Login
- **Passos:**
  1. Faça login
  2. Verifique se a lista de pedidos aparece
  3. Verifique se os cards de pedidos mostram: cliente, destinatário, produto, data, horário, status
  4. Verifique se os stats aparecem no topo
- **Comportamento Esperado:** Lista de pedidos e stats carregam corretamente após login

### 6. Refresh Behavior - Automatic Interval
- **Passos:**
  1. Faça login e aguarde a lista carregar
  2. Abra DevTools > Network
  3. Aguarde 15 segundos (ou verifique o timestamp das requisições)
  4. Verifique se novas requisições para `/api/pedidos` são feitas automaticamente
  5. Aguarde 8 segundos e verifique se `/api/stats` é atualizado
- **Comportamento Esperado:** Requisições automáticas a cada 15s (pedidos) e 8s (stats) quando a aba está em foco

### 7. Refresh Behavior - Manual Button
- **Passos:**
  1. Faça login e aguarde a lista carregar
  2. Abra DevTools > Network
  3. Clique no botão "Atualizar" (ícone de refresh)
  4. Verifique se novas requisições para `/api/pedidos` e `/api/stats` são feitas imediatamente
  5. Verifique se o indicador "Atualizando..." aparece durante o fetch
  6. Verifique se o botão fica desabilitado durante o fetch
- **Comportamento Esperado:** Botão de refresh invalida queries e refaz requisições, indicador visual mostra estado de loading

### 8. Refresh Behavior - Filter Changes
- **Passos:**
  1. Faça login e aguarde a lista carregar
  2. Aplique um filtro de status (ex: "Agendado")
  3. Verifique se a lista muda sem "flicker" (dados anteriores mantidos durante fetch)
  4. Mude o filtro para outro status
  5. Verifique se a transição é suave (keepPreviousData)
- **Comportamento Esperado:** Mudanças de filtro não causam "flicker", dados anteriores são mantidos até novos dados chegarem

### 9. Storage Key Compatibility with Legacy
- **Passos:**
  1. Faça login no app legado (`http://localhost:5000`)
  2. Verifique no DevTools > Application > Local Storage se existe `plante_uma_flor_auth` ou `plante_uma_flor_auth_session`
  3. Acesse `http://localhost:5173` (v2)
  4. Verifique se os pedidos são carregados automaticamente (sem precisar fazer login novamente)
  5. Faça logout no v2
  6. Verifique se ambas as chaves (`plante_uma_flor_auth` e `plante_uma_flor_auth_session`) foram removidas
- **Comportamento Esperado:** v2 reconhece credenciais do legado, logout limpa ambas as chaves

### 10. Navigation Menu
- **Passos:**
  1. Faça login
  2. Verifique se o menu de navegação aparece no AppBar
  3. Verifique se os links estão presentes: "Pedidos", "Clientes", "Novo Pedido"
  4. Clique em cada link e verifique se navega corretamente
  5. Verifique se o menu não aparece na página de login
- **Comportamento Esperado:** Menu de navegação funcional, links navegam corretamente, menu oculto na página de login

### 11. Logout Functionality
- **Passos:**
  1. Faça login
  2. Clique no ícone de usuário no AppBar
  3. Clique em "Sair"
  4. Verifique se redireciona para `/login`
  5. Verifique se localStorage e sessionStorage foram limpos
  6. Tente acessar `/` diretamente
  7. Verifique se redireciona para `/login`
- **Comportamento Esperado:** Logout limpa storage e redireciona para login, rotas protegidas não são acessíveis após logout

### 12. Username Display
- **Passos:**
  1. Faça login
  2. Verifique se o nome de usuário aparece no menu dropdown (ao clicar no ícone de usuário)
  3. Verifique se o formato está correto
- **Comportamento Esperado:** Nome de usuário exibido no menu dropdown

### 13. Auth Header Injection
- **Passos:**
  1. Faça login
  2. Abra DevTools > Network
  3. Verifique uma requisição para `/api/pedidos`
  4. Clique na requisição e verifique o Headers
  5. Verifique se o header `Authorization: Basic ...` está presente
  6. Verifique se requisições para `/api/auth/check` NÃO têm o header (se houver)
- **Comportamento Esperado:** Header Authorization presente em todas as requisições `/api/*` exceto `/api/auth/login` e `/api/auth/check`

### 14. UTF-8 Characters in Auth
- **Passos:**
  1. Se possível, teste com credenciais contendo caracteres especiais (UTF-8)
  2. Faça login
  3. Verifique se o login funciona corretamente
  4. Verifique se as requisições subsequentes funcionam
- **Comportamento Esperado:** Login funciona mesmo com caracteres UTF-8 (fallback implementado)

### 15. Window Focus Refetch
- **Passos:**
  1. Faça login e aguarde a lista carregar
  2. Abra DevTools > Network
  3. Mude para outra aba do navegador
  4. Aguarde alguns segundos
  5. Volte para a aba do v2
  6. Verifique se novas requisições são feitas automaticamente
- **Comportamento Esperado:** Requisições automáticas quando a aba recupera o foco (refetchOnWindowFocus)

## Notas

### Auth Behavior Differences
- **Legacy:** Usa modal `promptPassword()` para autenticação
- **v2:** Usa página dedicada `/login` com formulário MUI
- **Compatibilidade:** Ambos usam as mesmas chaves de storage (`plante_uma_flor_auth`, `plante_uma_flor_auth_session`)
- **Método:** Ambos usam HTTP Basic Auth header

### React Query Configuration
- **staleTime:** 5 segundos (dados considerados "frescos" por 5s)
- **refetchInterval:** 15s (pedidos), 8s (stats) - pode pausar quando aba não está em foco
- **keepPreviousData:** true (mantém dados anteriores durante mudanças de filtro)
- **refetchOnWindowFocus:** true (refaz requisições quando aba recupera foco)
- **Query invalidation:** Usa `exact: false` para invalidar todas as variações de queries filtradas

### Gradual Migration Strategy
- Páginas stub permitem estabelecer estrutura de navegação
- Cada stub pode ser migrado incrementalmente
- Nenhuma reescrita big-bang necessária

## Problemas Conhecidos

- Nenhum no momento (Phase 1.1 MVP)

