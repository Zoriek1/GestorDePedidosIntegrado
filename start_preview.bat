@echo off
setlocal

echo [backend] Iniciando Flask na porta 5000...
start "backend" cmd /c "cd backend && python main.py"

echo [frontend] Servindo estatico existente (dist) na porta 3000...
cd frontend_v2
npx serve -s dist -l 3000

endlocal

