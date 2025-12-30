# Phase 0: Golden Flows - Checklist de Testes

Este documento contém o checklist de fluxos críticos ("Golden flows") para validar que a Phase 0 não introduziu regressões funcionais.

## Pré-requisitos

- Servidor backend rodando (Flask)
- Navegador moderno (Chrome, Edge, Firefox, Safari)
- Acesso ao sistema (local ou rede)

## Checklist de Fluxos

### 1. Login

- [ ] Acessar `/login`
- [ ] Preencher usuário e senha
- [ ] Clicar em "Entrar para Editar"
- [ ] Verificar que login é bem-sucedido
- [ ] Verificar que indicador de autenticação aparece na navegação
- [ ] Verificar que botão "Sair" aparece na navegação

**Mobile:**
- [ ] Verificar que campos de login são focáveis via teclado virtual
- [ ] Verificar que formulário submete corretamente no mobile

---

### 2. Carregar Painel Principal

- [ ] Após login, navegar para `/painel` (ou acessar diretamente)
- [ ] Verificar que painel carrega sem erros
- [ ] Verificar que estatísticas são exibidas (Total, Agendados, etc.)
- [ ] Verificar que lista de pedidos é renderizada
- [ ] Verificar que não há erros no console

---

### 3. Listar Pedidos

- [ ] No painel, verificar que pedidos são listados
- [ ] Verificar que cards de pedidos são exibidos corretamente
- [ ] Verificar que informações básicas estão visíveis (cliente, data, status)
- [ ] Verificar que pedidos são ordenados corretamente (mais próximos primeiro)

---

### 4. Filtrar Pedidos

- [ ] Usar filtro de status (ex.: "Agendado", "Produção", "Pronto")
- [ ] Verificar que lista é filtrada corretamente
- [ ] Usar filtro de data (ex.: "Hoje", "Esta Semana")
- [ ] Verificar que lista é filtrada por data
- [ ] Usar busca textual (campo de busca)
- [ ] Verificar que busca funciona em tempo real
- [ ] Limpar filtros e verificar que todos os pedidos voltam a aparecer

---

### 5. Abrir Detalhes do Pedido

- [ ] Clicar em um card de pedido no painel
- [ ] Verificar que modal de detalhes abre
- [ ] Verificar que todas as informações do pedido são exibidas
- [ ] Verificar que botões de ação estão disponíveis (Editar, Imprimir, etc.)
- [ ] Fechar modal e verificar que volta ao painel

---

### 6. Criar Novo Pedido

- [ ] Clicar em "Novo Pedido" (botão na navegação ou painel)
- [ ] Verificar que modal de seleção de fonte aparece (se aplicável)
- [ ] Selecionar fonte de pedido
- [ ] Preencher formulário completo:
  - [ ] Dados do cliente (nome, telefone)
  - [ ] Dados do destinatário
  - [ ] Tipo de pedido (Entrega/Retirada)
  - [ ] Produto e descrição
  - [ ] Data e horário de entrega
  - [ ] Endereço (se Entrega)
  - [ ] Mensagem e forma de pagamento
- [ ] Submeter formulário
- [ ] Verificar que pedido é criado com sucesso
- [ ] Verificar que notificação de sucesso aparece
- [ ] Verificar que pedido aparece no painel

---

### 7. Editar Pedido

- [ ] Abrir detalhes de um pedido existente
- [ ] Clicar em "Editar" (ou botão equivalente)
- [ ] Modificar campos do pedido
- [ ] Salvar alterações
- [ ] Verificar que pedido é atualizado
- [ ] Verificar que mudanças aparecem no painel

---

### 8. Buscar Clientes

- [ ] No formulário de pedido, começar a digitar nome de cliente
- [ ] Verificar que autocomplete aparece
- [ ] Selecionar cliente da lista
- [ ] Verificar que dados do cliente são preenchidos automaticamente

**Mobile (foco/teclado):**
- [ ] Abrir formulário em dispositivo mobile
- [ ] Tocar no campo de busca de cliente
- [ ] Verificar que teclado virtual aparece
- [ ] Digitar nome de cliente
- [ ] Verificar que autocomplete funciona com teclado virtual
- [ ] Selecionar cliente via toque
- [ ] Verificar que foco retorna corretamente após seleção

---

### 9. Imprimir/Exportar

- [ ] Abrir detalhes de um pedido
- [ ] Clicar em "Imprimir" (ou botão equivalente)
- [ ] Verificar que preview de impressão aparece
- [ ] Verificar que layout está correto para A4
- [ ] Fechar preview

**Se houver exportação:**
- [ ] Acessar funcionalidade de exportação (ex.: Google Sheets)
- [ ] Executar exportação
- [ ] Verificar que exportação é bem-sucedida

---

### 10. Offline: Abrir App Offline e Ver Lista Cacheada

- [ ] Com app online, carregar painel e aguardar carregamento completo
- [ ] Desconectar internet (modo avião ou desabilitar Wi-Fi/rede)
- [ ] Recarregar página (F5)
- [ ] Verificar que app carrega (Service Worker ativo)
- [ ] Verificar que lista de pedidos aparece (dados cacheados)
- [ ] Verificar que notificação de "offline" aparece

---

### 11. Offline: Criar/Editar Pedido Offline

- [ ] Com app offline (após passo 10)
- [ ] Criar novo pedido (seguir fluxo do passo 6)
- [ ] Verificar que pedido é salvo localmente
- [ ] Verificar que notificação indica que será sincronizado quando online
- [ ] Editar um pedido existente
- [ ] Verificar que alterações são salvas localmente

---

### 12. Reconnect: Sincronizar/Flush da Fila

- [ ] Após criar/editar pedidos offline (passo 11)
- [ ] Reconectar internet
- [ ] Verificar que notificação de "Conexão restaurada" aparece
- [ ] Aguardar sincronização automática (ou forçar refresh)
- [ ] Verificar que pedidos criados/editados offline aparecem no painel
- [ ] Verificar que notificação de sincronização aparece (ex.: "X pedido(s) sincronizado(s)")
- [ ] Verificar que pedidos pendentes foram removidos da fila local

**Comportamento esperado:**
- Sincronização automática ao voltar online
- Pedidos são enviados na ordem em que foram criados
- Erros de sincronização são reportados (mas não bloqueiam outros pedidos)

**Limitação conhecida (pré-existente):**
- Pedidos criados offline podem se perder devido a IDs hard-coded
- Este é um bug pré-existente, não introduzido pela Phase 0
- Não é regressão funcional da instrumentação

---

## Validação de Phase 0 (Instrumentação)

### Diagnóstico

- [ ] Pressionar `Ctrl+Shift+D` (ou `Cmd+Shift+D` no Mac)
- [ ] Verificar que modal de diagnóstico abre
- [ ] Verificar que informações do sistema são exibidas:
  - [ ] Versão do app
  - [ ] Status online/offline
  - [ ] Status do Service Worker
  - [ ] Status do IndexedDB
- [ ] Verificar que tabela de logs é exibida
- [ ] Verificar que logs contêm eventos de API, DB, etc.
- [ ] Clicar em "Exportar Logs"
- [ ] Verificar que arquivo JSON é baixado
- [ ] Abrir arquivo JSON e verificar que contém logs estruturados
- [ ] Clicar em "Limpar Logs" e confirmar
- [ ] Verificar que logs são limpos
- [ ] Fechar modal

**Mobile:**
- [ ] Verificar que diagnóstico pode ser acessado (botão discreto ou menu)
- [ ] Verificar que modal é responsivo e usável em mobile

---

## Notas

- Todos os fluxos devem funcionar **exatamente como antes** da Phase 0
- Erros devem aparecer nos logs de telemetria, mas não devem quebrar funcionalidades
- Performance não deve degradar significativamente
- Não deve haver regressões visuais (exceto UI de diagnóstico)

---

## Como Executar

1. Executar cada fluxo na ordem listada
2. Marcar checkbox quando passo for concluído com sucesso
3. Se algum passo falhar, documentar o erro e verificar logs de telemetria
4. Exportar logs e anexar em issue se necessário

---

**Última atualização:** Phase 0 - Freeze Behavior

