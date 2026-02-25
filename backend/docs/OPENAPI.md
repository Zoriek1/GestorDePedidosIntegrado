# Documentação OpenAPI/Swagger

Este documento descreve o estado atual da documentação OpenAPI e o roadmap para implementação completa.

## Estado Atual

O sistema utiliza **Flask-Smorest** para documentação OpenAPI. A implementação atual documenta os endpoints prioritários usados pelo frontend.

### Acesso

- **Swagger UI**: `http://localhost:5000/docs/swagger`
- **ReDoc**: `http://localhost:5000/docs/redoc` (se disponível)
- **OpenAPI JSON**: `http://localhost:5000/docs/openapi.json`

### Endpoints Documentados

Atualmente, os seguintes endpoints estão documentados no Swagger:

1. **GET** `/api/health` - Health Check
2. **GET** `/api/auth/check` - Verificar Autenticação
3. **GET** `/api/pedidos` - Listar Pedidos
4. **GET** `/api/stats` - Obter Estatísticas
5. **GET** `/api/clientes/search` - Buscar Clientes

### Localização do Código

- **Configuração**: `app/openapi/__init__.py`
- **Blueprint**: `app/openapi/blueprint.py`
- **Schemas**: `app/openapi/schemas.py`

### Configuração

A documentação OpenAPI é inicializada em `app/factory.py`:

```python
from app.openapi import init_openapi

try:
    init_openapi(app)
    print("[OPENAPI] Swagger UI disponível em /docs/swagger")
except ImportError:
    # flask-smorest não instalado, continuar sem documentação
    print("[AVISO] flask-smorest não instalado. Swagger UI não estará disponível.")
```

## Como Adicionar Documentação OpenAPI

### 1. Definir Schema

Criar schema em `app/openapi/schemas.py`:

```python
from marshmallow import Schema, fields

class NovoRecursoResponseSchema(Schema):
    id = fields.Int()
    nome = fields.Str()
    # ... outros campos
```

### 2. Documentar Endpoint no Blueprint

Adicionar documentação no blueprint OpenAPI (`app/openapi/blueprint.py`):

```python
from app.openapi.schemas import NovoRecursoResponseSchema

@blp.route('/api/novo-recurso', methods=['GET'])
@blp.doc(
    summary='Listar Recursos',
    description='Lista todos os recursos disponíveis',
    tags=['Recursos']
)
@blp.response(200, NovoRecursoResponseSchema(many=True))
def novo_recurso_list_doc(**kwargs):
    """Listar Recursos"""
    from app.routes.novo_recurso import listar_recursos
    return listar_recursos()
```

### 3. Registrar no Blueprint

O blueprint já está registrado automaticamente quando a aplicação inicia.

## Estrutura de Schemas

Schemas são definidos usando **Marshmallow** em `app/openapi/schemas.py`:

```python
from marshmallow import Schema, fields

class HealthResponseSchema(Schema):
    status = fields.Str()
    timestamp = fields.DateTime()

class PedidosResponseSchema(Schema):
    success = fields.Bool()
    data = fields.Dict()
```

## Roadmap para Implementação Completa

### Fase 1: Endpoints Prioritários ✅ (Concluído)

- [x] Health check
- [x] Autenticação
- [x] Listar pedidos
- [x] Estatísticas
- [x] Buscar clientes

### Fase 2: Endpoints de Pedidos (Planejado)

- [ ] Criar pedido (POST /api/pedidos)
- [ ] Obter pedido (GET /api/pedidos/<id>)
- [ ] Atualizar pedido (PUT /api/pedidos/<id>)
- [ ] Deletar pedido (DELETE /api/pedidos/<id>)
- [ ] Atualizar status (PUT /api/pedidos/<id>/status)
- [ ] Gerar comprovante (GET /api/pedidos/<id>/comprovante)

### Fase 3: Endpoints de Clientes (Planejado)

- [ ] CRUD completo de clientes
- [ ] Endereços de clientes
- [ ] Histórico de pedidos
- [ ] Estatísticas de clientes

### Fase 4: Outros Endpoints (Planejado)

- [ ] Rotas otimizadas
- [ ] Fontes de pedido
- [ ] Backup admin
- [ ] Endpoints de desenvolvimento

## Exemplos de Schemas

### Query Parameters

```python
class PedidosQuerySchema(Schema):
    status = fields.Str(required=False)
    data_inicio = fields.Date(required=False)
    data_fim = fields.Date(required=False)
    search = fields.Str(required=False)
```

### Request Body

```python
class CriarPedidoSchema(Schema):
    cliente = fields.Str(required=True)
    destinatario = fields.Str(required=True)
    produto = fields.Str(required=True)
    # ... outros campos
```

### Response

```python
class PedidosResponseSchema(Schema):
    success = fields.Bool()
    data = fields.Dict()
    message = fields.Str(required=False)
```

## Dependências

**Flask-Smorest**: Biblioteca para documentação OpenAPI no Flask

**Instalação**:
```bash
pip install flask-smorest
```

**Requisitos**:
- Flask-Smorest requer que `flask-smorest` esteja instalado
- Se não estiver instalado, a aplicação continua funcionando normalmente (sem Swagger UI)

## Notas

- A documentação OpenAPI é **opcional**: Se `flask-smorest` não estiver instalado, a aplicação funciona normalmente
- Endpoints documentados continuam funcionando normalmente (a documentação apenas documenta os endpoints reais)
- A documentação pode ser evoluída incrementalmente, adicionando endpoints conforme necessário

---

**Última atualização**: 2026-01-04  
**Ver também**: [ROUTES.md](ROUTES.md) para documentação completa de endpoints
