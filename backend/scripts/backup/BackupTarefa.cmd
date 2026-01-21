@echo off
setlocal

set ROOT="C:\Gestor de Pedidos Plante uma flor\backend"
set PY="C:\Users\caioc\AppData\Local\Microsoft\WindowsApps\python.exe"

cd /d "%ROOT%"
"%PY%" "scripts\backup\run_scheduled_backup.py"

exit /b %errorlevel%
