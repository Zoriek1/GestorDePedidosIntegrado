# Script PowerShell para instalar tarefa de envio diário para Meta CAPI no Windows Task Scheduler

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
$taskName = "GestorPedidos_MetaCAPI_Daily"

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
$scriptPath = "$scriptDir\send_daily_purchases_to_meta.py"

# Verificar se script existe
if (-not (Test-Path $scriptPath)) {
    Write-Host "[ERRO] Script não encontrado: $scriptPath" -ForegroundColor Red
    pause
    exit 1
}

Write-Host "===========================================" -ForegroundColor Cyan
Write-Host "  INSTALAR TAREFA META CAPI DIÁRIA" -ForegroundColor Cyan
Write-Host "===========================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "Tarefa: $taskName" -ForegroundColor Yellow
Write-Host "Script: $scriptPath" -ForegroundColor Yellow
Write-Host "Python: $pythonPath" -ForegroundColor Yellow
Write-Host ""

# Verificar se tarefa já existe
$existingTask = Get-ScheduledTask -TaskName $taskName -ErrorAction SilentlyContinue
if ($existingTask) {
    Write-Host "[AVISO] Tarefa já existe. Deseja substituir? (S/N)" -ForegroundColor Yellow
    $response = Read-Host
    if ($response -ne "S" -and $response -ne "s") {
        Write-Host "[CANCELADO] Operação cancelada pelo usuário" -ForegroundColor Yellow
        pause
        exit 0
    }
    Write-Host "[REMOVENDO] Removendo tarefa existente..." -ForegroundColor Yellow
    Unregister-ScheduledTask -TaskName $taskName -Confirm:$false
}

# Criar diretório de logs se não existir
$logDir = "$backendDir\instance\logs"
if (-not (Test-Path $logDir)) {
    New-Item -ItemType Directory -Path $logDir -Force | Out-Null
}

# Horário de execução (padrão: 23:00)
Write-Host "Horário de execução (padrão: 23:00):" -ForegroundColor Cyan
$hourInput = Read-Host "Hora (0-23)"
$minuteInput = Read-Host "Minuto (0-59)"

$hour = if ($hourInput) { [int]$hourInput } else { 23 }
$minute = if ($minuteInput) { [int]$minuteInput } else { 0 }

if ($hour -lt 0 -or $hour -gt 23) {
    Write-Host "[ERRO] Hora inválida (deve ser 0-23)" -ForegroundColor Red
    pause
    exit 1
}
if ($minute -lt 0 -or $minute -gt 59) {
    Write-Host "[ERRO] Minuto inválido (deve ser 0-59)" -ForegroundColor Red
    pause
    exit 1
}

# Criar ação (executar script Python)
$action = New-ScheduledTaskAction -Execute $pythonPath -Argument "`"$scriptPath`"" -WorkingDirectory $backendDir

# Criar trigger (diário às 23:00)
$trigger = New-ScheduledTaskTrigger -Daily -At "$($hour.ToString('00')):$($minute.ToString('00'))"

# Configurações da tarefa
$settings = New-ScheduledTaskSettingsSet `
    -AllowStartIfOnBatteries `
    -DontStopIfGoingOnBatteries `
    -StartWhenAvailable `
    -RunOnlyIfNetworkAvailable `
    -ExecutionTimeLimit (New-TimeSpan -Hours 1)

# Criar principal (executar como usuário atual)
$principal = New-ScheduledTaskPrincipal -UserId "$env:USERDOMAIN\$env:USERNAME" -LogonType Interactive -RunLevel Limited

# Registrar tarefa
try {
    Register-ScheduledTask `
        -TaskName $taskName `
        -Action $action `
        -Trigger $trigger `
        -Settings $settings `
        -Principal $principal `
        -Description "Envia compras diárias para Meta Conversions API" `
        -Force

    Write-Host ""
    Write-Host "[SUCCESS] Tarefa instalada com sucesso!" -ForegroundColor Green
    Write-Host ""
    Write-Host "Detalhes:" -ForegroundColor Cyan
    Write-Host "  Nome: $taskName" -ForegroundColor White
    Write-Host "  Horário: $($hour.ToString('00')):$($minute.ToString('00')) (diário)" -ForegroundColor White
    Write-Host "  Script: $scriptPath" -ForegroundColor White
    Write-Host ""
    Write-Host "Para verificar a tarefa:" -ForegroundColor Yellow
    Write-Host "  Get-ScheduledTask -TaskName '$taskName'" -ForegroundColor Gray
    Write-Host ""
    Write-Host "Para remover a tarefa:" -ForegroundColor Yellow
    Write-Host "  Unregister-ScheduledTask -TaskName '$taskName' -Confirm:`$false" -ForegroundColor Gray
    Write-Host ""

} catch {
    Write-Host "[ERRO] Falha ao instalar tarefa: $_" -ForegroundColor Red
    pause
    exit 1
}

pause
