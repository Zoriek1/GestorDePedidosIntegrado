# Guia de Teste das Automacoes

Este documento descreve como verificar se as automacoes do sistema estao funcionando corretamente.

## Automacoes Disponiveis

| Automacao | Funcao | Agendamento |
|-----------|--------|-------------|
| Backup Agendado | Cria backup do banco de dados | Horario (Seg-Sex 07-18h, Sab 07-14h) |
| Exportacao Vendas | Exporta vendas para Google Sheets | Diario as 19:00 |
| Meta CAPI | Envia eventos de compra para Meta | Diario (ou manual) |

---

## 1. Backup Agendado

### 1.1 Verificar se a Tarefa Agendada Existe (Windows)

```powershell
# Listar tarefas de backup
Get-ScheduledTask | Where-Object {$_.TaskName -like "*backup*"} | Format-Table TaskName, State, LastRunTime

# Ou verificar tarefa especifica
Get-ScheduledTask -TaskName "GestorPedidos_BackupHorario" -ErrorAction SilentlyContinue
```

**Resultado esperado:** Tarefa listada com `State: Ready`

**Nota:** A tarefa antiga `GestorPedidos_BackupDiario1` pode existir mas estar configurada incorretamente. 
Verifique se esta usando o script correto (`run_scheduled_backup.py`).

### 1.2 Verificar Detalhes da Tarefa

```powershell
# Verificar ultima execucao e resultado
Get-ScheduledTaskInfo -TaskName "GestorPedidos_BackupHorario" | Format-List

# Verificar acoes (script e Python usados)
$task = Get-ScheduledTask -TaskName "GestorPedidos_BackupHorario"
$task.Actions | Format-List

# Verificar triggers (horarios de execucao)
$task.Triggers | Select-Object -First 3 | Format-List
```

**Resultado esperado:**
- `LastTaskResult: 0` = Sucesso
- `LastTaskResult: 2147942667` = Erro de configuracao (remover e reinstalar)
- Execute: caminho completo do Python (nao stub da Store)
- Arguments: caminho completo do `run_scheduled_backup.py`
- WorkingDirectory: caminho do diretorio `backend`

### 1.3 Testar Script de Backup Manualmente

```powershell
cd "C:\Gestor de Pedidos Plante uma flor\backend"
python scripts/backup/run_scheduled_backup.py
```

**Resultados possiveis:**
- `[INFO] Fora da janela de execucao (Dia HH:MM) - ignorado` - Normal fora do horario
- `[INFO] Backup recente encontrado (...) - idempotencia ativa, ignorado` - Backup ja existe
- `[SUCCESS] Backup criado com sucesso: database_YYYYMMDD_HHMMSS.zip` - Backup criado

### 1.4 Verificar Backups Existentes

```powershell
# Listar backups recentes
Get-ChildItem "C:\Gestor de Pedidos Plante uma flor\backend\instance\backups" | 
    Sort-Object LastWriteTime -Descending | 
    Select-Object -First 5 Name, @{N='SizeMB';E={[math]::Round($_.Length/1MB, 2)}}, LastWriteTime
```

**Resultado esperado:** Lista de arquivos `database_YYYYMMDD_HHMMSS.zip`

### 1.5 Verificar Status do Backup via API

```powershell
# Se o servidor estiver rodando
Invoke-RestMethod -Uri "http://localhost:5000/api/backup/status" -Method GET
```

**Resultado esperado:**
```json
{
  "success": true,
  "last_backup": "2026-01-15T10:00:00",
  "backup_count": 42,
  "total_size_mb": 125.5
}
```

### 1.6 Forcar Backup Manual (Ignorando Janela)

```powershell
cd "C:\Gestor de Pedidos Plante uma flor\backend"
# Opcao 1: Script batch (se existir)
scripts\backup\backup_manual.bat

# Opcao 2: Via Python diretamente (precisa estar no diretorio backend)
python -c "import sys; from pathlib import Path; sys.path.insert(0, str(Path.cwd())); from app.utils.backup_helper import create_backup; result = create_backup(reason='manual_test'); print(f'Backup criado: {result}' if result else 'Erro ao criar backup')"

# Opcao 3: Criar script temporario
python scripts/backup/backup.py
```

---

## 2. Exportacao de Vendas (Google Sheets)

### 2.1 Verificar se a Tarefa Agendada Existe

```powershell
# Verificar tarefa de exportacao
Get-ScheduledTask -TaskName "GestorPedidos_ExportarVendas" -ErrorAction SilentlyContinue | Format-List TaskName, State
```

**Resultado esperado:** Tarefa listada com `State: Ready`

### 2.2 Verificar Detalhes da Tarefa

```powershell
# Verificar ultima execucao e resultado
Get-ScheduledTaskInfo -TaskName "GestorPedidos_ExportarVendas" | Format-List

# Verificar acoes e triggers
$task = Get-ScheduledTask -TaskName "GestorPedidos_ExportarVendas"
$task.Actions | Format-List
$task.Triggers | Format-List
```

**Resultado esperado:**
- `LastTaskResult: 0` = Sucesso
- `LastTaskResult: 2` = Erro de configuracao (remover e reinstalar)
- Execute: caminho completo do Python (nao stub da Store)
- Arguments: caminho completo do `exportar_vendas_sheets.py`
- WorkingDirectory: caminho do diretorio `backend` (OBRIGATORIO para imports funcionarem)
- Trigger: Diario as 19:00

### 2.3 Testar Script Manualmente

```powershell
cd "C:\Gestor de Pedidos Plante uma flor\backend"
python scripts/export/exportar_vendas_sheets.py
```

**Resultado esperado:**
```
==================================================
EXPORTACAO DE VENDAS - JANEIRO/2026
==================================================
[OK] Autenticacao Google OK
[OK] Planilha encontrada: VENDAS_JANEIRO_2026
Total de pedidos no mes: 150
...
```

### 2.4 Verificar Credenciais do Google

```powershell
cd "C:\Gestor de Pedidos Plante uma flor\backend"
python -c "from app import create_app; from scripts.export.exportar_vendas_sheets import _resolve_credentials_path; import os; os.chdir(r'C:\Gestor de Pedidos Plante uma flor\backend'); print('Credenciais:', _resolve_credentials_path())"
```

**Resultado esperado:** Caminho para arquivo JSON de credenciais do Google

---

## 3. Meta CAPI (Conversions API)

### 2.1 Verificar Configuracao

```powershell
cd "C:\Gestor de Pedidos Plante uma flor\backend"
python scripts/meta/verificar_config_meta.py
```

**Resultado esperado:**
```
[OK] META_PIXEL_ID: ***7593 (OK)
[OK] META_CAPI_ACCESS_TOKEN: EAAC...ZDZD (OK)
[OK] META_CAPI_USE_GATEWAY: Ativado (usando Gateway)
```

### 2.2 Verificar Conectividade do Gateway

```powershell
python scripts/maintenance/diagnosticar_gateway.py
```

**Resultado esperado:**
```
TESTE DE CONECTIVIDADE (GATEWAY):
- AUTOCONFIG: https://gestaopedidos.planteumaflor.online/capig/autoconfig
  Resultado: {'ok': True, 'status_code': 200, ...}
```

### 3.1 Verificar Configuracao

```powershell
python scripts/meta/verificar_outbox.py
```

**Resultado esperado:**
```
OUTBOX STATUS:
- Pending: 0
- Sent: 46
- Failed (retryable): 0
- Failed (permanent): 0
```

### 3.4 Verificar Outbox com Falhas

```powershell
python scripts/meta/verificar_outbox_failed.py
```

**Resultado esperado:** Lista vazia ou detalhes dos erros

### 3.5 Executar Envio Manual

```powershell
python scripts/meta/send_daily_purchases_to_meta.py
```

**Resultado esperado:**
```
[META_CAPI] Sucesso: X eventos recebidos (fbtrace_id: AWh11...)
[SUCCESS] Processamento concluido
```

---

## 4. Verificacao Completa (Checklist)

### 4.1 Script de Verificacao Rapida

```powershell
cd "C:\Gestor de Pedidos Plante uma flor\backend"

Write-Host "=== VERIFICACAO DE AUTOMACOES ===" -ForegroundColor Cyan

# Backup
Write-Host "`n[BACKUP]" -ForegroundColor Yellow
$lastBackup = Get-ChildItem "instance\backups\*.zip" -ErrorAction SilentlyContinue | 
    Sort-Object LastWriteTime -Descending | 
    Select-Object -First 1
if ($lastBackup) {
    $age = (Get-Date) - $lastBackup.LastWriteTime
    Write-Host "  Ultimo backup: $($lastBackup.Name)" -ForegroundColor Green
    Write-Host "  Idade: $([math]::Round($age.TotalHours, 1)) horas"
    if ($age.TotalHours -gt 24) {
        Write-Host "  AVISO: Backup com mais de 24h!" -ForegroundColor Red
    }
} else {
    Write-Host "  ERRO: Nenhum backup encontrado!" -ForegroundColor Red
}

# Verificar tarefa agendada
$task = Get-ScheduledTask -TaskName "GestorPedidos_BackupHorario" -ErrorAction SilentlyContinue
if ($task) {
    $info = Get-ScheduledTaskInfo -TaskName "GestorPedidos_BackupHorario"
    Write-Host "  Tarefa agendada: $($task.State)" -ForegroundColor Green
    Write-Host "  Ultima execucao: $($info.LastRunTime)"
    if ($info.LastTaskResult -ne 0 -and $info.LastRunTime) {
        Write-Host "  ERRO: Ultima execucao falhou (codigo: $($info.LastTaskResult))" -ForegroundColor Red
    }
} else {
    Write-Host "  AVISO: Tarefa agendada nao encontrada!" -ForegroundColor Yellow
}

# Exportacao Vendas
Write-Host "`n[EXPORTACAO VENDAS]" -ForegroundColor Yellow
$exportTask = Get-ScheduledTask -TaskName "GestorPedidos_ExportarVendas" -ErrorAction SilentlyContinue
if ($exportTask) {
    $exportInfo = Get-ScheduledTaskInfo -TaskName "GestorPedidos_ExportarVendas"
    Write-Host "  Tarefa agendada: $($exportTask.State)" -ForegroundColor Green
    Write-Host "  Ultima execucao: $($exportInfo.LastRunTime)"
    if ($exportInfo.LastTaskResult -ne 0 -and $exportInfo.LastRunTime) {
        Write-Host "  ERRO: Ultima execucao falhou (codigo: $($exportInfo.LastTaskResult))" -ForegroundColor Red
        if ($exportInfo.LastTaskResult -eq 2) {
            Write-Host "  DICA: Reinstalar tarefa (WorkingDirectory vazio ou Python stub)" -ForegroundColor Yellow
        }
    }
} else {
    Write-Host "  AVISO: Tarefa agendada nao encontrada!" -ForegroundColor Yellow
}

# Meta CAPI
Write-Host "`n[META CAPI]" -ForegroundColor Yellow
python -c "
from app import create_app
from app.repositories.meta_capi_outbox_repository import MetaCapiOutboxRepository
from app.models.meta_capi_outbox import MetaCapiOutbox

app = create_app()
with app.app_context():
    pending = MetaCapiOutbox.query.filter_by(status='pending').count()
    sent = MetaCapiOutbox.query.filter_by(status='sent').count()
    failed = MetaCapiOutbox.query.filter_by(status='failed').count()
    print(f'  Pending: {pending}')
    print(f'  Sent: {sent}')
    print(f'  Failed: {failed}')
    if pending > 10:
        print('  AVISO: Muitos eventos pendentes!')
    if failed > 0:
        print('  AVISO: Existem eventos com falha!')
"

Write-Host "`n=== FIM ===" -ForegroundColor Cyan
```

### 4.2 Checklist Manual

- [ ] Backup mais recente tem menos de 24 horas
- [ ] Tarefa agendada `GestorPedidos_BackupHorario` existe e esta ativa
- [ ] Tarefa agendada tem `LastTaskResult: 0` (sucesso)
- [ ] Tarefa `GestorPedidos_ExportarVendas` existe e esta ativa
- [ ] Exportacao tem `LastTaskResult: 0` (sucesso)
- [ ] WorkingDirectory da exportacao esta configurado corretamente
- [ ] Configuracao Meta CAPI esta correta (.env)
- [ ] Gateway responde em `/capig/autoconfig`
- [ ] Nenhum evento pendente ha mais de 1 hora
- [ ] Nenhum evento failed com tipo `permanent`
- [ ] Events Manager mostra eventos recentes

---

## 5. Resolucao de Problemas

### 5.1 Backup Nao Executa

**Sintoma:** Nenhum backup criado nas ultimas 24h

**Verificar:**
1. Tarefa agendada existe? `Get-ScheduledTask -TaskName "GestorPedidos_BackupHorario"`
2. Verificar ultima execucao e resultado:
```powershell
Get-ScheduledTaskInfo -TaskName "GestorPedidos_BackupHorario" | Format-List
```
   - `LastTaskResult: 0` = Sucesso
   - `LastTaskResult: 2147942667` = Erro de configuracao (remover e reinstalar)
3. Verificar acoes e triggers:
```powershell
$task = Get-ScheduledTask -TaskName "GestorPedidos_BackupHorario"
$task.Actions | Format-List
$task.Triggers | Format-List
```
   - Deve executar: `run_scheduled_backup.py` (nao `backup.py`)
   - Deve ter triggers de hora em hora (Seg-Sex 07-18h, Sab 07-14h)
4. Executar manual e ver erro: `python scripts/backup/run_scheduled_backup.py`

**Solucao comum - "Nao e possivel acessar o arquivo pelo sistema":**

Este erro ocorre quando o Python usado e o "stub" da Microsoft Store (que nao funciona para SYSTEM).

**Solucao:**
```powershell
# Remover tarefa antiga (como Administrador)
Unregister-ScheduledTask -TaskName "GestorPedidos_BackupDiario1" -Confirm:$false -ErrorAction SilentlyContinue
Unregister-ScheduledTask -TaskName "GestorPedidos_BackupHorario" -Confirm:$false -ErrorAction SilentlyContinue

# Instalar tarefa correta (como Administrador)
# O script agora procura Python real (nao stub da Store)
cd "C:\Gestor de Pedidos Plante uma flor\backend\scripts\backup"
powershell -ExecutionPolicy Bypass -File install_backup_task.ps1
```

**O script atualizado procura Python nesta ordem:**
1. Venv local (`backend\venv\Scripts\python.exe`) - MELHOR OPCAO
2. Python Launcher (`py.exe`) - funciona como SYSTEM
3. Python no registro do Windows (nao stub da Store)
4. Python em Program Files ou outros locais comuns

**Se ainda der erro:**
```powershell
# Opcao 1: Criar venv local
cd "C:\Gestor de Pedidos Plante uma flor\backend"
python -m venv venv
.\venv\Scripts\Activate.ps1
pip install -r requirements.txt

# Depois reinstalar tarefa
cd scripts\backup
powershell -ExecutionPolicy Bypass -File install_backup_task.ps1
```

### 5.2 Exportacao de Vendas Nao Executa

**Sintoma:** LastTaskResult = 2 (ERROR_FILE_NOT_FOUND)

**Verificar:**
1. Tarefa agendada existe? `Get-ScheduledTask -TaskName "GestorPedidos_ExportarVendas"`
2. Verificar ultima execucao e resultado:
```powershell
Get-ScheduledTaskInfo -TaskName "GestorPedidos_ExportarVendas" | Format-List
```
   - `LastTaskResult: 0` = Sucesso
   - `LastTaskResult: 2` = Erro de configuracao (Python stub ou WorkingDirectory vazio)
3. Verificar acoes:
```powershell
$task = Get-ScheduledTask -TaskName "GestorPedidos_ExportarVendas"
$task.Actions | Format-List
```
   - Deve ter `WorkingDirectory` configurado como diretorio `backend`
   - Execute deve ser Python real (nao stub da Store)
4. Testar manual:
```powershell
cd "C:\Gestor de Pedidos Plante uma flor\backend"
python scripts/export/exportar_vendas_sheets.py
```

**Solucao - "Erro 0x2" ou "Nao e possivel acessar o arquivo pelo sistema":**

Este erro ocorre quando:
- Python usado e o "stub" da Microsoft Store (nao funciona para SYSTEM)
- WorkingDirectory esta vazio (imports do `app` falham)

**Solucao:**
```powershell
# Remover tarefa antiga (como Administrador)
Unregister-ScheduledTask -TaskName "GestorPedidos_ExportarVendas" -Confirm:$false -ErrorAction SilentlyContinue

# Instalar tarefa correta (como Administrador)
cd "C:\Gestor de Pedidos Plante uma flor\backend\scripts\export"
powershell -ExecutionPolicy Bypass -File install_export_task.ps1
```

O script procura Python real e configura WorkingDirectory corretamente.

**Erros comuns:**
- `ModuleNotFoundError: No module named 'app'`: WorkingDirectory nao esta configurado
- `FileNotFoundError: Credenciais do Google`: Verificar arquivo de credenciais em `backend/user/config/`

### 5.3 Meta CAPI Nao Envia

**Sintoma:** Eventos pendentes acumulando

**Verificar:**
1. Credenciais configuradas? `python scripts/meta/verificar_config_meta.py`
2. Gateway acessivel? `python scripts/maintenance/diagnosticar_gateway.py`
3. Erro especifico? `python scripts/meta/verificar_outbox_failed.py`

**Erros comuns:**
- `Invalid parameter (2804016)`: Campos invalidos no payload
- `Timestamp no futuro (2804004)`: event_time incorreto (corrigido automaticamente)
- `401 Unauthorized`: Token expirado - gerar novo no Business Manager

### 5.4 Recriar Outboxes Apos Correcao

Se houve correcao no codigo de normalizacao:
```powershell
python scripts/meta/recriar_outboxes.py
python scripts/meta/send_daily_purchases_to_meta.py
```

---

## 6. Testes Automatizados

### 6.1 Executar Suite de Testes

```powershell
cd "C:\Gestor de Pedidos Plante uma flor\backend"

# Testes unitarios (rapidos)
pytest tests/test_meta_capi.py tests/test_backup_automation.py -v

# Suite completa
pytest tests/ -v -m "not integration and not slow"
```

**Resultado esperado:** `150 passed`

### 6.2 Testes Especificos

```powershell
# Apenas normalizacao Meta CAPI
pytest tests/test_meta_capi.py::TestMetaCapiServiceNormalization -v

# Apenas janela de backup
pytest tests/test_backup_automation.py::TestBackupWindowSchedule -v

# Apenas outbox repository
pytest tests/test_meta_capi.py::TestMetaCapiOutboxRepository -v
```

---

## 7. Monitoramento Continuo

### 7.1 Log de Backup

```powershell
Get-Content "instance\logs\scheduled_backup.log" -Tail 20
```

### 7.2 Log do Servidor (se rodando)

```powershell
Get-Content "instance\logs\app.log" -Tail 50 | Select-String "META_CAPI|BACKUP"
```

### 7.3 Alertas Recomendados

Configure alertas para:
1. Nenhum backup nas ultimas 24h
2. Mais de 10 eventos pendentes por mais de 1h
3. Qualquer evento com status `failed` e `error_type: permanent`
