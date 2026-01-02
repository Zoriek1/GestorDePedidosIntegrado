# Script PowerShell para instalar tarefa de backup automático no Windows Task Scheduler
# P0.1 - Backups Automáticos Horários com Janelas Restritas

# Verificar se está executando como administrador
$isAdmin = ([Security.Principal.WindowsPrincipal] [Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)
if (-not $isAdmin) {
    Write-Host "[ERRO] Este script precisa ser executado como Administrador!" -ForegroundColor Red
    Write-Host "Clique com botão direito e selecione 'Executar como administrador'" -ForegroundColor Yellow
    pause
    exit 1
}

# Obter diretório do script
$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$backendDir = Split-Path -Parent (Split-Path -Parent $scriptDir)
$projectRoot = Split-Path -Parent $backendDir

# Nome da tarefa
$taskName = "GestorPedidos_BackupHorario"

# Caminho do Python (preferir venv se existir)
$pythonPath = "python"
if (Test-Path "$backendDir\venv\Scripts\python.exe") {
    $pythonPath = "$backendDir\venv\Scripts\python.exe"
} else {
    # Tentar encontrar Python no PATH
    $pythonInPath = Get-Command python -ErrorAction SilentlyContinue
    if ($pythonInPath) {
        $pythonPath = $pythonInPath.Source
    } else {
        Write-Host "[ERRO] Python não encontrado no PATH!" -ForegroundColor Red
        Write-Host "Instale Python ou ative o ambiente virtual (venv)" -ForegroundColor Yellow
        pause
        exit 1
    }
}

# Caminho do script Python
$scriptPath = "$scriptDir\run_scheduled_backup.py"

# Verificar se script existe
if (-not (Test-Path $scriptPath)) {
    Write-Host "[ERRO] Script não encontrado: $scriptPath" -ForegroundColor Red
    pause
    exit 1
}

Write-Host "===========================================" -ForegroundColor Cyan
Write-Host "  INSTALAR TAREFA DE BACKUP AUTOMÁTICO" -ForegroundColor Cyan
Write-Host "===========================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "Tarefa: $taskName" -ForegroundColor Yellow
Write-Host "Script: $scriptPath" -ForegroundColor Yellow
Write-Host "Python: $pythonPath" -ForegroundColor Yellow
Write-Host ""
Write-Host "Janelas de execução:" -ForegroundColor Yellow
Write-Host "  - Segunda a Sexta: 07:00 até 18:00 (a cada 1 hora)" -ForegroundColor White
Write-Host "  - Sábado: 07:00 até 14:00 (a cada 1 hora)" -ForegroundColor White
Write-Host "  - Domingo: não executa" -ForegroundColor White
Write-Host ""

# Remover tarefa existente se houver
$existingTask = Get-ScheduledTask -TaskName $taskName -ErrorAction SilentlyContinue
if ($existingTask) {
    Write-Host "[INFO] Removendo tarefa existente..." -ForegroundColor Yellow
    Unregister-ScheduledTask -TaskName $taskName -Confirm:$false -ErrorAction SilentlyContinue
}

# Criar ação (executar Python script)
$action = New-ScheduledTaskAction -Execute $pythonPath -Argument "`"$scriptPath`"" -WorkingDirectory $backendDir

# Criar triggers - uma abordagem mais simples: criar triggers individuais para cada hora
# O script Python já tem lógica de janela e idempotência, então podemos criar triggers simples
$triggers = @()

# Segunda a Sexta: criar trigger para cada hora de 07:00 até 18:00
for ($hour = 7; $hour -le 18; $hour++) {
    $timeStr = "{0:D2}:00" -f $hour
    $trigger = New-ScheduledTaskTrigger -Weekly -DaysOfWeek Monday,Tuesday,Wednesday,Thursday,Friday -At $timeStr
    $triggers += $trigger
}

# Sábado: criar trigger para cada hora de 07:00 até 14:00
for ($hour = 7; $hour -le 14; $hour++) {
    $timeStr = "{0:D2}:00" -f $hour
    $trigger = New-ScheduledTaskTrigger -Weekly -DaysOfWeek Saturday -At $timeStr
    $triggers += $trigger
}

# Configurações da tarefa
$settings = New-ScheduledTaskSettingsSet -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries -StartWhenAvailable -RunOnlyIfNetworkAvailable:$false
# Não definir ExecutionTimeLimit (deixar padrão) para evitar problemas de formato
# O script Python tem timeout próprio e não deve demorar mais que alguns minutos
$settings.RestartCount = 0  # Não tentar reiniciar se falhar

# Principal (executar mesmo sem usuário logado)
$principal = New-ScheduledTaskPrincipal -UserId "SYSTEM" -LogonType ServiceAccount -RunLevel Highest

# Registrar tarefa
try {
    Register-ScheduledTask -TaskName $taskName -Action $action -Trigger $triggers -Settings $settings -Principal $principal -Description "Backup automático horário do banco de dados (P0.1) - Janelas: Seg-Sex 07:00-18:00, Sáb 07:00-14:00" -Force
    
    Write-Host ""
    Write-Host "[OK] Tarefa instalada com sucesso!" -ForegroundColor Green
    Write-Host ""
    Write-Host "Verificações:" -ForegroundColor Cyan
    Write-Host "  1. Abra o Agendador de Tarefas do Windows" -ForegroundColor White
    Write-Host "  2. Procure por: $taskName" -ForegroundColor White
    Write-Host "  3. Clique com botão direito → Executar (para testar)" -ForegroundColor White
    Write-Host ""
    Write-Host "Logs:" -ForegroundColor Cyan
    Write-Host "  - $backendDir\instance\logs\scheduled_backup.log" -ForegroundColor White
    Write-Host "  - $backendDir\instance\logs\backup_audit.log" -ForegroundColor White
    Write-Host ""
    
} catch {
    Write-Host ""
    Write-Host "[ERRO] Falha ao instalar tarefa: $_" -ForegroundColor Red
    Write-Host ""
    pause
    exit 1
}

pause

