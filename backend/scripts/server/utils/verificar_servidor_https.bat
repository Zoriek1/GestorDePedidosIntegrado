@echo off
:: ===================================================
:: PLANTE UMA FLOR - Verificar Servidor HTTPS
:: Verifica status do servidor e mostra log
:: ===================================================

title Verificar Servidor HTTPS - Plante Uma Flor

cd /d "%~dp0\.."

echo.
echo ============================================
echo   VERIFICAR SERVIDOR HTTPS
echo ============================================
echo.

:: Verificar se a porta 5000 está em uso
netstat -ano | findstr :5000 >nul 2>&1
if %errorlevel% equ 0 (
    echo [OK] Servidor esta RODANDO na porta 5000
    echo.
    
    :: Mostrar processo
    echo Processo:
    for /f "tokens=5" %%a in ('netstat -ano ^| findstr :5000') do (
        tasklist /FI "PID eq %%a" /FO TABLE
    )
) else (
    echo [!] Servidor NAO esta rodando
)

echo.
echo ============================================
echo   ULTIMAS LINHAS DO LOG
echo ============================================
echo.

if exist "servidor_https.log" (
    echo Log: backend\servidor_https.log
    echo.
    
    :: Mostrar últimas 20 linhas
    powershell -Command "Get-Content 'servidor_https.log' -Tail 20"
) else (
    echo [!] Arquivo de log nao encontrado
    echo Execute o servidor primeiro: iniciar_servidor_https_invisivel.vbs
)

echo.
echo ============================================
echo.
pause

