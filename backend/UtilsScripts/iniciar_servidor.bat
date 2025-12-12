@echo off
:: ===================================================
:: PLANTE UMA FLOR - Iniciar Servidor (Modo Simples)
:: Script simplificado para inicialização rápida
:: ===================================================

title Plante Uma Flor - Iniciar Servidor

cd /d "%~dp0"

echo.
echo ============================================
echo    PLANTE UMA FLOR - SERVIDOR
echo ============================================
echo.

:: Verificar se Python está disponível
where python >nul 2>&1
if %errorlevel% neq 0 (
    echo [ERRO] Python nao encontrado!
    echo.
    echo Instale Python 3.8+ em: https://www.python.org
    echo.
    pause
    exit /b 1
)

:: Verificar se certificados existem
if not exist "ssl\cert.pem" (
    echo [INFO] Certificados SSL nao encontrados.
    echo.
    choice /C SN /M "Deseja gerar certificados agora (S/N)? "
    if errorlevel 2 goto :iniciar_http
    if errorlevel 1 goto :gerar_certs
)

goto :iniciar_https

:gerar_certs
echo.
echo [INFO] Gerando certificados SSL...
call CONFIGURAR_SERVIDOR.bat
if %errorlevel% neq 0 (
    echo.
    echo [ERRO] Falha ao gerar certificados.
    echo [INFO] Iniciando em modo HTTP...
    timeout /t 3 >nul
    goto :iniciar_http
)
goto :iniciar_https

:iniciar_https
echo.
echo [INFO] Iniciando servidor HTTPS...
echo [INFO] Modo estavel ativado (sem auto-reload)
echo.
echo ============================================
echo   Servidor HTTPS - Porta 5000
echo ============================================
echo   Local:    https://localhost:5000
echo   Hostname: https://Gestor-pedidos.local:5000
echo   Rede:     https://[SEU-IP]:5000
echo.
echo   Para parar: Pressione Ctrl+C
echo ============================================
echo.

python main.py --https --no-reload
goto :fim

:iniciar_http
echo.
echo [INFO] Iniciando servidor HTTP...
echo [INFO] Modo estavel ativado (sem auto-reload)
echo.
echo ============================================
echo   Servidor HTTP - Porta 5000
echo ============================================
echo   Local:    http://localhost:5000
echo   Rede:     http://[SEU-IP]:5000
echo.
echo   AVISO: PWA so instala em HTTPS!
echo   Para HTTPS: Execute CONFIGURAR_SERVIDOR.bat
echo.
echo   Para parar: Pressione Ctrl+C
echo ============================================
echo.

python main.py --no-reload
goto :fim

:fim
echo.
echo [INFO] Servidor encerrado.
pause

