# 📚 Guia de Configuração: Pacote P1 - Robustez Operacional e Confiabilidade

Este guia detalha como configurar e usar as funcionalidades do pacote P1 do sistema de backup.

---

## 📋 Índice

1. [Configuração Inicial](#configuração-inicial)
2. [P1.1 - Validação Padronizada](#p11---validação-padronizada)
3. [P1.2 - Retenção GFS](#p12---retenção-gfs)
4. [P1.3 - Verificação Offsite](#p13---verificação-offsite)
5. [P1.4 - Diretório Secundário](#p14---diretório-secundário)
6. [P1.5 - Health/Status](#p15---healthstatus)
7. [Troubleshooting](#troubleshooting)

---

## 🔧 Configuração Inicial

### Variáveis de Ambiente

Adicione as seguintes variáveis ao arquivo `.env` (em `backend/.env`):

```env
# Schema Version (P1.1)
APP_SCHEMA_VERSION=1.0

# Retenção GFS (P1.2)
BACKUP_RETENTION_HOURLY=48
BACKUP_RETENTION_DAILY=30
BACKUP_RETENTION_WEEKLY=12
BACKUP_RETENTION_MONTHLY=12

# Verificação Remota (P1.3)
BACKUP_REMOTE_VERIFY_HASH=false

# Diretório Secundário (P1.4) - Opcional
BACKUP_SECONDARY_DIR=

# Health/Status (P1.5)
BACKUP_HEALTH_MAX_AGE_HOURS=24
```

### Migração de Schema

Execute a migração para criar a tabela `app_meta`:

```bash
python scripts/migrations/add_app_meta_schema_version.py
```

---

## ✅ P1.1 - Validação Padronizada

### O que faz

Validação robusta e padronizada usada tanto em restore real quanto em restore-smoke-test.

### Validações Implementadas

1. **PRAGMA integrity_check** (obrigatório)
2. **Schema Version** - Verifica compatibilidade do schema
3. **Sanity Checks** - Tabelas essenciais, queries básicas
4. **Invariantes** (opcional) - Foreign keys, etc

### Uso

A validação é automática em:
- `restore.py` - Após restaurar backup
- `restore_smoke_test.py` - Durante teste de restauração

Se a validação falhar, o restore será revertido (rollback).

---

## 🗑️ P1.2 - Retenção GFS

### O que é GFS

GFS (Grandfather-Father-Son) é uma política de retenção que mantém backups em diferentes níveis:
- **Hourly**: Backups da última hora (hoje)
- **Daily**: Backups do dia (esta semana)
- **Weekly**: Backups da semana (este mês)
- **Monthly**: Backups do mês (histórico)

### Como Funciona

O algoritmo:
1. Extrai timestamp do nome do arquivo (`database_YYYYMMDD_HHMMSS.*`)
2. Categoriza cada backup em slot (hourly/daily/weekly/monthly)
3. Mantém N backups mais recentes em cada slot (conforme política)
4. Deleta o resto

### Executar Cleanup Manualmente

```bash
# Simular (dry-run)
python scripts/backup/cleanup_backups.py --local --dry-run

# Executar em backups locais
python scripts/backup/cleanup_backups.py --local

# Executar em backups remotos
python scripts/backup/cleanup_backups.py --remote

# Executar em ambos
python scripts/backup/cleanup_backups.py

# Customizar política
python scripts/backup/cleanup_backups.py --local --policy-hourly 24 --policy-daily 14
```

### Configuração de Limites

Edite `.env`:
```env
BACKUP_RETENTION_HOURLY=48   # Manter 48 backups hourly
BACKUP_RETENTION_DAILY=30    # Manter 30 backups daily
BACKUP_RETENTION_WEEKLY=12   # Manter 12 backups weekly
BACKUP_RETENTION_MONTHLY=12  # Manter 12 backups monthly
```

---

## 🌐 P1.3 - Verificação Offsite

### O que faz

Verifica que o backup foi realmente recebido no diretório remoto (Google Drive Desktop) através de heurísticas objetivas.

### Verificações

1. Arquivo existe no destino
2. Tamanho bate com origem
3. Hash SHA-256 (opcional)
4. Stability check (re-verificar tamanho após 3-5 segundos)

### Configuração

```env
# Ativar verificação por hash (mais lento, mais seguro)
BACKUP_REMOTE_VERIFY_HASH=true

# Desativar hash (padrão, mais rápido)
BACKUP_REMOTE_VERIFY_HASH=false
```

### Status

O status remoto é registrado em `backup_status.json`:
- `last_remote_ok_at` - Último backup remoto bem-sucedido
- `last_remote_error` - Último erro de backup remoto

Se o diretório remoto não estiver acessível, o backup local não falha (apenas registra warning).

---

## 💾 P1.4 - Diretório Secundário

### Objetivo

Armazenar backup em segundo destino local (preferencialmente outro drive) para evitar que DB e backup morram juntos.

### Configuração

```env
# Caminho para diretório secundário (opcional)
BACKUP_SECONDARY_DIR=D:\Backups\PlanteUmaFlor
```

### Verificação de Drive

O sistema detecta automaticamente se DB, backup local e backup secundário estão no mesmo drive e gera warnings:

```
[AVISO] Banco de dados e backup local estão no mesmo drive (C:). 
        Considere usar BACKUP_SECONDARY_DIR em outro drive para proteção adicional.
```

### Funcionamento

- Backup é copiado para diretório secundário após criação
- Verificação de tamanho (e hash opcional) é realizada
- Se falhar, não bloqueia backup principal (apenas registra warning)

---

## 📊 P1.5 - Health/Status

### Arquivo de Status

O status é persistido em: `backend/instance/backup_status.json`

Formato:
```json
{
  "last_backup_ok_at": "2026-01-02T14:30:00",
  "last_backup_error": null,
  "last_remote_ok_at": "2026-01-02T14:30:05",
  "last_remote_error": null,
  "last_restore_test_ok_at": "2026-01-02T06:30:00",
  "last_restore_test_error": null,
  "last_cleanup_ok_at": "2026-01-02T15:00:00",
  "last_cleanup_error": null,
  "backups_local_count": 25,
  "backups_remote_count": 150
}
```

### Endpoint de Health

**GET** `/api/admin/backup/health`

Requere autenticação (usar `requires_edit_auth`).

Resposta:
```json
{
  "success": true,
  "health": "OK",
  "status": { ... },
  "issues": [],
  "last_update": "2026-01-02T14:30:00"
}
```

### Regras de Health

- **FAIL**: 
  - Último backup OK há mais de 24h
  - Último restore-test falhou

- **WARN**: 
  - Remoto não OK há mais de 24h
  - Cleanup falhou

- **OK**: 
  - Tudo operacional

### Configuração

```env
# Idade máxima (em horas) para considerar backup válido
BACKUP_HEALTH_MAX_AGE_HOURS=24
```

### Interpretação

- `health: "OK"` - Sistema operacional
- `health: "WARN"` - Problemas não críticos (verificar remoto/cleanup)
- `health: "FAIL"` - Problema crítico (backup muito antigo ou restore test falhou)

---

## 🔍 Troubleshooting

### Problema: Status mostra "FAIL" mesmo com backups recentes

**Verificar:**
1. Arquivo `backup_status.json` existe e é legível?
2. Formato de timestamp está correto (ISO)?
3. Restore test está falhando?

**Solução:**
```bash
# Ver status manualmente
cat backend/instance/backup_status.json

# Forçar atualização (criar novo backup)
python scripts/backup/backup.py
```

### Problema: Verificação remota sempre falha

**Verificar:**
1. Google Drive Desktop está rodando?
2. Diretório remoto está acessível?
3. Arquivo está sendo escrito quando verificação roda?

**Solução:**
```bash
# Verificar diretório remoto
ls "C:\Users\<USER>\Meu Drive\Plante Uma Flor Confidential\Database - Pedidos Gestor"

# Desativar verificação por hash (mais rápido)
BACKUP_REMOTE_VERIFY_HASH=false
```

### Problema: Cleanup GFS deletando backups recentes

**Verificar:**
1. Timestamps dos nomes dos arquivos estão corretos?
2. Política de retenção está adequada?

**Solução:**
```bash
# Fazer dry-run primeiro
python scripts/backup/cleanup_backups.py --local --dry-run

# Aumentar limites se necessário
BACKUP_RETENTION_HOURLY=72
BACKUP_RETENTION_DAILY=60
```

### Problema: Diretório secundário não está recebendo backups

**Verificar:**
1. `BACKUP_SECONDARY_DIR` está configurado corretamente?
2. Diretório existe e tem permissões de escrita?
3. Espaço em disco suficiente?

**Solução:**
```bash
# Verificar configuração
echo %BACKUP_SECONDARY_DIR%

# Criar diretório manualmente se necessário
mkdir D:\Backups\PlanteUmaFlor

# Verificar logs de backup
tail backend/instance/logs/backup_audit.log
```

### Problema: Validação de restore sempre falha

**Verificar:**
1. Schema version está correto?
2. Tabelas essenciais existem?
3. Banco não está corrompido?

**Solução:**
```bash
# Executar validação manualmente
python -c "
from scripts.backup.validate_db import validate_restored_db
from pathlib import Path
from app.config import Config

result = validate_restored_db(
    db_path=Config.DATABASE_PATH,
    app_schema_version=Config.APP_SCHEMA_VERSION,
    verbose=True
)
print(result)
"

# Verificar integridade manualmente
sqlite3 database.db "PRAGMA integrity_check;"
```

---

## 📝 Comandos Rápidos

```bash
# Ver health do sistema
curl -u admin:<password> http://localhost:5000/api/admin/backup/health

# Limpar backups antigos (dry-run)
python scripts/backup/cleanup_backups.py --local --dry-run

# Ver status manualmente
cat backend/instance/backup_status.json | python -m json.tool

# Executar migração de schema
python scripts/migrations/add_app_meta_schema_version.py

# Testar validação
python -m pytest tests/test_validate_db.py -v
```

---

**Última atualização**: 2026-01-02

