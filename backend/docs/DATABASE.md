# Integração com Database

Este documento descreve a integração com SQLite, models, Repository Pattern, migrations e configurações do banco de dados.

## Visão Geral

O sistema utiliza **SQLite** como banco de dados, gerenciado via **SQLAlchemy 2.0**. O banco de dados é armazenado em `instance/database.db` (desenvolvimento) ou `%USERPROFILE%/var/lib/database/database.db` (produção).

## Localização do Banco

- **Desenvolvimento**: `backend/instance/database.db`
- **Produção**: `%USERPROFILE%/var/lib/database/database.db`

A localização é configurada via variável de ambiente `DATABASE_PATH` no arquivo `.env`.

## Models

Os models são definidos em `backend/app/models/` usando SQLAlchemy. Cada model representa uma tabela do banco de dados.

### Models Disponíveis

- **Pedido** (`app/models/pedido.py`): Entidade principal do sistema
- **Cliente** (`app/models/cliente.py`): Clientes do sistema
- **EnderecoCliente** (`app/models/endereco_cliente.py`): Endereços de clientes
- **RotaOtimizada** (`app/models/rota_otimizada.py`): Rotas otimizadas calculadas
- **FontePedido** (`app/models/fonte_pedido.py`): Fontes de pedidos (WhatsApp, Site, etc.)
- **AuditLog** (`app/models/audit_log.py`): Log de auditoria (P0.3)

### Exemplo de Model

```python
from app import db
from datetime import datetime

class Pedido(db.Model):
    __tablename__ = 'pedidos'
    
    id = db.Column(db.Integer, primary_key=True)
    cliente = db.Column(db.String(200), nullable=False)
    destinatario = db.Column(db.String(200), nullable=False)
    # ... outros campos
    
    def to_dict(self) -> dict:
        """Serializa model para dicionário"""
        return {
            'id': self.id,
            'cliente': self.cliente,
            # ...
        }
    
    def is_overdue(self) -> bool:
        """Verifica se pedido está atrasado"""
        # Lógica de negócio
        pass
```

## Repository Pattern

Toda interação com o banco de dados passa pelo **Repository Pattern**, evitando acesso direto ao `db.session` no código de negócio.

### Estrutura

- **Base Repository**: `app/repositories/base_repository.py` - Classe base com métodos comuns
- **Pedido Repository**: `app/repositories/pedido_repository.py` - Métodos específicos de pedidos
- **Cliente Repository**: `app/repositories/cliente_repository.py` - Métodos específicos de clientes

### Uso do Repository

```python
from app.repositories.pedido_repository import PedidoRepository

pedido_repo = PedidoRepository()

# Buscar pedido
pedido = pedido_repo.get_by_id(pedido_id)

# Buscar com filtros
pedidos = pedido_repo.buscar_com_filtros(
    status='agendado',
    data_inicio=datetime.now().date()
)

# Criar pedido
novo_pedido = pedido_repo.create(dados_pedido)

# Atualizar
pedido_repo.update(pedido_id, dados_atualizados)

# Soft delete (se suportado)
pedido_repo.soft_delete_pedido(pedido_id, actor='admin')
```

### Vantagens

- **Abstração**: Código de negócio não conhece detalhes de SQL
- **Testabilidade**: Fácil mockar repositories em testes
- **Manutenibilidade**: Queries centralizadas
- **Reutilização**: Lógica de acesso a dados reutilizável

## Migrations

O sistema utiliza **Flask-Migrate** para gerenciar migrations do banco de dados.

### Comandos Principais

```bash
# Inicializar migrations (apenas primeira vez)
flask db init

# Criar nova migration
flask db migrate -m "Descrição da migration"

# Aplicar migrations
flask db upgrade

# Reverter última migration
flask db downgrade
```

### Scripts de Migration Manuais

Algumas migrations complexas estão em `backend/scripts/migrations/`:

- `add_soft_delete_and_audit.py` - Adiciona soft delete e auditoria (P0.3)
- `add_distancia_column.py` - Adiciona coluna de distância
- `add_endereco_columns.py` - Adiciona colunas de endereço
- `criar_tabelas_clientes.py` - Cria tabelas de clientes

**Como executar**:
```bash
cd backend/scripts/migrations
python nome_do_script.py
```

## PRAGMAs SQLite

O sistema configura automaticamente PRAGMAs SQLite via event hooks em `app/extensions.py`:

### PRAGMAs Configurados

- **journal_mode = WAL**: Write-Ahead Logging para melhor performance
- **synchronous = FULL/NORMAL/OFF**: Sincronização (configurável via `SQLITE_SYNCHRONOUS`)
- **foreign_keys = ON/OFF**: Foreign keys (configurável via `SQLITE_FOREIGN_KEYS`)
- **busy_timeout = 5000**: Timeout de 5 segundos para operações bloqueadas

### Configuração via Variáveis de Ambiente

No arquivo `.env`:

```env
# Sincronização (FULL, NORMAL, OFF)
SQLITE_SYNCHRONOUS=FULL

# Foreign keys (ON, OFF, 1, 0, TRUE, FALSE, YES, NO)
SQLITE_FOREIGN_KEYS=ON
```

### Foreign Keys

Por padrão, foreign keys estão **habilitadas**. Para desabilitar temporariamente (debug):

```env
SQLITE_FOREIGN_KEYS=OFF
```

⚠️ **Aviso**: Desabilitar foreign keys pode causar problemas de integridade. Use apenas para debug ou migração de dados.

**Quando usar OFF**:
- Debug de problemas de inicialização
- Migração de dados
- Testes temporários

**Sempre reabilite depois**:
```env
SQLITE_FOREIGN_KEYS=ON
```

## Inicialização do Banco

O banco de dados é inicializado automaticamente na inicialização da aplicação (`app/extensions.py`):

1. Verifica se banco existe
2. Cria banco se não existir (desenvolvimento)
3. Importa todos os models
4. Cria tabelas via `db.create_all()` (se banco novo ou `ALLOW_DB_BOOTSTRAP=true`)
4. Configura PRAGMAs via event hooks

**Em produção**: O banco deve existir antes de iniciar o servidor (migrations devem ser aplicadas manualmente).

## Soft Delete

O sistema implementa **soft delete** para pedidos (P0.3):

- Pedidos não são removidos fisicamente
- Coluna `deleted_at` marca como deletado
- Filtragem automática: Métodos `buscar_*` excluem deletados por padrão
- Métodos especiais: `buscar_deletados()`, `restore_pedido()`

**Tabela**: `pedidos`  
**Coluna**: `deleted_at DATETIME NULL`

## Auditoria

O sistema registra ações em `audit_log` (P0.3):

**Tabela**: `audit_log`

**Campos**:
- `id`: Primary key
- `ts`: Timestamp
- `actor`: Usuário que executou a ação
- `action`: Tipo de ação (CREATE, UPDATE, DELETE, RESTORE, OVERRIDE_DELETE)
- `entity_type`: Tipo de entidade (pedido, cliente)
- `entity_id`: ID da entidade
- `metadata_json`: Metadados adicionais (JSON)

**Consulta**:
```sql
SELECT * FROM audit_log ORDER BY ts DESC LIMIT 10;
```

## Backup e Integridade

O sistema possui sistema robusto de backup (ver [BACKUP.md](BACKUP.md)):

- Backup automático no startup
- Backup antes de operações destrutivas (fail-closed P0.2)
- Backup agendado (horário)
- Validação de integridade (`PRAGMA integrity_check`)

---

**Última atualização**: 2026-01-04  
**Ver também**: [BACKUP.md](BACKUP.md), [ARCHITECTURE.md](ARCHITECTURE.md)
