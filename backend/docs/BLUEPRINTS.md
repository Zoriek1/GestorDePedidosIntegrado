# Blueprints Flask

Este documento descreve a organização de Blueprints Flask no backend e como adicionar novos blueprints.

## Conceito de Blueprints

Blueprints são uma forma de organizar rotas Flask em módulos. Cada blueprint agrupa rotas relacionadas e pode ser registrado na aplicação principal.

**Vantagens**:
- Organização modular do código
- Fácil manutenção e escalabilidade
- Reutilização de rotas
- Prefixos de URL por módulo

## Blueprints Registrados

A aplicação registra os seguintes blueprints em `app/factory.py`:

### 1. `api_bp` - API Principal (Legado)

**URL Prefix**: `/api`

**Arquivo**: `app/routes/api.py`

**Status**: ⚠️ Legado (mantido para compatibilidade)

**Descrição**: Blueprint com rotas mistas antigas. Está sendo migrado para blueprints específicos por domínio.

**Principais rotas**:
- `/api/stats` - Estatísticas
- `/api/health` - Health check
- `/api/backup/status` - Status de backup
- `/api/fontes-pedido` - Fontes de pedido
- `/api/pedidos/*` - Rotas legadas de pedidos (sendo migradas)

### 2. `pedidos_bp` - Pedidos

**URL Prefix**: `/api/pedidos`

**Arquivo**: `app/routes/pedidos.py`

**Status**: ✅ Refatorado

**Descrição**: Gerencia todas as operações relacionadas a pedidos.

**Rotas principais**:
- `GET /api/pedidos` - Listar pedidos
- `POST /api/pedidos` - Criar pedido
- `GET /api/pedidos/<id>` - Obter pedido
- `PUT /api/pedidos/<id>` - Atualizar pedido
- `DELETE /api/pedidos/<id>` - Deletar pedido (soft delete)
- `PUT /api/pedidos/<id>/status` - Atualizar status
- `GET /api/pedidos/<id>/comprovante` - Gerar comprovante
- `POST /api/pedidos/<id>/restore` - Restaurar pedido deletado
- `GET /api/pedidos/deleted` - Listar pedidos deletados

### 3. `clientes_bp` - Clientes

**URL Prefix**: `/api/clientes`

**Arquivo**: `app/routes/clientes.py`

**Status**: ✅ Refatorado

**Descrição**: Gerencia clientes, endereços, histórico e métricas (LTV).

**Rotas principais**:
- `GET /api/clientes` - Listar clientes
- `POST /api/clientes` - Criar cliente
- `GET /api/clientes/search` - Buscar clientes (autocomplete)
- `GET /api/clientes/<id>` - Obter cliente
- `PUT /api/clientes/<id>` - Atualizar cliente
- `DELETE /api/clientes/<id>` - Deletar cliente
- `GET /api/clientes/<id>/pedidos` - Histórico de pedidos
- `GET /api/clientes/<id>/enderecos` - Endereços do cliente
- `POST /api/clientes/<id>/enderecos` - Adicionar endereço
- `GET /api/clientes/stats` - Estatísticas de clientes

### 4. `rotas_bp` - Rotas Otimizadas

**URL Prefix**: `/api/pedidos`

**Arquivo**: `app/routes/rotas.py`

**Status**: ✅ Refatorado

**Descrição**: Calcula e gerencia rotas otimizadas de entrega.

**Rotas principais**:
- `POST /api/pedidos/rota-otimizada` - Calcular rota otimizada
- `GET /api/pedidos/rota-otimizada/<id>` - Obter rota otimizada

### 5. `auth_bp` - Autenticação

**URL Prefix**: `/api/auth`

**Arquivo**: `app/routes/auth.py`

**Status**: ✅ Refatorado

**Descrição**: Endpoints de autenticação.

**Rotas principais**:
- `POST /api/auth/login` - Login
- `GET /api/auth/check` - Verificar autenticação

### 6. `backup_admin_bp` - Backup (Admin)

**URL Prefix**: `/api/admin/backup`

**Arquivo**: `app/routes/develop/backup.py`

**Status**: ✅ Novo

**Descrição**: Endpoints administrativos para gerenciamento de backup.

**Rotas principais**:
- `GET /api/admin/backup/health` - Health do sistema de backup

## Organização e Responsabilidades

### Estrutura de um Blueprint

```python
from flask import Blueprint, request, jsonify
from app.repositories.pedido_repository import PedidoRepository
from app.middleware import requires_edit_auth

# Criar blueprint
pedidos_bp = Blueprint('pedidos', __name__, url_prefix='/api/pedidos')

# Instanciar repositórios/serviços
pedido_repo = PedidoRepository()

# Definir rotas
@pedidos_bp.route('', methods=['GET'])
def listar_pedidos():
    # Lógica da rota
    pass

@pedidos_bp.route('/<int:pedido_id>', methods=['GET'])
def obter_pedido(pedido_id):
    # Lógica da rota
    pass
```

### Princípios de Organização

1. **Um blueprint por domínio**: Cada entidade/feature tem seu próprio blueprint
2. **URL prefix consistente**: Seguir padrão `/api/<recurso>`
3. **Rotas RESTful**: Usar métodos HTTP adequados (GET, POST, PUT, DELETE)
4. **Autenticação seletiva**: Usar decorators `@requires_auth` ou `@requires_edit_auth`
5. **Schemas para validação**: Validar entrada com schemas (Marshmallow)

## Como Adicionar um Novo Blueprint

### Passo 1: Criar arquivo do blueprint

Criar arquivo em `app/routes/novo_recurso.py`:

```python
# -*- coding: utf-8 -*-
"""
Rotas de Novo Recurso - Blueprint para endpoints de novo recurso
"""
from flask import Blueprint, request
from app.schemas.common import success_response, error_response
from app.middleware import requires_edit_auth

novo_recurso_bp = Blueprint('novo_recurso', __name__, url_prefix='/api/novo-recurso')

@novo_recurso_bp.route('', methods=['GET'])
def listar_recursos():
    """Lista recursos"""
    try:
        # Lógica aqui
        return success_response({'recursos': []})
    except Exception as e:
        return error_response(f'Erro: {str(e)}', 500)
```

### Passo 2: Registrar no factory

Adicionar em `app/factory.py`:

```python
# Na função create_app(), dentro do with app.app_context():
from app.routes.novo_recurso import novo_recurso_bp

# Registrar blueprint
app.register_blueprint(novo_recurso_bp)
```

### Passo 3: (Opcional) Criar Repository e Schema

Se for uma nova entidade:
- Criar `app/repositories/novo_recurso_repository.py`
- Criar `app/schemas/novo_recurso_schema.py`
- Criar `app/models/novo_recurso.py` (se necessário)

## Registro de Blueprints

Todos os blueprints são registrados em `app/factory.py` na função `create_app()`:

```python
with app.app_context():
    from app.routes.api import api_bp
    from app.routes.pedidos import pedidos_bp
    from app.routes.clientes import clientes_bp
    from app.routes.rotas import rotas_bp
    from app.routes.auth import auth_bp
    from app.routes.develop.backup import backup_admin_bp
    
    # Registrar blueprints
    app.register_blueprint(api_bp)
    app.register_blueprint(pedidos_bp)
    app.register_blueprint(clientes_bp)
    app.register_blueprint(rotas_bp)
    app.register_blueprint(auth_bp)
    app.register_blueprint(backup_admin_bp)
```

**Ordem importa**: Blueprints mais específicos devem ser registrados antes dos mais genéricos (catch-all).

---

**Última atualização**: 2026-01-04
