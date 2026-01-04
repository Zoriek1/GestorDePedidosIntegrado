# Funcionalidades

Este documento descreve as funcionalidades atuais do sistema e o roadmap de funcionalidades futuras.

## Funcionalidades Atuais

### Autenticação

- **Login**: Autenticação HTTP Basic
- **Persistência**: Credenciais armazenadas em `localStorage` ou `sessionStorage`
- **Auto-logout**: Logout automático em caso de 401/403
- **Rotas protegidas**: Rotas protegidas com `RequireAuth`

**Localização**: `src/features/auth/`

### Pedidos

#### Gestão de Pedidos

- **Listagem**: Lista de pedidos com filtros (status, data, busca)
- **Criação**: Wizard multi-step para criação de pedidos
- **Edição**: Edição de pedidos existentes
- **Visualização**: Página de detalhes do pedido
- **Status**: Atualização de status de pedidos
- **Comprovante**: Geração de comprovante para impressão

#### Wizard de Criação

Wizard em 4 passos:
1. **Cliente**: Seleção/criação de cliente
2. **Entrega**: Endereço e dados de entrega
3. **Produto**: Produto, valor e observações
4. **Pagamento**: Forma de pagamento e finalização

**Localização**: `src/features/pedidos/`

### Clientes (CRM)

- **Listagem**: Lista de clientes com busca e paginação
- **Criação**: Criação de novos clientes
- **Visualização**: Detalhes do cliente com histórico
- **Edição**: Edição de dados do cliente
- **Endereços**: Gestão de endereços do cliente
- **Métricas**: LTV (Lifetime Value) e estatísticas

**Localização**: `src/features/customers/`

### Vendas

- **Estatísticas**: KPIs de vendas (total, agendados, atrasados)
- **Listagem**: Lista de vendas por período
- **Filtros**: Filtros por data de criação

**Localização**: `src/features/sales/`

### Rotas

- **Otimização**: Cálculo de rotas otimizadas para entrega
- **Visualização**: Visualização de rotas calculadas

**Localização**: `src/features/rotas/`

### Fontes de Pedido

- **Gestão**: CRUD de fontes de pedido (WhatsApp, Site, Catálogo, etc)

**Localização**: `src/features/fontes/`

### Offline

- **Cache**: Cache de dados para uso offline
- **Outbox**: Fila de operações para sincronização
- **Diagnósticos**: Página de diagnósticos offline (dev)

**Localização**: `src/features/offline/`, `src/lib/offline/`

### PWA

- **Service Worker**: Cache de assets e funcionalidade offline
- **Manifest**: Instalação como app nativo
- **Offline Support**: Funcionalidade completa offline

Ver [PWA.md](PWA.md) para detalhes.

## Roadmap de Funcionalidades Futuras

### Curto Prazo

- [ ] Notificações push
- [ ] Exportação de relatórios (PDF/Excel)
- [ ] Dashboard com gráficos
- [ ] Filtros avançados de busca
- [ ] Atalhos de teclado

### Médio Prazo

- [ ] Sincronização em tempo real
- [ ] Multi-usuário com permissões
- [ ] Histórico de alterações
- [ ] Templates de pedidos
- [ ] Integração com WhatsApp Web API

### Longo Prazo

- [ ] App mobile nativo (React Native)
- [ ] Analytics avançado
- [ ] IA para otimização de rotas
- [ ] Integração com sistemas externos (ERP, etc)
- [ ] Multi-tenant

---

**Última atualização**: 2026-01-04
