# 📋 Memória: Sistema de Backup e Integração

> Documento de referência rápida sobre o sistema de backup e sua integração com o sistema Gestor de Pedidos Plante uma Flor

---

## 🎯 Visão Geral

O sistema de backup é **multi-camadas** e **integrado profundamente** ao sistema, garantindo proteção automática contra perda de dados através de 4 camadas (Sistema P0).

---

## ⚙️ Integração com o Sistema

### 1. Inicialização do Servidor (`main.py`)
- **Gatilho**: Startup do servidor Flask
- **Quando**: Apenas no processo pai (evita duplicação no reloader)
- **Motivo**: `'startup'`
- **Comportamento**: Não bloqueia inicialização se falhar

```python
# backend/main.py (linhas 151-164)
if not is_reloader:
    with app.app_context():
        backup_path = create_backup(reason='startup', silent=False)
```

### 2. Operações Destrutivas (Fail-Closed - P0.2)
- **Rotas protegidas**: Todas as rotas `DELETE` críticas
  - `DELETE /api/pedidos/<id>` → Soft delete (P0.3)
  - `DELETE /api/clientes/<id>` → Hard delete
  - `DELETE /api/clientes/enderecos/<id>` → Hard delete
  - `DELETE /api/fontes-pedido/<id>` → Hard delete

- **Comportamento**: **BLOQUEIA operação** se backup falhar (HTTP 503)
- **Implementação**: `backend/app/utils/destructive_action_guard.py`

```python
# Exemplo: backend/app/routes/pedidos.py (linhas 110-121)
ensure_backup_before_destructive_action(reason='delete_pedido', context={'pedido_id': pedido_id})
# Se falhar → HTTP 503 com mensagem clara
```

### 3. Backup Agendado (P0.1)
- **Frequência**: A cada 1 hora
- **Janelas**: Seg-Sex 07:00-18:00, Sáb 07:00-14:00, Dom não executa
- **Script**: `backend/scripts/backup/run_scheduled_backup.py`
- **Idempotência**: Não cria backup se já existe um nos últimos 55 minutos
- **Logs**: `backend/instance/logs/scheduled_backup.log`

### 4. Teste de Restauração (P0.4)
- **Frequência**: Diária às 06:30
- **Script**: `backend/scripts/backup/restore_smoke_test.py`
- **Valida**: Integridade e restaurabilidade dos backups

---

## 🛡️ Sistema P0 - 4 Camadas de Proteção

### P0.1 - Backups Automáticos Horários
- Backups frequentes durante horário de trabalho
- Instalação: `install_backup_task.ps1`

### P0.2 - Fail-Closed
- **Zero "delete sem backup"**
- Bloqueia operação se backup falhar
- Resposta: HTTP 503
- Override: Suportado com auditoria (P0.3)

### P0.3 - Soft Delete + Auditoria
- **Soft Delete**: Pedidos não são removidos fisicamente
  - Coluna `deleted_at` na tabela `pedidos`
  - Endpoint: `POST /api/pedidos/<id>/restore` para restaurar
  - Endpoint: `GET /api/pedidos/deleted` para listar deletados
  
- **Trilha de Auditoria**: Tabela `audit_log`
  - Registra: CREATE, UPDATE, DELETE, RESTORE, OVERRIDE_DELETE
  - Campos: `ts`, `actor`, `action`, `entity_type`, `entity_id`, `metadata_json`

### P0.4 - Teste Recorrente de Restauração
- Valida automaticamente que backups são restauravels
- Instalação: `install_restore_test_task.ps1`

---

## 🔌 Endpoints da API

### Status de Backup
- **GET** `/api/backup/status`
- **Resposta**: Estatísticas dos backups (total, tamanho, último backup, etc)
- **Uso**: Frontend pode consumir para exibir status

### Operações Destrutivas
Todas as rotas DELETE estão protegidas pelo fail-closed (P0.2):
- `DELETE /api/pedidos/<id>` → Soft delete (P0.3) + backup obrigatório
- `DELETE /api/clientes/<id>` → Hard delete + backup obrigatório
- `DELETE /api/clientes/enderecos/<id>` → Hard delete + backup obrigatório
- `DELETE /api/fontes-pedido/<id>` → Hard delete + backup obrigatório

**Resposta em caso de falha de backup**: HTTP 503
```json
{
  "error": "Backup necessário antes de operação destrutiva. Falha ao criar backup. Operação bloqueada por segurança.",
  "details": {
    "error": "...",
    "pedido_id": 123
  }
}
```

### Soft Delete (P0.3)
- **GET** `/api/pedidos/deleted` → Lista pedidos soft-deleted
- **POST** `/api/pedidos/<id>/restore` → Restaura pedido deletado

---

## 📁 Estrutura de Arquivos

### Código Principal
- `backend/app/utils/backup_helper.py` - Interface programática (`create_backup()`, `get_backup_stats()`, etc)
- `backend/app/utils/destructive_action_guard.py` - Fail-closed (P0.2)
- `backend/app/utils/audit_logger.py` - Logger de auditoria (P0.3)
- `backend/app/utils/encryption.py` - Encriptação AES-256-GCM
- `backend/app/models/audit_log.py` - Modelo de auditoria (P0.3)
- `backend/app/repositories/pedido_repository.py` - Métodos de soft delete e restore (P0.3)

### Scripts
- `backend/scripts/backup/backup.py` - Gerenciador de backups
- `backend/scripts/backup/restore.py` - Gerenciador de restauração
- `backend/scripts/backup/run_scheduled_backup.py` - Backup agendado (P0.1)
- `backend/scripts/backup/restore_smoke_test.py` - Teste de restauração (P0.4)
- `backend/scripts/backup/install_backup_task.ps1` - Instalar tarefa P0.1
- `backend/scripts/backup/install_restore_test_task.ps1` - Instalar tarefa P0.4
- `backend/scripts/migrations/add_soft_delete_and_audit.py` - Migração P0.3

### Rotas
- `backend/app/routes/pedidos.py` - Rotas de pedidos (DELETE protegido, soft delete)
- `backend/app/routes/clientes.py` - Rotas de clientes (DELETE protegido)
- `backend/app/routes/api.py` - Rotas gerais (inclui `/api/backup/status`)

### Diretórios
- `backend/instance/backups/` - Backups locais não encriptados
- `backend/instance/logs/` - Logs de backup (`backup_audit.log`, `scheduled_backup.log`, `restore_test.log`)
- `C:\Users\<USER>\Meu Drive\Plante Uma Flor Confidential\Database - Pedidos Gestor\` - Backups encriptados (Google Drive Desktop)
- `%USERPROFILE%\var\lib\database\database.db` - Banco de dados principal

---

## 🔐 Encriptação

- **Algoritmo**: AES-256-GCM
- **Chave**: Variável de ambiente `BACKUP_ENCRYPTION_KEY` em `backend/.env`
- **Formato**: Base64 URL-safe
- **Uso**: Apenas para backups remotos (Google Drive Desktop)
- **Backups locais**: Não encriptados (para facilitar restauração)

---

## 📊 Funções Principais (`backup_helper.py`)

### `create_backup(reason, compress=True, silent=False)`
Cria backup programaticamente. Retorna `Path` ou `None`.

**Motivos comuns**:
- `'startup'` - Backup no startup do servidor
- `'critical_operation_delete_pedido'` - Antes de deletar pedido (P0.2)
- `'critical_operation_delete_cliente'` - Antes de deletar cliente (P0.2)
- `'scheduled_hourly'` - Backup agendado (P0.1)
- `'manual'` - Backup manual

### `get_backup_stats()`
Retorna estatísticas: `{'count': int, 'total_size_mb': float, 'oldest': datetime, 'newest': datetime}`

### `has_recent_backup(hours=24)`
Verifica se há backup recente (últimas N horas)

### `get_last_backup_time()`
Retorna tupla `(path, datetime, size_mb)` do último backup

---

## 🚨 Comportamento Fail-Closed (P0.2)

### Fluxo Completo
```
Operação Destrutiva (DELETE)
    ↓
[P0.2] Tentar criar backup
    ↓
Backup criado com sucesso?
    ├─ SIM → Continuar operação
    └─ NÃO → BLOQUEAR (HTTP 503)
            ↓
        allow_override=True?
            ├─ SIM → Registrar OVERRIDE_DELETE em auditoria → Continuar
            └─ NÃO → Operação bloqueada
    ↓
[P0.3] Soft Delete (se pedido) ou Hard Delete
    ↓
[P0.3] Auditoria: Registrar DELETE em audit_log
    ↓
Operação concluída
```

### Resposta de Erro (HTTP 503)
```json
{
  "error": "Backup necessário antes de operação destrutiva. Falha ao criar backup. Operação bloqueada por segurança.",
  "details": {
    "error": "...",
    "pedido_id": 123
  }
}
```

---

## 📝 Logs e Auditoria

### Logs de Arquivo
- `backend/instance/logs/backup_audit.log` - Logs de backup/restore
- `backend/instance/logs/scheduled_backup.log` - Logs de backup agendado (P0.1)
- `backend/instance/logs/restore_test.log` - Logs de teste de restauração (P0.4)

### Trilha de Auditoria (Banco)
- **Tabela**: `audit_log`
- **Consulta**: `SELECT * FROM audit_log ORDER BY ts DESC LIMIT 10;`
- **Ações registradas**: CREATE, UPDATE, DELETE, RESTORE, OVERRIDE_DELETE

---

## 🔄 Soft Delete (P0.3)

### Características
- Pedidos **não são removidos fisicamente**
- Coluna `deleted_at` marca como deletado
- Filtragem automática: Todos os métodos `buscar_*` excluem deletados por padrão
- Métodos especiais:
  - `buscar_deletados()` - Lista apenas deletados
  - `soft_delete_pedido(id, actor)` - Soft delete com auditoria
  - `restore_pedido(id, actor)` - Restauração com auditoria

### Endpoints
- `GET /api/pedidos/deleted` - Lista pedidos soft-deleted
- `POST /api/pedidos/<id>/restore` - Restaura pedido deletado

---

## ⚙️ Configurações

### Variáveis de Ambiente (`backend/.env`)
```env
BACKUP_ENCRYPTION_KEY=<chave_base64>  # Gerada automaticamente se não existir
GDRIVE_BACKUP_DIR=C:\Users\<USER>\Meu Drive\...  # Opcional
```

### Configurações do Sistema
- **Banco principal**: `%USERPROFILE%\var\lib\database\database.db`
- **Backups locais**: `backend/instance/backups/` (retenção: 30 dias)
- **Backups remotos**: Google Drive Desktop (encriptados, retenção: ilimitada)

---

## 🧪 Migração P0.3

Para habilitar soft delete e auditoria:
```bash
cd backend
python scripts/migrations/add_soft_delete_and_audit.py
```

**Alterações**:
1. Adiciona coluna `deleted_at DATETIME NULL` na tabela `pedidos`
2. Cria tabela `audit_log` com índices

---

## 📚 Referências

- **Documentação completa**: `backend/docs/ESTUDO_BACKUP_COMPLETO.md`
- **Guia de backup encriptado**: `backend/docs/BACKUP_GDRIVE.md`

---

**Última atualização**: 2026-01-02  
**Versão**: 2.0 (Sistema P0 completo)

