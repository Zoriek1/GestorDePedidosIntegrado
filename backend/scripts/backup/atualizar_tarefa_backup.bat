@echo off
:: Atualiza a tarefa existente no Windows Task Scheduler para usar o novo sistema de backup encriptado

set TAREFA=GestorPedidos_BackupDiario1
set HORA=20:00

:: Caminho do backend
set SCRIPT_DIR=%~dp0
pushd "%SCRIPT_DIR%"
cd ..
cd ..

set BACKEND_DIR=%CD%

:: Preferir venv se existir
set PY_CMD=python
if exist "%BACKEND_DIR%\venv\Scripts\python.exe" (
    set PY_CMD="%BACKEND_DIR%\venv\Scripts\python.exe"
)

:: Criar comando a executar (usa backup.py que agora cria backup encriptado no Google Drive Desktop)
set RUN_CMD=cmd /c "cd /d \"%BACKEND_DIR%\scripts\backup\" && %PY_CMD% backup.py --no-compress"

echo.
echo ============================================
echo   ATUALIZAR TAREFA DE BACKUP
echo ============================================
echo.
echo Tarefa: %TAREFA%
echo Horario: %HORA%
echo.
echo IMPORTANTE: Execute este script como Administrador!
echo.
pause

:: Deletar tarefa existente se houver
echo [1/2] Removendo tarefa antiga (se existir)...
schtasks /Delete /F /TN "%TAREFA%" >nul 2>&1

:: Criar nova tarefa
echo [2/2] Criando nova tarefa com backup encriptado...
schtasks /Create /F /SC DAILY /TN "%TAREFA%" /TR "%RUN_CMD%" /ST %HORA%

if %errorlevel% equ 0 (
    echo.
    echo [OK] Tarefa atualizada com sucesso!
    echo.
    echo A tarefa agora:
    echo   - Cria backup nao encriptado localmente
    echo   - Encripta e salva no Google Drive Desktop
    echo   - Roda diariamente as %HORA%
    echo.
) else (
    echo.
    echo [ERRO] Falha ao atualizar tarefa.
    echo Tente executar como administrador.
    echo.
)

popd
pause

