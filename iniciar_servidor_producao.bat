@echo off
setlocal enabledelayedexpansion

echo ============================================================
echo PLANTE UMA FLOR - Servidor de Producao (Waitress)
echo ============================================================
echo.

REM Verificar se Waitress está instalado
python -c "import waitress" 2>nul
if errorlevel 1 (
    echo [ERRO] Waitress nao esta instalado!
    echo.
    echo Instalando Waitress...
    pip install waitress
    if errorlevel 1 (
        echo [ERRO] Falha ao instalar Waitress!
        pause
        exit /b 1
    )
    echo [OK] Waitress importado com sucesso!
    echo.
)

REM Verificar se a porta já está em uso
netstat -an | findstr ":5000" | findstr "LISTENING" >nul
if not errorlevel 1 (
    echo [AVISO] A porta 5000 ja esta em uso!
    echo    Servidor pode ja estar rodando.
    echo    Para parar: Execute parar_servidor.bat
    echo.
    set /p resposta="Deseja tentar iniciar mesmo assim? (s/n): "
    if /i not "!resposta!"=="s" (
        echo [INFO] Inicializacao cancelada.
        pause
        exit /b 0
    )
    echo.
)

REM Navegar para o diretório backend
cd /d "%~dp0backend"

REM Verificar se arquivo wsgi.py existe
if not exist "wsgi.py" (
    echo [ERRO] Arquivo wsgi.py nao encontrado!
    pause
    exit /b 1
)

REM Iniciar servidor com Waitress

python wsgi.py

if errorlevel 1 (
    echo.
    echo [ERRO] Erro ao iniciar servidor!
    pause
    exit /b 1
)

endlocal
