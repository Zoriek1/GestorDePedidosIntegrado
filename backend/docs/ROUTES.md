# Documentação de Rotas da API

Documentação completa dos endpoints da API REST do sistema Plante Uma Flor.

## Convenções

- **Autenticação**: Rotas marcadas com 🔒 requerem autenticação (`@requires_edit_auth`)
- **Formato**: Todas as respostas são JSON (exceto endpoints de comprovante/HTML)
- **Status Codes**: Seguem padrão HTTP (200, 201, 400, 401, 404, 500, 503)

## Blueprint: Pedidos (`/api/pedidos`)

### Listar Pedidos

**GET** `/api/pedidos`

Lista pedidos com filtros opcionais.

**Query Parameters**:
- `status` (opcional): Filtrar por status
- `data_inicio` (opcional): Data inicial (YYYY-MM-DD)
- `data_fim` (opcional): Data final (YYYY-MM-DD)
- `search` (opcional): Busca textual
- `filtrar_por_criacao` (opcional): Se `true`, filtra por data de criação

**Resposta**:
```json
{
  "success": true,
  "data": {
    "pedidos": [...],
    "total": 10
  }
}
```

### Criar Pedido

**POST** `/api/pedidos` 🔒

Cria um novo pedido.

**Body**: Objeto JSON com dados do pedido (cliente, produto, endereço, etc.)

**Resposta**: 201 Created com dados do pedido criado

### Obter Pedido

**GET** `/api/pedidos/<id>`

Obtém detalhes de um pedido específico.

**Resposta**:
```json
{
  "success": true,
  "data": {
    "pedido": {...}
  }
}
```

### Atualizar Pedido

**PUT** `/api/pedidos/<id>` 🔒

Atualiza dados de um pedido.

**Body**: Objeto JSON com campos a atualizar

### Deletar Pedido

**DELETE** `/api/pedidos/<id>` 🔒

Deleta um pedido (soft delete). Requer backup antes da operação (fail-closed P0.2).

**Resposta**: 200 OK ou 503 Service Unavailable se backup falhar

### Atualizar Status

**PUT/POST** `/api/pedidos/<id>/status` 🔒

Atualiza apenas o status de um pedido.

**Body**:
```json
{
  "status": "concluido"
}
```

### Gerar Comprovante

**GET** `/api/pedidos/<id>/comprovante`

Retorna HTML pronto para impressão do comprovante.

**Resposta**: HTML (text/html)

### Restaurar Pedido Deletado

**POST** `/api/pedidos/<id>/restore` 🔒

Restaura um pedido que foi soft-deleted.

### Listar Pedidos Deletados

**GET** `/api/pedidos/deleted`

Lista pedidos que foram soft-deleted.

## Blueprint: Clientes (`/api/clientes`)

### Listar Clientes

**GET** `/api/clientes`

Lista clientes com filtros e paginação.

**Query Parameters**:
- `search` (opcional): Busca por nome ou telefone
- `page` (opcional): Número da página (padrão: 1)
- `per_page` (opcional): Itens por página (padrão: 50)
- `stats` (opcional): Se `true`, inclui estatísticas

### Criar Cliente

**POST** `/api/clientes`

Cria novo cliente.

**Body**:
```json
{
  "nome": "João Silva",
  "telefone": "11999999999",
  "email": "joao@email.com",
  "observacoes": "Cliente VIP"
}
```

### Buscar Clientes (Autocomplete)

**GET** `/api/clientes/search`

Busca clientes por termo (usado em autocomplete).

**Query Parameters**:
- `q` (obrigatório): Termo de busca
- `limit` (opcional): Limite de resultados (padrão: 10)

### Obter Cliente

**GET** `/api/clientes/<id>`

Obtém detalhes de um cliente específico.

### Atualizar Cliente

**PUT** `/api/clientes/<id>` 🔒

Atualiza dados de um cliente.

### Deletar Cliente

**DELETE** `/api/clientes/<id>` 🔒

Deleta um cliente (hard delete). Requer backup antes da operação.

### Histórico de Pedidos do Cliente

**GET** `/api/clientes/<id>/pedidos`

Lista pedidos de um cliente específico.

### Endereços do Cliente

**GET** `/api/clientes/<id>/enderecos`

Lista endereços cadastrados de um cliente.

**POST** `/api/clientes/<id>/enderecos` 🔒

Adiciona novo endereço ao cliente.

**PUT** `/api/clientes/enderecos/<id>` 🔒

Atualiza endereço.

**DELETE** `/api/clientes/enderecos/<id>` 🔒

Deleta endereço. Requer backup antes da operação.

### Estatísticas de Clientes

**GET** `/api/clientes/stats`

Retorna estatísticas consolidadas de clientes.

## Blueprint: Rotas (`/api/pedidos`)

### Calcular Rota Otimizada

**POST** `/api/pedidos/rota-otimizada`

Calcula rota otimizada para múltiplos pedidos usando GraphHopper.

**Body**:
```json
{
  "pedido_ids": [1, 2, 3],
  "nome": "Rota Otimizada"
}
```

**Resposta**: Rota calculada com distância total, tempo total e sequência de pedidos

### Obter Rota Otimizada

**GET** `/api/pedidos/rota-otimizada/<id>`

Obtém detalhes de uma rota otimizada calculada.

## Blueprint: Autenticação (`/api/auth`)

### Login

**POST** `/api/auth/login`

Valida credenciais e retorna confirmação.

**Body**:
```json
{
  "username": "admin",
  "password": "senha"
}
```

**Resposta**:
```json
{
  "success": true,
  "message": "Login realizado com sucesso",
  "data": {
    "username": "admin"
  }
}
```

### Verificar Autenticação

**GET** `/api/auth/check`

Verifica se a requisição está autenticada (via Basic Auth header).

**Headers**: `Authorization: Basic <base64(user:pass)>`

**Resposta**:
```json
{
  "success": true,
  "data": {
    "authenticated": true
  }
}
```

## Blueprint: API Geral (`/api`)

### Health Check

**GET** `/api/health`

Verifica se a API está funcionando.

**Resposta**:
```json
{
  "status": "ok",
  "timestamp": "2026-01-04T10:00:00"
}
```

### Estatísticas

**GET** `/api/stats`

Retorna KPIs dos pedidos (total, agendados, atrasados, etc.).

### Status de Backup

**GET** `/api/backup/status`

Retorna estatísticas dos backups (total, tamanho, último backup).

### Fontes de Pedido

**GET** `/api/fontes-pedido`

Lista fontes ativas (WhatsApp, Site, Catálogo).

**POST** `/api/fontes-pedido` 🔒

Cria nova fonte.

**PUT** `/api/fontes-pedido/<id>` 🔒

Atualiza fonte.

**DELETE** `/api/fontes-pedido/<id>` 🔒

Deleta fonte. Requer backup antes da operação.

## Blueprint: Backup Admin (`/api/admin/backup`)

### Health do Backup

**GET** `/api/admin/backup/health` 🔒

Retorna health do sistema de backup (OK/WARN/FAIL).

**Resposta**:
```json
{
  "success": true,
  "health": "OK",
  "status": {...},
  "issues": []
}
```

## Autenticação

### Basic Auth

Todas as rotas marcadas com 🔒 requerem autenticação HTTP Basic.

**Header**: `Authorization: Basic <base64(username:password)>`

**Credenciais**: Configuradas via variáveis de ambiente:
- `EDIT_USERNAME` (padrão: `admin`)
- `EDIT_PASSWORD`

### Decorators

- `@requires_auth`: Requer autenticação básica (visualização)
- `@requires_edit_auth`: Requer autenticação para operações de escrita (criar/editar/deletar)

## Respostas de Erro

Formato padrão de erro:

```json
{
  "success": false,
  "error": "Mensagem de erro",
  "details": {...}  // Opcional
}
```

**Status Codes comuns**:
- `200 OK`: Sucesso
- `201 Created`: Recurso criado
- `400 Bad Request`: Erro de validação
- `401 Unauthorized`: Não autenticado
- `404 Not Found`: Recurso não encontrado
- `500 Internal Server Error`: Erro interno
- `503 Service Unavailable`: Backup necessário antes de operação destrutiva

---

**Última atualização**: 2026-01-04  
**Ver também**: [BLUEPRINTS.md](BLUEPRINTS.md) para organização de blueprints
