# 📋 Estudo Completo: Sistema de Backup do Banco de Dados

## 📌 Visão Geral

O sistema de backup do **Gestor de Pedidos Plante uma Flor** é um sistema robusto e multi-camadas que garante a segurança e recuperação dos dados do banco SQLite.

---

## 🎯 1. O QUE É FEITO

### 1.1. Objeto do Backup
- **Arquivo de origem**: `database.db` (banco SQLite)
- **Localização padrão**: `C:\Users\<USER>\var\lib\database\database.db`
- **Conteúdo**: Todos os pedidos, clientes, fontes de pedidos e dados relacionados

### 1.2. Processo de Backup
O backup utiliza o método nativo do SQLite `sqlite3.Connection.backup()` que:
- Cria uma cópia completa e consistente do banco
- Garante integridade transacional
- Valida o backup com `PRAGMA integrity_check`

### 1.3. Formato dos Arquivos
- **Nome padrão**: `database_YYYYMMDD_HHMMSS.db` ou `.zip`
- **Exemplo**: `database_20251220_143022.db`
- **Compressão**: Opcional (ZIP com DEFLATE)

---

## 📍 2. ONDE É ARMAZENADO

### 2.1. Backups Locais (Não Encriptados)
- **Diretório**: `backend/instance/backups/`
- **Formato**: `.db` ou `.zip`
- **Propósito**: Acesso rápido para restauração local
- **Retenção**: 30 dias (configurável)

### 2.2. Backups Encriptados (Google Drive Desktop)
- **Diretório**: `C:\Users\<USER>\Meu Drive\Plante Uma Flor Confidential\Database - Pedidos Gestor`
- **Formato**: `.enc` (arquivo encriptado)
- **Propósito**: Backup remoto seguro na nuvem
- **Sincronização**: Automática via Google Drive Desktop
- **Retenção**: Ilimitada (gerenciada manualmente ou via API)

### 2.3. Estrutura de Diretórios
```
backend/
├── instance/
│   ├── backups/              # Backups locais não encriptados
│   │   ├── database_20251220_143022.zip
│   │   └── database_20251221_080000.zip
│   ├── logs/
│   │   ├── backup_audit.log  # Log de auditoria
│   │   └── backup_gdrive.log # Log de uploads
│   └── database.db           # Banco atual (NÃO é backup)
│
C:\Users\<USER>\
├── var\lib\database\
│   └── database.db           # Banco principal (fora do repositório)
└── Meu Drive\
    └── Plante Uma Flor Confidential\
        └── Database - Pedidos Gestor\  # Backups encriptados
            ├── database_20251220_143022.zip.enc
            └── database_20251221_080000.zip.enc
```

---

## 🔐 3. ENCRIPTAÇÃO

### 3.1. Algoritmo
- **Algoritmo**: AES-256-GCM (Advanced Encryption Standard)
- **Tamanho da chave**: 256 bits (32 bytes)
- **Modo**: GCM (Galois/Counter Mode) - autenticado e seguro
- **Biblioteca**: `cryptography.hazmat.primitives.ciphers.aead.AESGCM`

### 3.2. Chave de Encriptação
- **Armazenamento**: Variável de ambiente `BACKUP_ENCRYPTION_KEY` no arquivo `.env`
- **Formato**: Base64 URL-safe
- **Geração**: Automática no primeiro uso se não existir
- **Localização**: `backend/.env`

### 3.3. Formato do Arquivo Encriptado
```
[Header: 2 bytes] + [Nonce: 12 bytes] + [Ciphertext + Tag]
     'v1'              Random          Encrypted data
```

### 3.4. Segurança
- ✅ **Chave única**: Cada instalação gera sua própria chave
- ✅ **Nonce aleatório**: Cada arquivo tem nonce único (evita ataques de repetição)
- ✅ **Autenticação**: GCM garante integridade (detecta modificações)
- ✅ **Chave não versionada**: Nunca commitada no Git

---

## ⏰ 4. QUANDO É EXECUTADO

### 4.1. Backup Automático no Startup
- **Gatilho**: Inicialização do servidor Flask (`main.py`)
- **Condição**: Apenas no processo pai (evita duplicação no reloader)
- **Motivo**: `'startup'`
- **Comportamento**: Não bloqueia inicialização se falhar

### 4.2. Backup em Operações Críticas
- **Gatilho**: Antes de deletar pedido
- **Local**: `backend/app/routes/pedidos.py` (linha 111)
- **Motivo**: `'critical_operation'`
- **Comportamento**: Silencioso (não exibe mensagens)

### 4.3. Backup Agendado (Opcional - Legado)
- **Frequência**: Diária (configurável)
- **Horário padrão**: 02:00 ou 03:00 (madrugada)
- **Método**: Windows Task Scheduler
- **Script**: `agendar_backup_gdrive.bat` ou `agendar_backup_windows.bat`
- **Tipo**: Backup encriptado com upload para Google Drive
- **Status**: Mantido para compatibilidade, mas substituído por P0.1

### 4.4. Backup Automático Horário (P0.1) ⭐ NOVO
- **Frequência**: A cada 1 hora dentro das janelas de execução
- **Janelas de execução**:
  - **Segunda a Sexta**: 07:00 até 18:00 (inclusive)
  - **Sábado**: 07:00 até 14:00 (inclusive)
  - **Domingo**: Não executa
- **Método**: Windows Task Scheduler com múltiplos triggers
- **Script**: `backend/scripts/backup/run_scheduled_backup.py`
- **Instalação**: `install_backup_task.ps1` (executar como Administrador)
- **Idempotência**: Não cria backup se já existe um nos últimos 55 minutos
- **Logs**: `backend/instance/logs/scheduled_backup.log`
- **Motivo**: `'scheduled_hourly'`

### 4.5. Backup Manual
- **Via CLI**: `python backend/scripts/backup/backup.py`
- **Via código**: `create_backup(reason='manual')`
- **Motivo**: `'manual'`

### 4.6. Fail-Closed: Backup Obrigatório (P0.2) ⭐ NOVO
- **Gatilho**: Antes de qualquer operação destrutiva (delete)
- **Comportamento**: **Bloqueia a operação** se backup falhar
- **Rotas protegidas**:
  - `DELETE /api/pedidos/<id>` - Deletar pedido
  - `DELETE /api/clientes/<id>` - Deletar cliente
  - `DELETE /api/clientes/enderecos/<id>` - Deletar endereço
  - `DELETE /api/fontes-pedido/<id>` - Deletar fonte de pedido
- **Resposta em caso de falha**: HTTP 503 com mensagem clara
- **Implementação**: `backend/app/utils/destructive_action_guard.py`
- **Função**: `ensure_backup_before_destructive_action()`
- **Motivo**: `'critical_operation_<tipo>'` (ex: `'critical_operation_delete_pedido'`)
- **Override**: Suporta `allow_override=True` com auditoria (P0.3)

---

## 🛡️ 5. SOFT DELETE E AUDITORIA (P0.3) ⭐ NOVO

### 5.1. Soft Delete
- **Objetivo**: Reduzir perda de dados por erro humano
- **Implementação**: Coluna `deleted_at` na tabela `pedidos`
- **Comportamento**: Pedidos não são removidos fisicamente, apenas marcados como deletados
- **Métodos do Modelo**:
  - `pedido.soft_delete()` - Marca como deletado
  - `pedido.restore()` - Restaura pedido deletado
  - `pedido.is_deleted` - Propriedade que verifica se está deletado
- **Filtragem automática**: Todos os métodos `buscar_*` do `PedidoRepository` excluem deletados por padrão
- **Métodos especiais**:
  - `buscar_deletados()` - Lista apenas pedidos soft-deleted
  - `soft_delete_pedido(id, actor)` - Soft delete com auditoria
  - `restore_pedido(id, actor)` - Restauração com auditoria

### 5.2. Trilha de Auditoria
- **Tabela**: `audit_log`
- **Colunas**:
  - `id` - Chave primária
  - `ts` - Timestamp do evento
  - `actor` - Quem executou a ação (usuário/cliente/terminal)
  - `action` - Tipo de ação (CREATE/UPDATE/DELETE/RESTORE/OVERRIDE_DELETE)
  - `entity_type` - Tipo de entidade ('pedido', 'cliente', etc)
  - `entity_id` - ID da entidade afetada
  - `metadata_json` - JSON com informações adicionais (diffs, resumo)
- **Índices**: `ts`, `(entity_type, entity_id)`, `action`
- **Registro automático**: Todas as operações críticas são registradas
- **Função**: `log_action()` em `backend/app/utils/audit_logger.py`

### 5.3. Endpoints de Soft Delete
- **Deletar pedido**: `DELETE /api/pedidos/<id>` - Agora faz soft delete
- **Restaurar pedido**: `POST /api/pedidos/<id>/restore` - Restaura pedido deletado
- **Listar deletados**: `GET /api/pedidos/deleted` - Lista todos os pedidos soft-deleted

### 5.4. Migração de Banco de Dados
- **Script**: `backend/scripts/migrations/add_soft_delete_and_audit.py`
- **Alterações**:
  1. Adiciona coluna `deleted_at DATETIME NULL` na tabela `pedidos`
  2. Cria tabela `audit_log` com todas as colunas e índices
- **Execução**: `python backend/scripts/migrations/add_soft_delete_and_audit.py`
- **Idempotente**: Pode ser executado múltiplas vezes sem problemas

---

## 🗑️ 6. RETENÇÃO E LIMPEZA

### 5.1. Backups Locais
- **Retenção padrão**: 30 dias
- **Configurável**: Via parâmetro `retention_days` no `BackupManager`
- **Limpeza automática**: Executada após cada backup (se não usar `--no-cleanup`)
- **Critério**: Data de modificação do arquivo (`st_mtime`)
- **Padrões removidos**: `database_*.db`, `database_*.zip`, `database_*.enc`, `database_*.zip.enc`

### 5.2. Backups Remotos (Google Drive)
- **Retenção padrão**: 90 backups (configurável)
- **Limpeza**: Via API do Google Drive (se usar `--upload-drive`)
- **Método**: Remove os backups mais antigos, mantendo os N mais recentes
- **Nota**: Backups no Google Drive Desktop não são limpos automaticamente

### 5.3. Exemplo de Limpeza
```python
# Backups locais com mais de 30 dias são removidos
cutoff_date = datetime.now() - timedelta(days=30)
# Remove arquivos com data de modificação anterior a cutoff_date
```

---

## 🔄 7. FLUXO COMPLETO DE BACKUP

### 6.1. Backup Simples (Local)
```
1. Verificar se database.db existe
2. Criar backup usando sqlite3.Connection.backup()
3. Validar integridade com PRAGMA integrity_check
4. Comprimir (opcional) → database_YYYYMMDD_HHMMSS.zip
5. Salvar em backend/instance/backups/
6. Registrar no log de auditoria
7. Limpar backups antigos (se não usar --no-cleanup)
```

### 6.2. Backup Encriptado (Google Drive Desktop)
```
1. Criar backup local não encriptado (mantém este)
   └─> backend/instance/backups/database_YYYYMMDD_HHMMSS.zip

2. Encriptar cópia do backup
   └─> Usa AES-256-GCM com chave do .env
   └─> Salva diretamente no Google Drive Desktop
   └─> C:\Users\<USER>\Meu Drive\...\database_YYYYMMDD_HHMMSS.zip.enc

3. Google Drive Desktop sincroniza automaticamente para nuvem

4. (Opcional) Upload via API do Google Drive
   └─> Se usar --upload-drive
   └─> Remove backups antigos no Drive (mantém 90 mais recentes)
```

---

## 🧪 8. TESTE RECORRENTE DE RESTAURAÇÃO (P0.4) ⭐ NOVO

### 8.1. Objetivo
Validar automaticamente que os backups podem ser restaurados corretamente, detectando problemas antes que sejam necessários em produção.

### 8.2. Execução
- **Frequência**: Diária
- **Horário**: 06:30 (antes da janela de backup)
- **Método**: Windows Task Scheduler
- **Script**: `backend/scripts/backup/restore_smoke_test.py`
- **Instalação**: `install_restore_test_task.ps1` (executar como Administrador)
- **Logs**: `backend/instance/logs/restore_test.log`

### 8.3. Processo
1. **Encontrar backup mais recente** em `backend/instance/backups/`
2. **Extrair backup** em diretório temporário (sandbox)
3. **Executar `PRAGMA integrity_check`** no banco restaurado
4. **Sanity checks**:
   - Verificar existência de tabelas essenciais (`pedidos`, `clientes`, `fonte_pedido`)
   - Verificar contagens básicas (devem ser >= 0)
   - Verificar schema_version (se existir)
5. **Limpar arquivos temporários** após teste
6. **Registrar resultado** no log

### 8.4. Resultados
- **Exit code 0**: Teste passou (backup é restauravel)
- **Exit code 1**: Teste falhou (backup pode estar corrompido)
- **Logs detalhados**: Cada etapa é registrada com timestamp

### 8.5. Benefícios
- ✅ Detecta corrupção de backups antes que sejam necessários
- ✅ Valida que o processo de backup está funcionando corretamente
- ✅ Garante que backups podem ser restaurados quando necessário
- ✅ Execução automática sem intervenção manual

---

## 📊 9. LOGS E AUDITORIA

### 9.1. Log de Auditoria de Backup
- **Arquivo**: `backend/instance/logs/backup_audit.log`
- **Formato**: `YYYY-MM-DD HH:MM:SS | LEVEL | MESSAGE`
- **Eventos registrados**:
  - ✅ `BACKUP CRIADO | Arquivo: ... | Motivo: ... | Tamanho: ... MB`
  - ❌ `BACKUP FALHOU | Motivo: ... | Erro: ...`
  - ⚠️ `RESTORE TENTATIVA | Arquivo: ... | Status: CONFIRMADO/CANCELADO`
  - ⚠️ `RESTORE SUCESSO/FALHA | Arquivo: ...`

### 9.2. Log de Backup Agendado (P0.1)
- **Arquivo**: `backend/instance/logs/scheduled_backup.log`
- **Formato**: `YYYY-MM-DD HH:MM:SS | LEVEL | MESSAGE`
- **Eventos registrados**:
  - `INFO | Iniciando backup agendado (motivo: scheduled_hourly)`
  - `INFO | Fora da janela de execução (...) - ignorado`
  - `INFO | Backup recente encontrado (...) - idempotência ativa, ignorado`
  - `SUCCESS | Backup criado com sucesso: ... (X.XX MB)`
  - `ERROR | Falha ao criar backup (...)`

### 9.3. Log de Teste de Restauração (P0.4)
- **Arquivo**: `backend/instance/logs/restore_test.log`
- **Formato**: `YYYY-MM-DD HH:MM:SS | LEVEL | MESSAGE`
- **Eventos registrados**:
  - `INFO | TESTE DE RESTAURAÇÃO (P0.4)`
  - `INFO | Backup selecionado: ...`
  - `INFO | Executando PRAGMA integrity_check...`
  - `SUCCESS | Integrity check: OK`
  - `INFO | Executando sanity checks...`
  - `SUCCESS | Sanity checks: OK`
  - `SUCCESS | TESTE DE RESTAURAÇÃO CONCLUÍDO COM SUCESSO`
  - `ERROR | Integrity check falhou: ...`
  - `ERROR | Sanity checks falharam: ...`

### 9.4. Log de Google Drive
- **Arquivo**: `backend/instance/logs/backup_gdrive.log`
- **Conteúdo**: Execuções do script `agendar_backup_gdrive.py`

### 9.5. Trilha de Auditoria no Banco (P0.3)
- **Tabela**: `audit_log`
- **Consulta**: `SELECT * FROM audit_log ORDER BY ts DESC LIMIT 10;`
- **Eventos registrados**:
  - `CREATE` - Criação de entidades
  - `UPDATE` - Atualização de entidades
  - `DELETE` - Soft delete de entidades
  - `RESTORE` - Restauração de entidades deletadas
  - `OVERRIDE_DELETE` - Override de fail-closed (com auditoria)

---

## 🛠️ 10. FERRAMENTAS E COMANDOS

### 8.1. Criar Backup Manual
```bash
# Backup simples (local, não encriptado)
python backend/scripts/backup/backup.py

# Backup encriptado (Google Drive Desktop)
python backend/scripts/backup/backup.py --no-compress

# Backup com upload via API
python backend/scripts/backup/backup.py --upload-drive --keep-remote 90
```

### 8.2. Listar Backups
```bash
python backend/scripts/backup/backup.py --list
```

### 8.3. Estatísticas
```bash
python backend/scripts/backup/backup.py --stats
```

### 8.4. Restaurar Backup
```bash
# Modo interativo (lista backups e escolhe)
python backend/scripts/backup/restore.py

# Restaurar backup específico
python backend/scripts/backup/restore.py --backup "database_20251220_143022.zip"
```

### 10.5. Agendar Backup (Legado)
```bash
# Windows Task Scheduler (backup simples)
backend\scripts\backup\agendar_backup_windows.bat

# Windows Task Scheduler (backup encriptado)
backend\scripts\backup\agendar_backup_gdrive.bat
```

### 10.6. Instalar Backup Automático Horário (P0.1) ⭐ NOVO
```powershell
# Abrir PowerShell como Administrador
cd "C:\Gestor de Pedidos Plante uma flor\backend\scripts\backup"
.\install_backup_task.ps1
```

**Desinstalar**:
```powershell
.\uninstall_backup_task.ps1
```

### 10.7. Instalar Teste de Restauração (P0.4) ⭐ NOVO
```powershell
# Abrir PowerShell como Administrador
cd "C:\Gestor de Pedidos Plante uma flor\backend\scripts\backup"
.\install_restore_test_task.ps1
```

**Desinstalar**:
```powershell
.\uninstall_restore_test_task.ps1
```

### 10.8. Executar Migração de Soft Delete e Auditoria (P0.3) ⭐ NOVO
```bash
cd backend
python scripts/migrations/add_soft_delete_and_audit.py
```

### 10.9. Consultar Trilha de Auditoria
```python
from app import create_app, db
from app.models import AuditLog

app = create_app()
with app.app_context():
    logs = AuditLog.query.order_by(AuditLog.ts.desc()).limit(10).all()
    for log in logs:
        print(f"{log.ts} | {log.action} | {log.entity_type} #{log.entity_id} | {log.actor}")
```

### 10.10. Listar Pedidos Deletados
```bash
# Via API
GET /api/pedidos/deleted

# Via código
from app.repositories.pedido_repository import PedidoRepository
repo = PedidoRepository()
deletados = repo.buscar_deletados()
```

### 10.11. Restaurar Pedido Deletado
```bash
# Via API
POST /api/pedidos/<id>/restore

# Via código
from app.repositories.pedido_repository import PedidoRepository
repo = PedidoRepository()
pedido = repo.restore_pedido(pedido_id, actor='usuario')
```

### 10.12. Comandos P1 - Robustez Operacional ⭐ NOVO

#### P1.1 - Validar Banco de Dados
```bash
# Validar backup restaurado
python -c "from scripts.backup.validate_db import validate_restored_db; from pathlib import Path; r = validate_restored_db(Path('instance/backups/database_20250102_120000.db')); print('OK' if r.success else f'ERRO: {r.errors}')"
```

#### P1.2 - Limpeza GFS de Backups
```bash
# Simular limpeza (não deleta nada)
python scripts/backup/cleanup_backups.py --local --dry-run

# Executar limpeza local
python scripts/backup/cleanup_backups.py --local

# Executar limpeza remota (Google Drive Desktop)
python scripts/backup/cleanup_backups.py --remote

# Executar ambos
python scripts/backup/cleanup_backups.py --local --remote

# Sobrescrever política de retenção
python scripts/backup/cleanup_backups.py --local --policy-hourly 24 --policy-daily 15
```

#### P1.3 - Verificar Backup Remoto
```bash
# A verificação remota é automática durante backup encriptado
# Para testar manualmente (via código Python):
python -c "
from scripts.backup.remote_verify import copy_and_verify_remote
from pathlib import Path
success, error = copy_and_verify_remote(
    Path('instance/backups/database_20250102_120000.zip'),
    Path('C:/Users/<USER>/Meu Drive/...'),
    check_hash=False
)
print('OK' if success else f'ERRO: {error}')
"
```

#### P1.5 - Consultar Health do Backup
```bash
# Via API (com autenticação)
curl -u admin:<senha> http://localhost:5000/api/admin/backup/health

# Via arquivo JSON
cat backend/instance/backup_status.json | python -m json.tool

# Via Python
python -c "
from scripts.backup.status import get_backup_health
health = get_backup_health(max_age_hours=24)
print(f\"Health: {health['health']}\")
print(f\"Issues: {health['issues']}\")
"
```

#### P1.1 - Executar Migração de Schema Version
```bash
# Adicionar tabela app_meta e schema_version
python scripts/migrations/add_app_meta_schema_version.py
```

---

## 🔍 11. VALIDAÇÃO E INTEGRIDADE

### 11.1. Validação do Backup (Legado)
- **Método**: `PRAGMA integrity_check`
- **Quando**: Após criar o backup
- **Resultado esperado**: `'ok'`
- **Ação se falhar**: Backup é deletado e retorna `None`

### 11.2. Verificação de Tamanho
- **Validação**: Tamanho do arquivo restaurado não pode ser 0
- **Local**: Durante restauração (`restore.py`)

### 11.3. Validação Padronizada (P1.1) ⭐ NOVO
- **Módulo**: `scripts/backup/validate_db.py`
- **Função**: `validate_restored_db()`
- **Validações executadas**:
  1. **PRAGMA integrity_check** (obrigatório) - Verifica integridade estrutural do banco
  2. **Schema Version** - Verifica compatibilidade via tabela `app_meta`
  3. **Sanity Checks** - Verifica existência de tabelas essenciais (`pedidos`, `clientes`, `fonte_pedido`)
  4. **Invariantes opcionais** - Verificação de foreign keys (se habilitado)
- **Usado por**:
  - `restore.py` - Após restaurar backup
  - `restore_smoke_test.py` - Teste diário de restauração
- **Retorno**: `ValidationResult` com `success`, `errors`, `warnings`, `details`
- **Exit code**: 0 se sucesso, 1 se falha (para uso em scripts)

---

## ⚙️ 12. CONFIGURAÇÕES

### 12.1. Variáveis de Ambiente

#### Variáveis Base
```env
# Chave de encriptação (gerada automaticamente se não existir)
BACKUP_ENCRYPTION_KEY=<chave_base64>

# Diretório do Google Drive Desktop (opcional)
GDRIVE_BACKUP_DIR=C:\Users\<USER>\Meu Drive\Plante Uma Flor Confidential\Database - Pedidos Gestor

# ID da pasta no Google Drive (para upload via API)
GDRIVE_BACKUP_FOLDER_ID=<folder_id>
```

#### Variáveis P1 - Robustez Operacional ⭐ NOVO
```env
# P1.1 - Schema Version (já configurado em config.py como '1.0', pode sobrescrever)
APP_SCHEMA_VERSION=1.0

# P1.2 - Retenção GFS (política Grandfather-Father-Son)
BACKUP_RETENTION_HOURLY=48      # Quantidade de backups por hora
BACKUP_RETENTION_DAILY=30       # Quantidade de backups por dia
BACKUP_RETENTION_WEEKLY=12      # Quantidade de backups por semana
BACKUP_RETENTION_MONTHLY=12     # Quantidade de backups por mês

# P1.3 - Verificação Remota (opcional)
BACKUP_REMOTE_VERIFY_HASH=false  # Se true, verifica hash SHA-256 (mais lento)

# P1.4 - Diretório Secundário (opcional, preferencialmente outro drive)
BACKUP_SECONDARY_DIR=D:\Backups\Secundario

# P1.5 - Health/Status (opcional)
BACKUP_HEALTH_MAX_AGE_HOURS=24   # Idade máxima em horas para considerar backup válido
```

### 12.2. Configurações do BackupManager
```python
BackupManager(
    db_path=None,              # Padrão: Config.DATABASE_PATH
    backup_dir=None,           # Padrão: backend/instance/backups
    retention_days=30          # Dias para manter backups locais (legado, substituído por P1.2 GFS)
)
```

### 12.3. Valores Padrão P1
Se as variáveis de ambiente P1 não forem configuradas, os seguintes valores padrão são usados:
- `BACKUP_RETENTION_HOURLY=48` (2 dias de backups horários)
- `BACKUP_RETENTION_DAILY=30` (30 dias de backups diários)
- `BACKUP_RETENTION_WEEKLY=12` (12 semanas de backups semanais)
- `BACKUP_RETENTION_MONTHLY=12` (12 meses de backups mensais)
- `BACKUP_HEALTH_MAX_AGE_HOURS=24` (24 horas para considerar backup válido)
- `APP_SCHEMA_VERSION='1.0'` (hardcoded em `config.py`, pode ser sobrescrito)

---

## 📈 13. ESTATÍSTICAS E MONITORAMENTO

### 13.1. Funções Disponíveis (Legado)
- `get_backup_stats()`: Retorna contagem, tamanho total, mais antigo/novo
- `get_last_backup_time()`: Informações do último backup
- `has_recent_backup(hours=24)`: Verifica se há backup recente

### 13.2. Exemplo de Uso (Legado)
```python
from app.utils.backup_helper import get_backup_stats, has_recent_backup

stats = get_backup_stats()
# {
#     'count': 15,
#     'total_size_mb': 245.67,
#     'oldest': datetime(2025, 11, 20, 14, 30, 22),
#     'newest': datetime(2025, 12, 20, 14, 30, 22)
# }

if has_recent_backup(hours=24):
    print("Há backup recente (últimas 24h)")
```

### 13.3. Health/Status (P1.5) ⭐ NOVO
- **Arquivo de status**: `backend/instance/backup_status.json`
- **Endpoint API**: `GET /api/admin/backup/health`
- **Função Python**: `get_backup_health(max_age_hours=24)`
- **Campos do status**:
  - `last_backup_ok_at`, `last_backup_error`
  - `last_remote_ok_at`, `last_remote_error`
  - `last_restore_test_ok_at`, `last_restore_test_error`
  - `last_cleanup_ok_at`, `last_cleanup_error`
  - `backups_local_count`, `backups_remote_count`
- **Health levels**:
  - `OK`: Tudo operacional
  - `WARN`: Problemas não críticos (remoto não OK, cleanup falhou)
  - `FAIL`: Problemas críticos (backup muito antigo, restore test falhou)

### 13.4. Exemplo de Uso do Health (P1.5)
```python
from scripts.backup.status import get_backup_health, read_backup_status

# Obter health completo
health = get_backup_health(max_age_hours=24)
print(f"Health: {health['health']}")  # OK, WARN ou FAIL
print(f"Issues: {health['issues']}")  # Lista de problemas

# Ler status bruto
status = read_backup_status()
print(f"Último backup OK: {status.last_backup_ok_at}")
print(f"Contagem local: {status.backups_local_count}")
```

---

## 🚨 14. SEGURANÇA E BOAS PRÁTICAS

### 14.1. Segurança
- ✅ **Chave não versionada**: Nunca commitada no Git
- ✅ **Encriptação forte**: AES-256-GCM
- ✅ **Validação de integridade**: PRAGMA integrity_check
- ✅ **Backup preventivo**: Antes de operações críticas
- ✅ **Logs de auditoria**: Rastreabilidade completa
- ✅ **Fail-closed (P0.2)**: Bloqueia operações destrutivas sem backup
- ✅ **Soft delete (P0.3)**: Reduz perda de dados por erro humano
- ✅ **Trilha de auditoria**: Registro completo de todas as operações críticas

### 14.2. Boas Práticas
- ✅ **Backup no startup**: Garante backup antes de qualquer operação
- ✅ **Backup antes de deletar**: Proteção contra perda acidental
- ✅ **Backup automático horário (P0.1)**: Backups frequentes dentro de janelas de trabalho
- ✅ **Fail-closed (P0.2)**: Zero "delete sem backup" - operação bloqueada se backup falhar
- ✅ **Soft delete (P0.3)**: Pedidos não são removidos fisicamente, permitindo recuperação fácil
- ✅ **Teste de restauração (P0.4)**: Validação automática de que backups são restauravels
- ✅ **Retenção configurável**: Balanceia espaço vs. histórico
- ✅ **Backup remoto encriptado**: Proteção contra desastres locais
- ✅ **Validação automática**: Detecta corrupção imediatamente
- ✅ **Idempotência**: Evita backups duplicados em janelas curtas

---

## 🔄 15. RESTAURAÇÃO

### 15.1. Processo de Restauração
1. **Listar backups disponíveis**
2. **Selecionar backup** (interativo ou via `--backup`)
3. **Criar backup preventivo** do banco atual (se existir)
4. **Extrair backup** (se for `.zip`)
5. **Copiar para local do banco** (`database.db`)
6. **Validar tamanho** (não pode ser 0)
7. **Registrar no log de auditoria**

### 15.2. Proteções
- ⚠️ **Confirmação dupla**: Requer digitar 'SIM' e 'CONFIRMO' (se backup antigo)
- ⚠️ **Aviso para backups antigos**: Alerta se backup tem mais de 7 dias
- ⚠️ **Backup preventivo**: Cria backup do banco atual antes de restaurar

### 15.3. Desencriptação
```python
from app.utils.encryption import decrypt_file

# Desencriptar arquivo .enc
decrypt_file(
    src="database_20251220_143022.zip.enc",
    dst="database_20251220_143022.zip"
)
```

---

## 📝 16. RESUMO EXECUTIVO

### ✅ O que é feito
- Backup completo do banco SQLite usando método nativo
- Validação de integridade automática
- Compressão opcional (ZIP)
- Encriptação AES-256-GCM para backups remotos

### 📍 Onde é armazenado
- **Local**: `backend/instance/backups/` (não encriptado)
- **Remoto**: Google Drive Desktop (encriptado)

### 🔐 Encriptação
- **Algoritmo**: AES-256-GCM
- **Chave**: Armazenada em `.env` (não versionada)
- **Formato**: `.enc` (header + nonce + ciphertext)

### ⏰ Quando é executado
- **Startup do servidor**: Automático
- **Antes de deletar pedido**: Automático (fail-closed - P0.2)
- **Agendado horário (P0.1)**: A cada 1 hora (Seg-Sex 07:00-18:00, Sáb 07:00-14:00)
- **Teste de restauração (P0.4)**: Diário às 06:30
- **Agendado legado**: Diário (opcional, via Task Scheduler)
- **Manual**: Via CLI ou código

### 🗑️ Retenção
- **Local**: 30 dias (configurável)
- **Remoto**: 90 backups (se usar API) ou ilimitado (Google Drive Desktop)

### 🚨 Segurança
- Chave de encriptação única por instalação
- Validação de integridade em cada backup
- Logs de auditoria completos
- Backup preventivo antes de operações críticas
- **Fail-closed (P0.2)**: Zero "delete sem backup"
- **Soft delete (P0.3)**: Recuperação fácil de dados deletados
- **Trilha de auditoria (P0.3)**: Rastreabilidade completa de operações
- **Teste de restauração (P0.4)**: Validação automática de backups

---

## 📚 17. ARQUIVOS RELACIONADOS

### Código Principal
- `backend/scripts/backup/backup.py` - Gerenciador de backups
- `backend/scripts/backup/restore.py` - Gerenciador de restauração
- `backend/app/utils/backup_helper.py` - Interface programática
- `backend/app/utils/encryption.py` - Encriptação/desencriptação
- `backend/app/utils/gdrive_backup.py` - Upload via API (opcional)

### Sistema P0 - Proteção contra Perda de Dados ⭐ NOVO
- **P0.1 - Backups Automáticos Horários**:
  - `backend/scripts/backup/run_scheduled_backup.py` - Script de backup agendado
  - `backend/scripts/backup/install_backup_task.ps1` - Instalar tarefa no Task Scheduler
  - `backend/scripts/backup/uninstall_backup_task.ps1` - Remover tarefa
- **P0.2 - Fail-Closed**:
  - `backend/app/utils/destructive_action_guard.py` - Guard para operações destrutivas
- **P0.3 - Soft Delete e Auditoria**:
  - `backend/app/models/audit_log.py` - Modelo de log de auditoria
  - `backend/app/utils/audit_logger.py` - Logger de auditoria
  - `backend/scripts/migrations/add_soft_delete_and_audit.py` - Migração de banco
  - `backend/app/models/pedido.py` - Métodos `soft_delete()`, `restore()`, `is_deleted`
  - `backend/app/repositories/pedido_repository.py` - Métodos de soft delete e restore
  - `backend/app/routes/pedidos.py` - Rotas de restore e listagem de deletados
- **P0.4 - Teste de Restauração**:
  - `backend/scripts/backup/restore_smoke_test.py` - Teste automático de restauração
  - `backend/scripts/backup/install_restore_test_task.ps1` - Instalar tarefa
  - `backend/scripts/backup/uninstall_restore_test_task.ps1` - Remover tarefa

### Scripts de Agendamento
- `backend/scripts/backup/agendar_backup_windows.bat` - Agendar backup simples
- `backend/scripts/backup/agendar_backup_gdrive.bat` - Agendar backup encriptado
- `backend/scripts/backup/agendar_backup_gdrive.py` - Script Python para agendamento

### Documentação
- `backend/docs/BACKUP_GDRIVE.md` - Guia de backup encriptado
- `backend/scripts/backup/CRIAR_TAREFA_MANUAL.txt` - Instruções manuais

---

## ❓ 18. PERGUNTAS FREQUENTES

### Q: Os backups são encriptados?
**R**: Apenas os backups enviados para o Google Drive Desktop são encriptados. Os backups locais em `backend/instance/backups/` são **não encriptados** para facilitar restauração rápida.

### Q: Quanto tempo os backups ficam armazenados?
**R**: 
- **Locais**: 30 dias (configurável)
- **Remotos**: 90 backups via API ou ilimitado no Google Drive Desktop

### Q: O backup é automático?
**R**: Sim, em várias situações:
1. **Startup do servidor**: Sempre que o servidor inicia
2. **Antes de deletar pedido/cliente/endereço**: Proteção contra perda acidental (fail-closed - P0.2)
3. **Agendado horário (P0.1)**: A cada 1 hora dentro das janelas (Seg-Sex 07:00-18:00, Sáb 07:00-14:00)
4. **Teste de restauração (P0.4)**: Diário às 06:30 (valida backups)
5. **Agendado legado**: Diário (opcional, via Task Scheduler)

### Q: Como restaurar um backup?
**R**: 
```bash
python backend/scripts/backup/restore.py
```
O script lista todos os backups e permite escolher qual restaurar.

### Q: Onde está a chave de encriptação?
**R**: No arquivo `backend/.env` na variável `BACKUP_ENCRYPTION_KEY`. Se não existir, é gerada automaticamente no primeiro uso.

### Q: Os backups são versionados no Git?
**R**: **NÃO**. Os backups ficam em `backend/instance/backups/` que está no `.gitignore`. Apenas o código de backup é versionado.

### Q: O que acontece se o backup falhar?
**R**: Depende do contexto:
- **No startup**: Servidor continua inicializando (não bloqueia)
- **Em operação destrutiva (P0.2)**: **Operação é BLOQUEADA** - retorna HTTP 503
  - Mensagem: "Backup necessário antes de operação destrutiva. Falha ao criar backup. Operação bloqueada por segurança."
  - Com `allow_override=True`: Permite override mas registra em auditoria
- **Em backup agendado (P0.1)**: Erro é registrado no log, próximo backup tenta novamente
- **Erro é sempre registrado**: No log de auditoria

### Q: Posso desabilitar backups automáticos?
**R**: Não há flag para desabilitar, mas você pode:
- Ignorar erros de backup (sistema continua funcionando)
- Remover chamadas de `create_backup()` (não recomendado)
- Desinstalar tarefas do Task Scheduler: `uninstall_backup_task.ps1` e `uninstall_restore_test_task.ps1`

### Q: O que é soft delete? (P0.3)
**R**: Soft delete é uma técnica onde pedidos não são removidos fisicamente do banco, apenas marcados como deletados com a coluna `deleted_at`. Isso permite:
- Recuperação fácil de pedidos deletados acidentalmente
- Histórico completo de pedidos
- Redução massiva de perda de dados por erro humano
- Restauração via `POST /api/pedidos/<id>/restore`

### Q: Como funciona o fail-closed? (P0.2)
**R**: Fail-closed significa que se o backup falhar antes de uma operação destrutiva, a operação é **bloqueada** e retorna erro HTTP 503. Isso garante "zero delete sem backup". A operação só é permitida se:
1. Backup for criado com sucesso, OU
2. `allow_override=True` for usado (com auditoria obrigatória)

### Q: O que é o teste de restauração? (P0.4)
**R**: É um teste automático que executa diariamente às 06:30 e:
1. Encontra o backup mais recente
2. Restaura em ambiente sandbox (temporário)
3. Executa `PRAGMA integrity_check`
4. Faz sanity checks (tabelas existem, contagens válidas)
5. Limpa arquivos temporários
6. Registra resultado no log

Isso garante que os backups são restauravels quando necessário.

### Q: Como consultar a trilha de auditoria? (P0.3)
**R**: 
```sql
-- Via SQL
SELECT * FROM audit_log ORDER BY ts DESC LIMIT 10;

-- Via Python
from app import create_app, db
from app.models import AuditLog

app = create_app()
with app.app_context():
    logs = AuditLog.query.order_by(AuditLog.ts.desc()).limit(10).all()
    for log in logs:
        print(f"{log.ts} | {log.action} | {log.entity_type} #{log.entity_id}")
```

### Q: O que acontece se eu deletar um pedido agora?
**R**: Com P0.2 e P0.3 implementados:
1. Sistema tenta criar backup (fail-closed)
2. Se backup falhar: Operação é **bloqueada** (HTTP 503)
3. Se backup suceder: Pedido é **soft-deleted** (não removido fisicamente)
4. `deleted_at` é preenchido com timestamp atual
5. Evento é registrado em `audit_log`
6. Pedido não aparece mais nas listagens normais
7. Pode ser restaurado via `POST /api/pedidos/<id>/restore`

---

## 🎯 19. SISTEMA P0 - PROTEÇÃO CONTRA PERDA DE DADOS ⭐ NOVO

### 19.1. Visão Geral
O Sistema P0 implementa 4 camadas de proteção contra perda de dados, reutilizando o sistema de backup existente e adicionando garantias adicionais.

### 19.2. Componentes

#### P0.1 - Backups Automáticos Horários
- **Objetivo**: Backups frequentes durante horário de trabalho
- **Frequência**: A cada 1 hora
- **Janelas**: Seg-Sex 07:00-18:00, Sáb 07:00-14:00, Dom não executa
- **Idempotência**: Não cria backup se já existe um nos últimos 55 minutos
- **Instalação**: `install_backup_task.ps1`
- **Logs**: `scheduled_backup.log`

#### P0.2 - Fail-Closed para Operações Destrutivas
- **Objetivo**: Zero "delete sem backup"
- **Comportamento**: Bloqueia operação se backup falhar
- **Rotas protegidas**: Todas as rotas DELETE críticas
- **Resposta**: HTTP 503 com mensagem clara
- **Override**: Suportado com auditoria obrigatória

#### P0.3 - Soft Delete + Trilha de Auditoria
- **Objetivo**: Redução massiva de perda por erro humano
- **Soft Delete**: Pedidos não são removidos fisicamente
- **Auditoria**: Tabela `audit_log` registra todas as operações críticas
- **Recuperação**: Endpoints para restaurar e listar deletados
- **Migração**: `add_soft_delete_and_audit.py`

#### P0.4 - Teste Recorrente de Restauração
- **Objetivo**: Validar que backups são restauravels
- **Frequência**: Diário às 06:30
- **Processo**: Restaura em sandbox, valida integridade, faz sanity checks
- **Instalação**: `install_restore_test_task.ps1`
- **Logs**: `restore_test.log`

### 19.3. Fluxo Completo de Proteção

```
Operação Destrutiva (DELETE)
    ↓
[P0.2] Fail-Closed: Tentar criar backup
    ↓
Backup criado com sucesso?
    ├─ SIM → Continuar
    └─ NÃO → BLOQUEAR (HTTP 503)
            ↓
        allow_override=True?
            ├─ SIM → Registrar OVERRIDE_DELETE em auditoria → Continuar
            └─ NÃO → Operação bloqueada
    ↓
[P0.3] Soft Delete: Marcar deleted_at (não remover fisicamente)
    ↓
[P0.3] Auditoria: Registrar DELETE em audit_log
    ↓
Operação concluída
```

### 19.4. Testes Unitários
Todos os componentes P0 têm testes unitários:
- `tests/test_scheduled_backup.py` - Testes de janela e idempotência
- `tests/test_fail_closed.py` - Testes de bloqueio
- `tests/test_soft_delete.py` - Testes de soft delete e restore
- `tests/test_audit_log.py` - Testes de auditoria
- `tests/test_restore_smoke_test.py` - Testes do smoke test

### 19.5. Checklist de Instalação
- [ ] Executar migração: `python scripts/migrations/add_soft_delete_and_audit.py`
- [ ] Instalar tarefa de backup: `install_backup_task.ps1`
- [ ] Instalar tarefa de teste: `install_restore_test_task.ps1`
- [ ] Verificar tarefas no Task Scheduler
- [ ] Testar fail-closed (tentar deletar sem backup funcionando)
- [ ] Testar soft delete (deletar pedido e verificar `deleted_at`)
- [ ] Testar restore (restaurar pedido deletado)
- [ ] Verificar logs de auditoria
- [ ] Executar testes unitários: `pytest tests/ -v`

---

## 🔒 20. P1 - ROBUSTEZ OPERACIONAL E CONFIABILIDADE ⭐ NOVO

### 20.1. Visão Geral

O pacote P1 adiciona camadas de robustez operacional ao sistema de backup, focando em reduzir falhas "annoying" (disco cheio, backups inutilizáveis, retenção ruim, offsite não sincronizado, falta de visibilidade) e acelerar diagnóstico.

### 20.2. Componentes

#### P1.1 - Validação Forte e Padronizada de Restore
- **Objetivo**: Validação única e robusta para restore real e restore-smoke-test
- **Módulo**: `scripts/backup/validate_db.py`
- **Validações**:
  - `PRAGMA integrity_check` (obrigatório)
  - Verificação de schema_version (compatibilidade)
  - Sanity checks (tabelas essenciais, queries básicas)
  - Invariantes opcionais (foreign keys)
- **Migração**: `scripts/migrations/add_app_meta_schema_version.py`
- **Schema Version**: `APP_SCHEMA_VERSION = '1.0'` (em `config.py`)
- **Integração**: Usado por `restore.py` e `restore_smoke_test.py`
- **Testes**: `tests/test_validate_db.py`

#### P1.2 - Política de Retenção GFS
- **Objetivo**: Retenção tipo GFS (Grandfather-Father-Son) para backups locais e remotos
- **Módulo**: `scripts/backup/retention.py`
- **Script**: `scripts/backup/cleanup_backups.py`
- **Política**: Configurável via `.env`:
  - `BACKUP_RETENTION_HOURLY=48`
  - `BACKUP_RETENTION_DAILY=30`
  - `BACKUP_RETENTION_WEEKLY=12`
  - `BACKUP_RETENTION_MONTHLY=12`
- **Algoritmo**: Determinístico baseado em timestamps dos nomes dos arquivos
- **Slots**: HOURLY, DAILY, WEEKLY, MONTHLY
- **Uso**: `python scripts/backup/cleanup_backups.py --local --remote`
- **Testes**: `tests/test_retention.py`

#### P1.3 - Verificação de Offsite (Drive Desktop)
- **Objetivo**: Verificar que backup foi realmente recebido no diretório remoto
- **Módulo**: `scripts/backup/remote_verify.py`
- **Verificações**:
  - Arquivo existe no destino
  - Tamanho bate com origem
  - Hash opcional (SHA-256)
  - Stability check (re-verificar tamanho após alguns segundos)
- **Integração**: Usado em `backup.py` (create_encrypted_backup)
- **Status**: Registra `last_remote_ok_at` e `last_remote_error`
- **Configuração**: `BACKUP_REMOTE_VERIFY_HASH=false` (opcional)
- **Testes**: `tests/test_remote_verify.py`

#### P1.4 - Diretório Secundário Local
- **Objetivo**: Segundo destino local (preferencialmente outro drive) para evitar que DB e backup morram juntos
- **Configuração**: `BACKUP_SECONDARY_DIR` (opcional, em `.env`)
- **Módulo**: `scripts/backup/drive_utils.py`
- **Funcionalidade**: `check_drive_separation()` - detecta e avisa quando drives são iguais
- **Integração**: Automática em `backup.py` (create_backup)
- **Verificação**: Tamanho e hash (opcional)
- **Testes**: `tests/test_drive_utils.py`

#### P1.5 - Health/Status Operacional
- **Objetivo**: Status persistente e visibilidade do estado do backup
- **Módulo**: `scripts/backup/status.py`
- **Arquivo**: `backend/instance/backup_status.json`
- **Campos**:
  - `last_backup_ok_at`, `last_backup_error`
  - `last_remote_ok_at`, `last_remote_error`
  - `last_restore_test_ok_at`, `last_restore_test_error`
  - `last_cleanup_ok_at`, `last_cleanup_error`
  - `backups_local_count`, `backups_remote_count`
- **Endpoint**: `GET /api/admin/backup/health`
- **Health Rules**:
  - FAIL: último backup OK > 24h OU último restore-test falhou
  - WARN: remoto não OK > 24h, ou cleanup falhou
  - OK: tudo operacional
- **Integração**: Atualizado por backup.py, restore_smoke_test.py, cleanup_backups.py
- **Configuração**: `BACKUP_HEALTH_MAX_AGE_HOURS=24` (opcional)
- **Testes**: `tests/test_backup_status.py`

### 20.3. Fluxo Completo P1

```
Backup Criado
    ↓
[P1.1] Validação (integrity_check, schema, sanity)
    ↓
[P1.4] Cópia para diretório secundário (se configurado)
    ↓
[P1.3] Verificação remota (tamanho, hash, stability)
    ↓
[P1.5] Atualizar status (last_backup_ok_at, last_remote_ok_at)
    ↓
[P1.2] Cleanup GFS (opcional, após backup)
    ↓
[P1.5] Atualizar status (last_cleanup_ok_at)

Restore Test (P0.4)
    ↓
[P1.1] Validação padronizada
    ↓
[P1.5] Atualizar status (last_restore_test_ok_at/error)
```

### 20.4. Testes Unitários
Todos os componentes P1 têm testes unitários:
- `tests/test_validate_db.py` - Validação padronizada
- `tests/test_retention.py` - Algoritmo GFS
- `tests/test_remote_verify.py` - Verificação remota
- `tests/test_drive_utils.py` - Detecção de drives
- `tests/test_backup_status.py` - Status e health

### 20.5. Checklist de Configuração P1
- [ ] Executar migração: `python scripts/migrations/add_app_meta_schema_version.py`
- [ ] Configurar `.env` com variáveis P1 (veja guia abaixo)
- [ ] (Opcional) Configurar `BACKUP_SECONDARY_DIR` para diretório em outro drive
- [ ] Verificar endpoint de health: `GET /api/admin/backup/health`
- [ ] Testar cleanup GFS: `python scripts/backup/cleanup_backups.py --dry-run`
- [ ] Verificar arquivo de status: `backend/instance/backup_status.json`
- [ ] Executar testes unitários: `pytest tests/test_validate_db.py tests/test_retention.py tests/test_remote_verify.py tests/test_backup_status.py tests/test_drive_utils.py -v`

---

## 📚 21. REFERÊNCIAS E LINKS ÚTEIS

### Documentação Relacionada
- `backend/docs/BACKUP_P1_GUIA.md` - Guia detalhado de configuração e troubleshooting do P1
- `backend/docs/MEMORIA_BACKUP_SISTEMA.md` - Referência rápida do sistema de backup

### Arquivos de Configuração
- `backend/.env` - Variáveis de ambiente (incluindo P1)
- `backend/app/config.py` - Configurações da aplicação (incluindo `APP_SCHEMA_VERSION`)

### Scripts de Migração
- `backend/scripts/migrations/add_soft_delete_and_audit.py` - Migração P0.3
- `backend/scripts/migrations/add_app_meta_schema_version.py` - Migração P1.1

### Testes
- `backend/tests/test_validate_db.py` - Testes P1.1
- `backend/tests/test_retention.py` - Testes P1.2
- `backend/tests/test_remote_verify.py` - Testes P1.3
- `backend/tests/test_drive_utils.py` - Testes P1.4
- `backend/tests/test_backup_status.py` - Testes P1.5

---

**Última atualização**: 2026-01-02  
**Versão do documento**: 3.1  
**Novidades**: 
- Sistema P1 completo (P1.1, P1.2, P1.3, P1.4, P1.5) implementado e documentado
- Seção de comandos P1 adicionada (10.12)
- Configurações P1 documentadas (12.1, 12.3)
- Validação padronizada documentada (11.3)
- Health/Status documentado (13.3, 13.4)
- Seção de referências adicionada (21)

