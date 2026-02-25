# Script PowerShell para instalar tarefa de teste de restauração no Windows Task Scheduler
# P0.4 - Teste Recorrente de Restauração

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
$taskName = "GestorPedidos_RestoreTest"

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
$scriptPath = "$scriptDir\restore_smoke_test.py"

# Verificar se script existe
if (-not (Test-Path $scriptPath)) {
    Write-Host "[ERRO] Script não encontrado: $scriptPath" -ForegroundColor Red
    pause
    exit 1
}

Write-Host "===========================================" -ForegroundColor Cyan
Write-Host "  INSTALAR TAREFA DE TESTE DE RESTAURAÇÃO" -ForegroundColor Cyan
Write-Host "===========================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "Tarefa: $taskName" -ForegroundColor Yellow
Write-Host "Script: $scriptPath" -ForegroundColor Yellow
Write-Host "Python: $pythonPath" -ForegroundColor Yellow
Write-Host ""
Write-Host "Horário de execução:" -ForegroundColor Yellow
Write-Host "  - Diariamente às 06:30 (antes da janela de backup)" -ForegroundColor White
Write-Host ""

# Remover tarefa existente se houver
$existingTask = Get-ScheduledTask -TaskName $taskName -ErrorAction SilentlyContinue
if ($existingTask) {
    Write-Host "[INFO] Removendo tarefa existente..." -ForegroundColor Yellow
    Unregister-ScheduledTask -TaskName $taskName -Confirm:$false -ErrorAction SilentlyContinue
}

# Criar ação (executar Python script)
$action = New-ScheduledTaskAction -Execute $pythonPath -Argument "`"$scriptPath`"" -WorkingDirectory $backendDir

# Criar trigger: diariamente às 06:30
$trigger = New-ScheduledTaskTrigger -Daily -At "06:30"

# Configurações da tarefa
$settings = New-ScheduledTaskSettingsSet -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries -StartWhenAvailable -RunOnlyIfNetworkAvailable:$false
# Não definir ExecutionTimeLimit (deixar padrão) para evitar problemas de formato
# O script Python tem timeout próprio e não deve demorar mais que alguns minutos
$settings.RestartCount = 0  # Não tentar reiniciar se falhar

# Principal (executar mesmo sem usuário logado)
$principal = New-ScheduledTaskPrincipal -UserId "SYSTEM" -LogonType ServiceAccount -RunLevel Highest

# Registrar tarefa
try {
    Register-ScheduledTask -TaskName $taskName -Action $action -Trigger $trigger -Settings $settings -Principal $principal -Description "Teste recorrente de restauração de backups (P0.4) - Executa diariamente às 06:30" -Force
    
    Write-Host ""
    Write-Host "[OK] Tarefa instalada com sucesso!" -ForegroundColor Green
    Write-Host ""
    Write-Host "Verificações:" -ForegroundColor Cyan
    Write-Host "  1. Abra o Agendador de Tarefas do Windows" -ForegroundColor White
    Write-Host "  2. Procure por: $taskName" -ForegroundColor White
    Write-Host "  3. Clique com botão direito → Executar (para testar)" -ForegroundColor White
    Write-Host ""
    Write-Host "Logs:" -ForegroundColor Cyan
    Write-Host "  - $backendDir\instance\logs\restore_test.log" -ForegroundColor White
    Write-Host ""
    
} catch {
    Write-Host ""
    Write-Host "[ERRO] Falha ao instalar tarefa: $_" -ForegroundColor Red
    Write-Host ""
    pause
    exit 1
}

pause

