@echo off
setlocal

REM Executa a migracao de tabelas Nuvemshop
set SCRIPT_DIR=%~dp0
set BACKEND_DIR=%SCRIPT_DIR%..\..

cd /d "%BACKEND_DIR%"
python "scripts\migrations\create_nuvemshop_tables.py"

endlocal
