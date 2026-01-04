@echo off
setlocal enabledelayedexpansion

echo ============================================================
echo PLANTE UMA FLOR - Servidor de Producao Completo
echo ============================================================
echo.

REM Verificar se Waitress está instalado
python -c "import waitress" 2>nul
if errorlevel 1 (
    echo [INFO] Waitress nao esta instalado. Instalando...
    pip install waitress
    if errorlevel 1 (
        echo [ERRO] Falha ao instalar Waitress!
        pause
        exit /b 1
    )
    echo [OK] Waitress instalado com sucesso!
    echo.
)

REM Verificar se a porta já está em uso
netstat -an | findstr ":5000" | findstr "LISTENING" >nul
if not errorlevel 1 (
    echo [AVISO] A porta 5000 ja esta em uso!
    echo    Backend pode ja estar rodando.
    echo.
    set /p resposta="Deseja tentar iniciar mesmo assim? (s/n): "
    if /i not "!resposta!"=="s" (
        echo [INFO] Inicializacao cancelada.
        pause
        exit /b 0
    )
    echo.
)

REM Verificar se backend/wsgi.py existe
if not exist "backend\wsgi.py" (
    echo [ERRO] Arquivo backend\wsgi.py nao encontrado!
    pause
    exit /b 1
)

REM Verificar se frontend_v2 existe
if not exist "frontend_v2" (
    echo [ERRO] Diretorio frontend_v2 nao encontrado!
    pause
    exit /b 1
)

echo [1/2] Fazendo build do frontend_v2...
cd frontend_v2
echo [INFO] Usando build:fast (sem type checking para maior velocidade)
echo [INFO] Para build completo com type checking, use: npm run build
call npm run build:fast

if %errorlevel% neq 0 (
    echo [ERRO] Falha no build do frontend!
    pause
    exit /b 1
)

echo [OK] Build do frontend concluido!
echo.

echo [2/2] Iniciando backend em producao (porta 5000)...
echo [INFO] O backend serve tanto a API (/api/*) quanto o frontend (/*)
echo [INFO] Cloudflare Tunnel deve apontar apenas para localhost:5000
echo.
start "Backend - Plante Uma Flor" cmd /k "cd /d %~dp0backend && python wsgi.py"
timeout /t 2 /nobreak >nul

echo.
echo ============================================================
echo [OK] Servidor de producao iniciado com sucesso!
echo ============================================================
echo.
echo Backend + Frontend: http://localhost:5000
echo API:               http://localhost:5000/api/health
echo Frontend:           http://localhost:5000/
echo.
echo [INFO] O servidor Waitress serve tanto a API quanto o frontend
echo [INFO] Nao e mais necessario o servidor na porta 3000
echo.
echo Pressione qualquer tecla para fechar este script...
echo (O servidor continuara rodando na janela aberta)
echo ============================================================
pause >nul

endlocal
