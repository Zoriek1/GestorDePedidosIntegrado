@echo off
chcp 65001 > nul
REM ============================================================
REM Remover Backup Automático - Windows Task Scheduler
REM Remove tarefa agendada de backup
REM ============================================================

echo.
echo ============================================================
echo   REMOVER BACKUP AUTOMÁTICO
echo ============================================================
echo.
echo Este script irá remover a tarefa de backup automático
echo do Agendador de Tarefas do Windows.
echo.
pause

echo.
echo [INFO] Verificando permissões...

REM Verificar se está rodando como administrador
net session >nul 2>&1
if %errorLevel% neq 0 (
    echo [ERRO] Este script precisa ser executado como Administrador!
    echo.
    echo Clique com botão direito no arquivo e escolha:
    echo "Executar como administrador"
    echo.
    pause
    exit /b 1
)

echo [OK] Permissões OK
echo.

REM Remover tarefa agendada
echo [INFO] Removendo tarefa agendada...
echo.

schtasks /Delete /TN "GestorPedidos_BackupDiario" /F

if %errorLevel% equ 0 (
    echo.
    echo ============================================================
    echo [OK] Tarefa de backup removida com sucesso!
    echo ============================================================
    echo.
    echo O backup automático foi desativado.
    echo.
    echo Para reativar:
    echo   - Execute: agendar_backup_windows.bat
    echo.
    echo Para fazer backup manual:
    echo   - Execute: python scripts/backup.py
    echo.
    echo ============================================================
) else (
    echo.
    echo [AVISO] Tarefa não encontrada ou já foi removida.
    echo.
)

echo.
pause

