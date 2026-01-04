@echo off
setlocal

echo [backend] Iniciando Flask na porta 5000...
start "backend" cmd /c "cd backend && python main.py"

echo [frontend] Buildando frontend_v2...
cd frontend_v2
call npm run build

if %errorlevel% neq 0 (
    echo [ERRO] Falha no build do frontend!
    pause
    exit /b 1
)

echo [frontend] Servindo estatico (dist) na porta 3000...
start "frontend" cmd /c "cd frontend_v2 && npx serve -s dist -l 3000"

endlocal

