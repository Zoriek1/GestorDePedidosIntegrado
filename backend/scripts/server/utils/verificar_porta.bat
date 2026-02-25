@echo off
:: ====================================================
:: VERIFICAR PORTA 5000
:: Mostra o que está usando a porta 5000
:: ====================================================

title Verificar Porta 5000

echo.
echo ============================================
echo   VERIFICAR PORTA 5000
echo ============================================
echo.

echo Verificando processos usando a porta 5000...
echo.

netstat -ano | findstr :5000

if %errorlevel% equ 0 (
    echo.
    echo ============================================
    echo.
    echo [OCUPADO] A porta 5000 esta sendo usada!
    echo.
    echo Coluna da direita = PID (ID do Processo)
    echo.
    echo Para parar: Execute parar_servidor.bat
    echo.
    echo ============================================
) else (
    echo.
    echo ============================================
    echo   [LIVRE] A porta 5000 esta disponivel!
    echo ============================================
)

echo.
pause

