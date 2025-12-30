# Documentação da API

Documentação completa da API REST do sistema Plante Uma Flor.

---

## Base URL

```
http://localhost:5000/api
https://localhost:5000/api
```

---

## Autenticação

Alguns endpoints requerem autenticação HTTP Basic.

**Configuração:**
- Usuário: `admin` (padrão)
- Senha: Configurada via `ADMIN_PASSWORD` no `.env`

**Uso:**
```http
Authorization: Basic <base64(username:password)>
```

Veja [configuration.md](configuration.md) para mais detalhes.

---

## Swagger UI

Quando implementado, a documentação interativa estará disponível em:

```
http://localhost:5000/docs/swagger
```

---

## Endpoints Principais

### Health Check

```http
GET /api/health
```

**Resposta:**
```json
{
  "success": true,
  "status": "healthy",
  "message": "API funcionando normalmente"
}
```

---

### Autenticação

#### Login

```http
POST /api/auth/login
Content-Type: application/json
```

**Body:**
```json
{
  "username": "admin",
  "password": "senha"
}
```

**Resposta:**
```json
{
  "success": true,
  "data": {
    "username": "admin"
  },
  "message": "Login realizado com sucesso"
}
```

#### Verificar Autenticação

```http
GET /api/auth/check
Authorization: Basic <credentials>
```

**Resposta:**
```json
{
  "success": true,
  "data": {
    "authenticated": true
  },
  "message": "Autenticado"
}
```

---

### Pedidos

#### Listar Pedidos

```http
GET /api/pedidos
```

**Query Parameters:**
- `status` (opcional): Filtrar por status
- `data_inicio` (opcional): Data inicial (YYYY-MM-DD)
- `data_fim` (opcional): Data final (YYYY-MM-DD)
- `search` (opcional): Busca textual

**Resposta:**
```json
{
  "success": true,
  "data": {
    "pedidos": [
      {
        "id": 1,
        "cliente": "João Silva",
        "telefone_cliente": "(62) 99999-9999",
        "destinatario": "Maria Santos",
        "produto": "Buquê de Rosas",
        "dia_entrega": "2024-12-15",
        "horario": "14:30",
        "status": "agendado",
        "distancia_km": 5.2,
        "taxa_entrega": 15.00
      }
    ],
    "total": 1
  }
}
```

#### Obter Pedido

```http
GET /api/pedidos/:id
```

**Resposta:**
```json
{
  "success": true,
  "data": {
    "pedido": {
      "id": 1,
      "cliente": "João Silva",
      // ... campos completos
    }
  }
}
```

#### Criar Pedido

```http
POST /api/pedidos
Content-Type: application/json
Authorization: Basic <credentials>
```

**Body:**
```json
{
  "cliente": "João Silva",
  "telefone_cliente": "(62) 99999-9999",
  "destinatario": "Maria Santos",
  "tipo_pedido": "Entrega",
  "produto": "Buquê de Rosas",
  "flores_cor": "Rosas vermelhas",
  "valor": "150.00",
  "dia_entrega": "2024-12-15",
  "horario": "14:30",
  "cep": "74000-000",
  "rua": "Rua Exemplo",
  "numero": "123",
  "bairro": "Centro",
  "cidade": "Goiânia",
  "mensagem": "Parabéns!",
  "pagamento": "Cartão"
}
```

**Resposta:**
```json
{
  "success": true,
  "data": {
    "pedido_id": 1,
    "pedido": { /* objeto completo */ }
  },
  "message": "Pedido criado com sucesso"
}
```

#### Atualizar Pedido

```http
PUT /api/pedidos/:id
Content-Type: application/json
Authorization: Basic <credentials>
```

**Body:** Mesmo formato do criar pedido (campos opcionais)

#### Atualizar Status

```http
PUT /api/pedidos/:id/status
Content-Type: application/json
Authorization: Basic <credentials>
```

**Body:**
```json
{
  "status": "producao"
}
```

**Status válidos:**
- `agendado`
- `em_producao`
- `pronto_entrega`
- `em_rota`
- `pronto_retirada`
- `concluido`

#### Deletar Pedido

```http
DELETE /api/pedidos/:id
Authorization: Basic <credentials>
```

---

### Estatísticas

#### Obter Estatísticas

```http
GET /api/stats
```

**Resposta:**
```json
{
  "success": true,
  "data": {
    "stats": {
      "total": 100,
      "agendados": 20,
      "producao": 15,
      "prontos": 10,
      "entregues": 50,
      "cancelados": 5,
      "atrasados": 3
    }
  }
}
```

#### Pedidos Atrasados

```http
GET /api/pedidos/overdue
```

---

### Clientes

#### Buscar Clientes

```http
GET /api/clientes/buscar?q=joao
```

**Query Parameters:**
- `q` (obrigatório): Termo de busca
- `limit` (opcional): Limite de resultados (padrão: 10)

**Resposta:**
```json
{
  "success": true,
  "data": {
    "clientes": [
      {
        "id": 1,
        "nome": "João Silva",
        "telefone": "(62) 99999-9999"
      }
    ],
    "total": 1
  }
}
```

---

### Distâncias e Rotas

#### Calcular Distância de um Pedido

```http
GET /api/pedidos/:id/distancia
```

**Query Parameters:**
- `force_recalc` (opcional): Forçar recálculo (padrão: false)

**Resposta:**
```json
{
  "success": true,
  "pedido_id": 1,
  "distancia_km": 5.2,
  "duracao_min": 12,
  "metodo": "graphhopper",
  "cached": false
}
```

#### Calcular Distâncias em Lote

```http
POST /api/pedidos/calcular-distancias
Content-Type: application/json
```

**Body:**
```json
{
  "pedido_ids": [1, 2, 3],
  "force_recalc": false
}
```

#### Calcular Taxa de Entrega

```http
POST /api/pedidos/:id/calcular-taxa
```

---

### Rotas Otimizadas

#### Criar Rota Otimizada

```http
POST /api/pedidos/rota-otimizada
Content-Type: application/json
```

**Body:**
```json
{
  "pedido_ids": [1, 2, 3],
  "nome": "Rota Otimizada"
}
```

#### Obter Rota Otimizada

```http
GET /api/pedidos/rota-otimizada/:rota_id
```

---

## Códigos de Status HTTP

- `200 OK`: Requisição bem-sucedida
- `201 Created`: Recurso criado com sucesso
- `400 Bad Request`: Dados inválidos
- `401 Unauthorized`: Não autenticado
- `403 Forbidden`: Sem permissão
- `404 Not Found`: Recurso não encontrado
- `429 Too Many Requests`: Rate limit excedido
- `500 Internal Server Error`: Erro no servidor

---

## Formato de Resposta

### Sucesso

```json
{
  "success": true,
  "data": { /* dados */ },
  "message": "Mensagem opcional"
}
```

### Erro

```json
{
  "success": false,
  "error": "Mensagem de erro",
  "details": { /* detalhes opcionais */ }
}
```

---

## Rate Limiting

- **Limite por minuto**: 60 requisições
- **Limite por hora**: 1000 requisições

Quando excedido, retorna `429 Too Many Requests` com header `Retry-After`.

---

## Mapa Completo de Rotas

Para ver todas as rotas disponíveis, consulte [routes.md](routes.md) (auto-gerado).

---

## Exemplos de Uso

### JavaScript (Fetch API)

```javascript
// GET request
const response = await fetch('/api/pedidos', {
  headers: {
    'Authorization': 'Basic ' + btoa('admin:senha')
  }
});
const data = await response.json();

// POST request
const response = await fetch('/api/pedidos', {
  method: 'POST',
  headers: {
    'Content-Type': 'application/json',
    'Authorization': 'Basic ' + btoa('admin:senha')
  },
  body: JSON.stringify({
    cliente: 'João Silva',
    // ... outros campos
  })
});
```

### Python (requests)

```python
import requests

# GET request
response = requests.get(
    'http://localhost:5000/api/pedidos',
    auth=('admin', 'senha')
)
data = response.json()

# POST request
response = requests.post(
    'http://localhost:5000/api/pedidos',
    json={
        'cliente': 'João Silva',
        # ... outros campos
    },
    auth=('admin', 'senha')
)
```

---

## Recursos Adicionais

- [Routes](routes.md) - Mapa completo de rotas
- [Configuration](configuration.md) - Variáveis de ambiente
- [Architecture](architecture.md) - Arquitetura do sistema
- [Dev Guide](dev.md) - Guia de desenvolvimento

---

**Última atualização:** Dezembro 2024


Documentação completa da API REST do sistema Plante Uma Flor.

---

## Base URL

```
http://localhost:5000/api
https://localhost:5000/api
```

---

## Autenticação

Alguns endpoints requerem autenticação HTTP Basic.

**Configuração:**
- Usuário: `admin` (padrão)
- Senha: Configurada via `ADMIN_PASSWORD` no `.env`

**Uso:**
```http
Authorization: Basic <base64(username:password)>
```

Veja [configuration.md](configuration.md) para mais detalhes.

---

## Swagger UI

Quando implementado, a documentação interativa estará disponível em:

```
http://localhost:5000/docs/swagger
```

---

## Endpoints Principais

### Health Check

```http
GET /api/health
```

**Resposta:**
```json
{
  "success": true,
  "status": "healthy",
  "message": "API funcionando normalmente"
}
```

---

### Autenticação

#### Login

```http
POST /api/auth/login
Content-Type: application/json
```

**Body:**
```json
{
  "username": "admin",
  "password": "senha"
}
```

**Resposta:**
```json
{
  "success": true,
  "data": {
    "username": "admin"
  },
  "message": "Login realizado com sucesso"
}
```

#### Verificar Autenticação

```http
GET /api/auth/check
Authorization: Basic <credentials>
```

**Resposta:**
```json
{
  "success": true,
  "data": {
    "authenticated": true
  },
  "message": "Autenticado"
}
```

---

### Pedidos

#### Listar Pedidos

```http
GET /api/pedidos
```

**Query Parameters:**
- `status` (opcional): Filtrar por status
- `data_inicio` (opcional): Data inicial (YYYY-MM-DD)
- `data_fim` (opcional): Data final (YYYY-MM-DD)
- `search` (opcional): Busca textual

**Resposta:**
```json
{
  "success": true,
  "data": {
    "pedidos": [
      {
        "id": 1,
        "cliente": "João Silva",
        "telefone_cliente": "(62) 99999-9999",
        "destinatario": "Maria Santos",
        "produto": "Buquê de Rosas",
        "dia_entrega": "2024-12-15",
        "horario": "14:30",
        "status": "agendado",
        "distancia_km": 5.2,
        "taxa_entrega": 15.00
      }
    ],
    "total": 1
  }
}
```

#### Obter Pedido

```http
GET /api/pedidos/:id
```

**Resposta:**
```json
{
  "success": true,
  "data": {
    "pedido": {
      "id": 1,
      "cliente": "João Silva",
      // ... campos completos
    }
  }
}
```

#### Criar Pedido

```http
POST /api/pedidos
Content-Type: application/json
Authorization: Basic <credentials>
```

**Body:**
```json
{
  "cliente": "João Silva",
  "telefone_cliente": "(62) 99999-9999",
  "destinatario": "Maria Santos",
  "tipo_pedido": "Entrega",
  "produto": "Buquê de Rosas",
  "flores_cor": "Rosas vermelhas",
  "valor": "150.00",
  "dia_entrega": "2024-12-15",
  "horario": "14:30",
  "cep": "74000-000",
  "rua": "Rua Exemplo",
  "numero": "123",
  "bairro": "Centro",
  "cidade": "Goiânia",
  "mensagem": "Parabéns!",
  "pagamento": "Cartão"
}
```

**Resposta:**
```json
{
  "success": true,
  "data": {
    "pedido_id": 1,
    "pedido": { /* objeto completo */ }
  },
  "message": "Pedido criado com sucesso"
}
```

#### Atualizar Pedido

```http
PUT /api/pedidos/:id
Content-Type: application/json
Authorization: Basic <credentials>
```

**Body:** Mesmo formato do criar pedido (campos opcionais)

#### Atualizar Status

```http
PUT /api/pedidos/:id/status
Content-Type: application/json
Authorization: Basic <credentials>
```

**Body:**
```json
{
  "status": "producao"
}
```

**Status válidos:**
- `agendado`
- `em_producao`
- `pronto_entrega`
- `em_rota`
- `pronto_retirada`
- `concluido`

#### Deletar Pedido

```http
DELETE /api/pedidos/:id
Authorization: Basic <credentials>
```

---

### Estatísticas

#### Obter Estatísticas

```http
GET /api/stats
```

**Resposta:**
```json
{
  "success": true,
  "data": {
    "stats": {
      "total": 100,
      "agendados": 20,
      "producao": 15,
      "prontos": 10,
      "entregues": 50,
      "cancelados": 5,
      "atrasados": 3
    }
  }
}
```

#### Pedidos Atrasados

```http
GET /api/pedidos/overdue
```

---

### Clientes

#### Buscar Clientes

```http
GET /api/clientes/buscar?q=joao
```

**Query Parameters:**
- `q` (obrigatório): Termo de busca
- `limit` (opcional): Limite de resultados (padrão: 10)

**Resposta:**
```json
{
  "success": true,
  "data": {
    "clientes": [
      {
        "id": 1,
        "nome": "João Silva",
        "telefone": "(62) 99999-9999"
      }
    ],
    "total": 1
  }
}
```

---

### Distâncias e Rotas

#### Calcular Distância de um Pedido

```http
GET /api/pedidos/:id/distancia
```

**Query Parameters:**
- `force_recalc` (opcional): Forçar recálculo (padrão: false)

**Resposta:**
```json
{
  "success": true,
  "pedido_id": 1,
  "distancia_km": 5.2,
  "duracao_min": 12,
  "metodo": "graphhopper",
  "cached": false
}
```

#### Calcular Distâncias em Lote

```http
POST /api/pedidos/calcular-distancias
Content-Type: application/json
```

**Body:**
```json
{
  "pedido_ids": [1, 2, 3],
  "force_recalc": false
}
```

#### Calcular Taxa de Entrega

```http
POST /api/pedidos/:id/calcular-taxa
```

---

### Rotas Otimizadas

#### Criar Rota Otimizada

```http
POST /api/pedidos/rota-otimizada
Content-Type: application/json
```

**Body:**
```json
{
  "pedido_ids": [1, 2, 3],
  "nome": "Rota Otimizada"
}
```

#### Obter Rota Otimizada

```http
GET /api/pedidos/rota-otimizada/:rota_id
```

---

## Códigos de Status HTTP

- `200 OK`: Requisição bem-sucedida
- `201 Created`: Recurso criado com sucesso
- `400 Bad Request`: Dados inválidos
- `401 Unauthorized`: Não autenticado
- `403 Forbidden`: Sem permissão
- `404 Not Found`: Recurso não encontrado
- `429 Too Many Requests`: Rate limit excedido
- `500 Internal Server Error`: Erro no servidor

---

## Formato de Resposta

### Sucesso

```json
{
  "success": true,
  "data": { /* dados */ },
  "message": "Mensagem opcional"
}
```

### Erro

```json
{
  "success": false,
  "error": "Mensagem de erro",
  "details": { /* detalhes opcionais */ }
}
```

---

## Rate Limiting

- **Limite por minuto**: 60 requisições
- **Limite por hora**: 1000 requisições

Quando excedido, retorna `429 Too Many Requests` com header `Retry-After`.

---

## Mapa Completo de Rotas

Para ver todas as rotas disponíveis, consulte [routes.md](routes.md) (auto-gerado).

---

## Exemplos de Uso

### JavaScript (Fetch API)

```javascript
// GET request
const response = await fetch('/api/pedidos', {
  headers: {
    'Authorization': 'Basic ' + btoa('admin:senha')
  }
});
const data = await response.json();

// POST request
const response = await fetch('/api/pedidos', {
  method: 'POST',
  headers: {
    'Content-Type': 'application/json',
    'Authorization': 'Basic ' + btoa('admin:senha')
  },
  body: JSON.stringify({
    cliente: 'João Silva',
    // ... outros campos
  })
});
```

### Python (requests)

```python
import requests

# GET request
response = requests.get(
    'http://localhost:5000/api/pedidos',
    auth=('admin', 'senha')
)
data = response.json()

# POST request
response = requests.post(
    'http://localhost:5000/api/pedidos',
    json={
        'cliente': 'João Silva',
        # ... outros campos
    },
    auth=('admin', 'senha')
)
```

---

## Recursos Adicionais

- [Routes](routes.md) - Mapa completo de rotas
- [Configuration](configuration.md) - Variáveis de ambiente
- [Architecture](architecture.md) - Arquitetura do sistema
- [Dev Guide](dev.md) - Guia de desenvolvimento

---

**Última atualização:** Dezembro 2024

