@echo off
chcp 65001 > nul
REM ============================================================
REM Agendador de Backup Automático - Windows Task Scheduler
REM Cria tarefa agendada para backup diário às 03:00
REM ============================================================

echo.
echo ============================================================
echo   CONFIGURAR BACKUP AUTOMÁTICO
echo ============================================================
echo.
echo Este script irá configurar backup automático diário do
echo banco de dados usando o Agendador de Tarefas do Windows.
echo.
echo Backup será executado todos os dias às 03:00
echo.
pause

REM Obter diretório atual
set "SCRIPT_DIR=%~dp0"
set "BACKEND_DIR=%SCRIPT_DIR%.."
set "PYTHON_SCRIPT=%SCRIPT_DIR%backup.py"

REM Encontrar caminho completo do Python
for /f "delims=" %%i in ('where python') do set "PYTHON_PATH=%%i"

if not defined PYTHON_PATH (
    echo [ERRO] Python nao encontrado no PATH!
    echo.
    echo Certifique-se de que o Python esta instalado e no PATH do sistema.
    echo.
    pause
    exit /b 1
)

echo [INFO] Python encontrado: %PYTHON_PATH%
echo.

echo [INFO] Verificando permissoes...
echo.

REM Verificar se está rodando como administrador
net session >nul 2>&1
if %errorLevel% neq 0 (
    echo [ERRO] Este script precisa ser executado como Administrador!
    echo.
    echo Clique com botao direito no arquivo e escolha:
    echo "Executar como administrador"
    echo.
    pause
    exit /b 1
)

echo [OK] Permissoes OK
echo.

REM Criar tarefa agendada com diretório de trabalho correto
echo [INFO] Criando tarefa agendada...
echo.
echo Comando que sera executado:
echo   Programa: %PYTHON_PATH%
echo   Argumentos: "%PYTHON_SCRIPT%"
echo   Diretorio de trabalho: %BACKEND_DIR%
echo.

REM Criar tarefa com diretório de trabalho configurado
schtasks /Create /SC DAILY /TN "GestorPedidos_BackupDiario" /TR "\"%PYTHON_PATH%\" \"%PYTHON_SCRIPT%\"" /ST 03:00 /F /RU SYSTEM /RL HIGHEST /WD "%BACKEND_DIR%"

if %errorLevel% equ 0 (
    echo.
    echo ============================================================
    echo [OK] Backup automático configurado com sucesso!
    echo ============================================================
    echo.
    echo Configurações:
    echo   - Nome da tarefa: GestorPedidos_BackupDiario
    echo   - Frequência: Diária
    echo   - Horário: 03:00 (madrugada)
    echo   - Retenção: 30 dias
    echo.
    echo Para gerenciar:
    echo   - Abrir Agendador de Tarefas do Windows
    echo   - Procurar por: GestorPedidos_BackupDiario
    echo.
    echo Para remover:
    echo   - Execute: desagendar_backup_windows.bat
    echo.
    echo ============================================================
) else (
    echo.
    echo [ERRO] Falha ao criar tarefa agendada!
    echo.
    echo Tente criar manualmente:
    echo 1. Abra o Agendador de Tarefas
    echo 2. Criar Tarefa Básica
    echo 3. Nome: GestorPedidos_BackupDiario
    echo 4. Gatilho: Diariamente às 03:00
    echo 5. Ação: Iniciar programa
    echo    Programa: python
    echo    Argumentos: "%PYTHON_SCRIPT%"
    echo.
)

echo.
pause

