@echo off
:: Agenda tarefa no Windows Task Scheduler para rodar backup diário
:: Ajuste o horário conforme necessário (HH:MM no formato 24h)

set HORA=02:00
set TAREFA=BackupGDrivePlanteUmaFlor

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

:: Criar comando a executar
set RUN_CMD=cmd /c "cd /d \"%BACKEND_DIR%\\scripts\\backup\" && %PY_CMD% backup.py --no-compress"

echo Criando tarefa %TAREFA% para rodar diariamente às %HORA%...
schtasks /Create /F /SC DAILY /TN "%TAREFA%" /TR "%RUN_CMD%" /ST %HORA% >nul

if %errorlevel% equ 0 (
    echo [OK] Tarefa agendada com sucesso.
) else (
    echo [ERRO] Falha ao agendar tarefa. Tente executar como administrador.
)

popd
pause

