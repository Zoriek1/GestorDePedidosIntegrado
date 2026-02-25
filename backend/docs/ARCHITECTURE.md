# Arquitetura do Backend

Este documento descreve a arquitetura do backend do sistema Plante Uma Flor, incluindo padrões de design, estrutura de pastas e fluxo de dependências.

## Visão Geral

O backend utiliza **Python 3 + Flask** com banco de dados **SQLite** (gerenciado via **SQLAlchemy**). A arquitetura evoluiu de scripts monolíticos para uma estrutura em camadas seguindo princípios de **Clean Architecture** e **Service-Oriented Architecture (SOA)**.

## Padrões de Design

### Repository Pattern

Abstração completa do acesso a dados. O código de negócio não toca no `db.session` diretamente.

**Localização**: `backend/app/repositories/`

**Responsabilidades**:
- CRUD básico (create, read, update, delete)
- Queries complexas com filtros
- Conversão entre Models e DTOs
- Soft delete (quando aplicável)

**Exemplo**:
```python
# Repository
pedido_repo = PedidoRepository()
pedido = pedido_repo.get_by_id(pedido_id)

# Route usa o Repository
@pedidos_bp.route('/<int:pedido_id>', methods=['GET'])
def obter_pedido(pedido_id):
    pedido = pedido_repo.get_by_id(pedido_id)
    return success_response({'pedido': pedido.to_dict()})
```

### Command Pattern

Encapsulamento de ações complexas que envolvem múltiplas etapas ou regras de negócio.

**Localização**: `backend/app/commands/`

**Uso**: Ações que combinam lógica de negócio com view/output (ex: gerar comprovante de pedido).

**Exemplo**: `GerarComprovanteCommand` - Busca dados, valida regras, gera HTML pronto para impressão.

### Service-Oriented Architecture

Separação clara entre camadas:

1. **Routes (Controllers)**: Recebem HTTP requests, validam entrada, chamam Services/Repositories
2. **Services**: Lógica de negócio pura e integrações externas
3. **Repositories**: Acesso a dados
4. **Models**: Entidades do domínio

## Estrutura de Pastas

```
backend/app/
├── models/          # Entidades do domínio (SQLAlchemy)
│   ├── pedido.py
│   ├── cliente.py
│   ├── rota_otimizada.py
│   ├── audit_log.py
│   └── ...
│
├── repositories/    # Camada de acesso a dados (Repository Pattern)
│   ├── base_repository.py
│   ├── pedido_repository.py
│   ├── cliente_repository.py
│   └── ...
│
├── services/        # Lógica de negócio e integrações externas
│   ├── distancia.py
│   ├── taxa_entrega.py
│   ├── graphhopper.py
│   └── ...
│
├── routes/          # Controllers HTTP (Blueprints)
│   ├── pedidos.py
│   ├── clientes.py
│   ├── rotas.py
│   ├── auth.py
│   ├── api.py       # [LEGADO] Rotas mistas antigas
│   └── develop/     # Endpoints de desenvolvimento
│
├── commands/        # Command Pattern (ações encapsuladas)
│   └── gerar_comprovante_command.py
│
├── schemas/         # DTOs e serialização (Marshmallow)
│   ├── pedido_schema.py
│   ├── cliente_schema.py
│   └── common.py
│
├── utils/           # Helpers e utilitários
│   ├── backup_helper.py
│   ├── encryption.py
│   ├── audit_logger.py
│   └── destructive_action_guard.py
│
├── openapi/         # Documentação OpenAPI/Swagger
│   ├── __init__.py
│   ├── blueprint.py
│   └── schemas.py
│
├── factory.py       # Application Factory
├── config.py        # Configurações
├── extensions.py    # Extensões Flask (db, migrate)
├── middleware.py    # Middleware (auth, rate limit)
├── errors.py        # Error handlers
└── cors.py          # CORS configuration
```

## Fluxo de Dependências

O sistema utiliza injeção de dependência manual (instanciação direta controlada) para manter a simplicidade, mas respeita a inversão de controle.

### Fluxo Padrão de uma Requisição

```
1. Route (Controller)
   ├─ Recebe Request HTTP (JSON/Params)
   ├─ Valida entrada (schemas)
   ├─ Depende de: Repositories, Commands ou Services
   └─ Não faz: Queries SQL diretas ou lógica complexa
   
2. Command / Service
   ├─ Processa regra de negócio
   ├─ Depende de: Repositories
   └─ Exemplo: GerarComprovanteCommand valida e gera HTML
   
3. Repository
   ├─ Executa query no banco
   ├─ Depende de: Models (SQLAlchemy)
   └─ Retorna: Objetos de Domínio (Pedido, Cliente) ou Listas
   
4. Model
   └─ Entidade rica com métodos de negócio (to_dict(), is_overdue(), etc)
```

### Exemplo Completo

```python
# Route (app/routes/pedidos.py)
@pedidos_bp.route('/<int:pedido_id>', methods=['GET'])
def obter_pedido(pedido_id):
    pedido = pedido_repo.get_by_id(pedido_id)  # ← Repository
    return success_response({'pedido': pedido.to_dict()})  # ← Model method

# Repository (app/repositories/pedido_repository.py)
def get_by_id(self, pedido_id: int) -> Optional[Pedido]:
    return Pedido.query.get(pedido_id)  # ← SQLAlchemy Model

# Model (app/models/pedido.py)
class Pedido(db.Model):
    def to_dict(self) -> dict:
        # Lógica de serialização
        return {...}
```

## Padrões de Código

### Clean Code

- **Nomes descritivos**: Variáveis e funções com nomes que descrevem claramente sua função
- **Funções pequenas**: Cada função faz uma coisa bem feita
- **Fail Fast**: Validações no início, retornos antecipados
- **Sem magic numbers**: Constantes nomeadas

### SOLID

- **Single Responsibility**: Cada classe tem uma única responsabilidade
- **Open/Closed**: Aberto para extensão, fechado para modificação
- **Liskov Substitution**: Interfaces bem definidas (Repository Pattern)
- **Interface Segregation**: Interfaces específicas (não genéricas demais)
- **Dependency Inversion**: Dependências apontam para abstrações (Repositories, Services)

### Princípios Específicos

- **Repository Pattern**: Toda interação com banco passa por Repository
- **Command Pattern**: Ações complexas encapsuladas em Commands
- **Service Layer**: Lógica de negócio isolada em Services
- **DTOs (Schemas)**: Dados transferidos via schemas validados

## Diferenciação: Novo vs. Legado

### ✅ O Que é Novo / Refatorado

- **Frontend V2**: Consome exclusivamente rotas JSON refatoradas
- **Repositories**: Toda leitura/escrita de `Pedido` e `Cliente` passa por `app/repositories`
- **Commands**: Lógica de impressão isolada em `app/commands`
- **Models**: Classes SQLAlchemy ricas (`Pedido.is_overdue()`, `to_dict()`)
- **Blueprints**: Rotas organizadas por domínio (pedidos, clientes, auth, rotas)

### ⚠️ O Que é Legado (Manter com Cuidado)

- **Scripts de Exportação**: `backend/scripts/export/exportar_vendas_sheets.py` - Script complexo que integra com Google API, envelopado na rota `/api/pedidos/exportar-planilha`
- **Frontend V1**: Diretório `frontend/` (HTML/JS puro) - Ainda existe para fallback, mas não deve receber novas features
- **Backups**: Sistema funcional e crítico, misturando lógica de OS (bat/shell) com Python
- **api.py**: Blueprint `api_bp` com rotas mistas antigas - Mantido para compatibilidade durante transição

## Autenticação e Segurança

- **Middleware**: `@requires_auth` e `@requires_edit_auth` decorators
- **Mecanismo**: Basic Auth (user/pass via variáveis de ambiente)
- **CORS**: Configurado globalmente para permitir acesso do `frontend_v2`
- **Rate Limiting**: 60 requisições/minuto, 1000/hora (configurável)
- **Fail-Closed**: Operações destrutivas (DELETE) bloqueadas se backup falhar (P0.2)

## Como Adicionar Nova Funcionalidade

1. **Definir Model** (se nova entidade): `app/models/nova_entidade.py`
2. **Criar Repository**: `app/repositories/nova_entidade_repository.py`
3. **Criar Schema**: `app/schemas/nova_entidade_schema.py` (validação)
4. **Criar Service** (se necessário): `app/services/nova_funcionalidade.py`
5. **Criar Route/Blueprint**: `app/routes/nova_entidade.py`
6. **Registrar Blueprint**: Adicionar em `app/factory.py`

---

**Última atualização**: 2026-01-04
