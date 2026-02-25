# Sistema de Backup

Este documento consolida informações sobre o sistema de backup do Plante Uma Flor.

## Visão Geral

O sistema de backup é **multi-camadas** e **integrado profundamente** ao sistema, garantindo proteção automática contra perda de dados através de 4 camadas (Sistema P0).

## Sistema P0 - Proteção contra Perda

### P0.1 - Backups Automáticos Horários

- **Frequência**: A cada 1 hora
- **Janelas**: Seg-Sex 07:00-18:00, Sáb 07:00-14:00, Dom não executa
- **Script**: `backend/scripts/backup/run_scheduled_backup.py`
- **Idempotência**: Não cria backup se já existe um nos últimos 55 minutos
- **Instalação**: `backend/scripts/backup/install_backup_task.ps1`

### P0.2 - Fail-Closed

- **Zero "delete sem backup"**: Operações destrutivas (DELETE) bloqueadas se backup falhar
- **Resposta**: HTTP 503 Service Unavailable
- **Implementação**: `backend/app/utils/destructive_action_guard.py`
- **Rotas protegidas**:
  - `DELETE /api/pedidos/<id>` → Soft delete (P0.3)
  - `DELETE /api/clientes/<id>` → Hard delete
  - `DELETE /api/clientes/enderecos/<id>` → Hard delete
  - `DELETE /api/fontes-pedido/<id>` → Hard delete

### P0.3 - Soft Delete + Auditoria

- **Soft Delete**: Pedidos não são removidos fisicamente (coluna `deleted_at`)
- **Trilha de Auditoria**: Tabela `audit_log` registra todas as ações
- **Endpoints**: `POST /api/pedidos/<id>/restore`, `GET /api/pedidos/deleted`
- **Migration**: `backend/scripts/migrations/add_soft_delete_and_audit.py`

### P0.4 - Teste Recorrente de Restauração

- **Frequência**: Diária às 06:30
- **Script**: `backend/scripts/backup/restore_smoke_test.py`
- **Valida**: Integridade e restaurabilidade dos backups
- **Instalação**: `backend/scripts/backup/install_restore_test_task.ps1`

## Integração com o Sistema

### 1. Inicialização do Servidor

- **Gatilho**: Startup do servidor Flask (`main.py`)
- **Quando**: Apenas no processo pai (evita duplicação no reloader)
- **Comportamento**: Não bloqueia inicialização se falhar

```python
if not is_reloader:
    with app.app_context():
        backup_path = create_backup(reason='startup', silent=False)
```

### 2. Operações Destrutivas (Fail-Closed)

Todas as rotas `DELETE` críticas são protegidas:

```python
ensure_backup_before_destructive_action(
    reason='delete_pedido',
    context={'pedido_id': pedido_id}
)
# Se falhar → HTTP 503 com mensagem clara
```

### 3. Backup Agendado

Executado automaticamente via tarefa agendada do Windows (P0.1).

## Arquivos de Backup

### Formato

- **Nome padrão**: `database_YYYYMMDD_HHMMSS.db` ou `.zip`
- **Exemplo**: `database_20251220_143022.zip`
- **Compressão**: Opcional (ZIP com DEFLATE)

### Localização

#### Backups Locais (Não Encriptados)

- **Diretório**: `backend/instance/backups/`
- **Formato**: `.db` ou `.zip`
- **Propósito**: Acesso rápido para restauração local
- **Retenção**: 30 dias (configurável)

#### Backups Encriptados (Google Drive Desktop)

- **Diretório**: `C:\Users\<USER>\Meu Drive\Plante Uma Flor Confidential\Database - Pedidos Gestor\`
- **Formato**: `.enc` (arquivo encriptado)
- **Propósito**: Backup remoto seguro na nuvem
- **Sincronização**: Automática via Google Drive Desktop
- **Retenção**: Ilimitada (gerenciada manualmente ou via API)

## Encriptação

### Algoritmo

- **Algoritmo**: AES-256-GCM (Advanced Encryption Standard)
- **Tamanho da chave**: 256 bits (32 bytes)
- **Modo**: GCM (Galois/Counter Mode) - autenticado e seguro
- **Biblioteca**: `cryptography.hazmat.primitives.ciphers.aead.AESGCM`

### Chave de Encriptação

- **Armazenamento**: Variável de ambiente `BACKUP_ENCRYPTION_KEY` no arquivo `.env`
- **Formato**: Base64 URL-safe
- **Geração**: Automática no primeiro uso se não existir
- **Localização**: `backend/.env`

### Formato do Arquivo Encriptado

```
[Header: 2 bytes] + [Nonce: 12 bytes] + [Ciphertext + Tag]
     'v1'              Random          Encrypted data
```

### Segurança

- ✅ **Chave única**: Cada instalação gera sua própria chave
- ✅ **Nonce aleatório**: Cada arquivo tem nonce único (evita ataques de repetição)
- ✅ **Autenticação**: GCM garante integridade (detecta modificações)
- ✅ **Chave não versionada**: Nunca commitada no Git

## Funções Principais

### `create_backup(reason, compress=True, silent=False)`

Cria backup programaticamente. Retorna `Path` ou `None`.

**Localização**: `backend/app/utils/backup_helper.py`

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

## Endpoints da API

### Status de Backup

**GET** `/api/backup/status`

Retorna estatísticas dos backups (total, tamanho, último backup, etc).

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

## Comandos Úteis

### Backup Manual

```bash
cd backend/scripts/backup
python backup.py
```

### Backup com Upload para Google Drive

```bash
python backup.py --upload-drive --keep-remote 90
```

### Verificar Health

```bash
curl -u admin:<password> http://localhost:5000/api/admin/backup/health
```

### Limpar Backups Antigos (Simulação)

```bash
python backend/scripts/backup/cleanup_backups.py --local --dry-run
```

### Ver Status do Backup

```bash
cat backend/instance/backup_status.json | python -m json.tool
```

## Logs e Auditoria

### Logs de Arquivo

- `backend/instance/logs/backup_audit.log` - Logs de backup/restore
- `backend/instance/logs/scheduled_backup.log` - Logs de backup agendado (P0.1)
- `backend/instance/logs/restore_test.log` - Logs de teste de restauração (P0.4)
- `backend/instance/logs/backup_gdrive.log` - Logs de uploads para Google Drive

### Trilha de Auditoria (Banco)

- **Tabela**: `audit_log`
- **Consulta**: `SELECT * FROM audit_log ORDER BY ts DESC LIMIT 10;`
- **Ações registradas**: CREATE, UPDATE, DELETE, RESTORE, OVERRIDE_DELETE

## Configuração

### Variáveis de Ambiente (`backend/.env`)

```env
BACKUP_ENCRYPTION_KEY=<chave_base64>  # Gerada automaticamente se não existir
GDRIVE_BACKUP_DIR=C:\Users\<USER>\Meu Drive\...  # Opcional
BACKUP_HEALTH_MAX_AGE_HOURS=24  # Idade máxima para considerar backup válido
```

### Estrutura de Arquivos

```
backend/
├── app/utils/
│   ├── backup_helper.py          # Interface programática
│   ├── destructive_action_guard.py  # Fail-closed (P0.2)
│   ├── audit_logger.py          # Logger de auditoria (P0.3)
│   └── encryption.py            # Encriptação AES-256-GCM
├── scripts/backup/
│   ├── backup.py                # Gerenciador de backups
│   ├── restore.py               # Gerenciador de restauração
│   ├── run_scheduled_backup.py  # Backup agendado (P0.1)
│   └── restore_smoke_test.py    # Teste de restauração (P0.4)
└── instance/
    ├── backups/                 # Backups locais
    └── logs/                    # Logs de backup
```

## Documentação de Referência

Para informações mais detalhadas, consulte:

- **[ESTUDO_BACKUP_COMPLETO.md](ESTUDO_BACKUP_COMPLETO.md)** - Documentação completa e detalhada do sistema de backup
- **[BACKUP_P1_GUIA.md](BACKUP_P1_GUIA.md)** - Guia de configuração do pacote P1 (Robustez Operacional)
- **[BACKUP_GDRIVE.md](BACKUP_GDRIVE.md)** - Configuração de backup encriptado para Google Drive
- **[MEMORIA_BACKUP_SISTEMA.md](MEMORIA_BACKUP_SISTEMA.md)** - Memória técnica do sistema de backup

---

**Última atualização**: 2026-01-04
