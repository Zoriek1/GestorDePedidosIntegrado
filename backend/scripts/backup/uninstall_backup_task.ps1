# Script PowerShell para remover tarefa de backup automático do Windows Task Scheduler

# Verificar se está executando como administrador
$isAdmin = ([Security.Principal.WindowsPrincipal] [Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)
if (-not $isAdmin) {
    Write-Host "[ERRO] Este script precisa ser executado como Administrador!" -ForegroundColor Red
    Write-Host "Clique com botão direito e selecione 'Executar como administrador'" -ForegroundColor Yellow
    pause
    exit 1
}

$taskName = "GestorPedidos_BackupHorario"

Write-Host "===========================================" -ForegroundColor Cyan
Write-Host "  REMOVER TAREFA DE BACKUP AUTOMÁTICO" -ForegroundColor Cyan
Write-Host "===========================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "Tarefa: $taskName" -ForegroundColor Yellow
Write-Host ""

# Verificar se tarefa existe
$existingTask = Get-ScheduledTask -TaskName $taskName -ErrorAction SilentlyContinue
if (-not $existingTask) {
    Write-Host "[INFO] Tarefa não encontrada. Nada a remover." -ForegroundColor Yellow
    pause
    exit 0
}

# Confirmar remoção
Write-Host "Tem certeza que deseja remover a tarefa '$taskName'?" -ForegroundColor Yellow
$confirm = Read-Host "Digite 'SIM' para confirmar"
if ($confirm -ne "SIM") {
    Write-Host "[INFO] Operação cancelada." -ForegroundColor Yellow
    pause
    exit 0
}

# Remover tarefa
try {
    Unregister-ScheduledTask -TaskName $taskName -Confirm:$false
    Write-Host ""
    Write-Host "[OK] Tarefa removida com sucesso!" -ForegroundColor Green
    Write-Host ""
} catch {
    Write-Host ""
    Write-Host "[ERRO] Falha ao remover tarefa: $_" -ForegroundColor Red
    Write-Host ""
    pause
    exit 1
}

pause

