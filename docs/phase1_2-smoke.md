# Phase 1.2 - Smoke Tests (Mobile UX + Responsividade + Redundância)

Este documento contém os testes de smoke para validar a implementação da Phase 1.2: Mobile UX para busca de clientes, responsividade de botões, redução de redundância, e organização de features.

## Pré-requisitos

1. Backend Flask rodando em `http://localhost:5000`
2. Frontend v2 rodando em `http://localhost:5173` (Vite dev server)
3. Credenciais de autenticação válidas
4. Dependências instaladas (incluindo `@tanstack/react-virtual`)

## Setup

### Terminal 1: Backend
```bash
cd backend
flask cli start
```

### Terminal 2: Frontend v2
```bash
cd frontend_v2
npm install  # Para instalar @tanstack/react-virtual
npm run dev
```

## Testes

### 1. Customer Search - Input Mantém Foco (Mobile + Desktop)

- **Passos:**
  1. Acesse `http://localhost:5173/clientes` (autenticado)
  2. Clique no campo de busca
  3. Digite caracteres rapidamente (ex: "joão silva")
  4. Observe se o input mantém foco durante a digitação
  5. Verifique se não há remontagem do componente (input não perde foco)

- **Comportamento Esperado:**
  - Input mantém foco durante toda a digitação
  - Nenhum blur ou remontagem ocorre
  - Funciona tanto em mobile (toque) quanto desktop (teclado)

### 2. Customer Search - Debounce Reduz Chamadas

- **Passos:**
  1. Acesse `http://localhost:5173/clientes`
  2. Abra DevTools > Network tab
  3. Digite "joão" no campo de busca (letra por letra)
  4. Observe as requisições à API

- **Comportamento Esperado:**
  - Não há requisição por cada tecla digitada
  - Requisição ocorre apenas após 300ms de pausa (debounce)
  - Apenas 1 requisição ao finalizar digitação (não 4-5 requisições)

### 3. Customer Search - Seleção Funciona

- **Passos:**
  1. Acesse `http://localhost:5173/clientes`
  2. Digite um termo que retorne resultados (ex: "joão")
  3. Aguarde aparecer lista de sugestões
  4. Clique/toque em um cliente da lista
  5. Verifique se cliente é selecionado e detalhes aparecem

- **Comportamento Esperado:**
  - Cliente selecionado aparece na seção "Cliente Selecionado"
  - Detalhes exibidos (ID, Nome, Telefone)
  - Input continua usável (não é limpo)

### 4. Customer Search - Virtualização (se > 50 itens)

- **Passos:**
  1. Acesse `http://localhost:5173/clientes`
  2. Digite um termo que retorne muitos resultados (> 50)
  3. Verifique se lista aparece e é scrollável
  4. Teste scroll dentro da lista

- **Comportamento Esperado:**
  - Lista virtualizada aparece corretamente
  - Scroll é suave
  - Performance mantida mesmo com muitos itens

### 5. Orders Page - Refresh Ainda Funciona

- **Passos:**
  1. Acesse `http://localhost:5173/` (página de pedidos)
  2. Clique no botão de atualizar (ícone refresh)
  3. Verifique se dados são atualizados

- **Comportamento Esperado:**
  - Refresh funciona corretamente
  - Indicador de loading aparece durante atualização
  - Dados são atualizados após refresh

### 6. Orders Page - Botões Têm Hit Targets Corretos (44px mínimo)

- **Passos:**
  1. Acesse `http://localhost:5173/`
  2. Em mobile (ou DevTools mobile mode):
     - Verifique se botão de refresh é facilmente clicável
     - Verifique se cards de pedidos são facilmente clicáveis
  3. Use DevTools para inspecionar tamanho dos elementos

- **Comportamento Esperado:**
  - Botões têm pelo menos 44px de altura (touch target)
  - Elementos clicáveis são facilmente tocáveis em mobile
  - Não há elementos muito pequenos que dificultam interação

### 7. Toast/Notification Aparecem Corretamente

- **Passos:**
  1. Acesse `http://localhost:5173/login`
  2. Tente fazer login com credenciais inválidas
  3. Verifique se toast de erro aparece

- **Comportamento Esperado:**
  - Toast aparece no canto inferior direito
  - Mensagem de erro é clara
  - Toast desaparece automaticamente após alguns segundos
  - Ícone de erro aparece (MUI Alert)

### 8. Confirm Modal Aparece Corretamente (Preparação)

- **Nota:** Confirm modal está preparado mas pode não ter uso ainda nesta fase
- **Passos:**
  1. Verificar se `ConfirmProvider` está registrado em `providers.tsx`
  2. Verificar se hook `useConfirm` está disponível

- **Comportamento Esperado:**
  - Provider está registrado
  - Hook pode ser importado sem erros
  - Preparado para uso futuro

### 9. Formatação Unificada - Currency e Date

- **Passos:**
  1. Acesse `http://localhost:5173/` (página de pedidos)
  2. Verifique se valores monetários aparecem formatados como "R$ X.XXX,XX"
  3. Verifique se datas aparecem como "dd/MM/yyyy"

- **Comportamento Esperado:**
  - Valores monetários formatados corretamente (R$ 1.234,56)
  - Datas formatadas corretamente (25/12/2024)
  - Formatação consistente em todos os lugares

### 10. Phase 1.1 Ainda Passa (Auth, Protected Routes)

- **Passos:**
  1. Limpe localStorage e sessionStorage
  2. Acesse `http://localhost:5173/` diretamente
  3. Verifique se redireciona para `/login`
  4. Faça login com credenciais válidas
  5. Verifique se redireciona para home

- **Comportamento Esperado:**
  - Rotas protegidas ainda funcionam
  - Login ainda funciona
  - Navegação ainda funciona
  - Nenhuma regressão introduzida

## Checklist de Validação

### Customer Search
- [ ] Input mantém foco durante digitação (mobile + desktop)
- [ ] Debounce reduz chamadas à API (não uma por tecla)
- [ ] Seleção de cliente funciona
- [ ] Lista virtualiza quando > 50 itens (se aplicável)

### Orders Page
- [ ] Refresh ainda funciona
- [ ] Botões têm hit targets corretos (44px mínimo)
- [ ] Não há "click em div" para ações (elementos semânticos)

### Toast/Confirm
- [ ] Toast aparece corretamente
- [ ] Confirm provider está registrado (preparado)

### Formatação
- [ ] Currency formatada corretamente (R$ X.XXX,XX)
- [ ] Dates formatadas corretamente (dd/MM/yyyy)

### Compatibilidade
- [ ] Phase 1.1 ainda passa (auth, protected routes)
- [ ] Legado não é afetado

## Notas

- **Debounce threshold:** 300ms (configurável via `useDebouncedValue`)
- **Virtualization threshold:** 50 itens (quando usar `@tanstack/react-virtual`)
- **Touch target mínimo:** 44px (iOS/Android guidelines)

## Diferenças entre Swagger e Resposta Real

Se houver diferenças encontradas entre a documentação Swagger e as respostas reais da API, documentar aqui:

- (Nenhuma diferença encontrada até o momento)

