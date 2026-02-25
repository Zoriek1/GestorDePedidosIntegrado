@echo off
:: ====================================================
:: PARAR TUDO - Incluindo scripts VBS
:: ====================================================

:: Verificar admin
net session >nul 2>&1
if %errorlevel% neq 0 (
    echo Solicitando permissoes de administrador...
    powershell -Command "Start-Process '%~f0' -Verb RunAs"
    exit /b
)

title Parar TUDO (VBS + Python + Porta 5000)

echo.
echo ============================================
echo   PARAR TUDO - LIMPEZA COMPLETA
echo ============================================
echo.

echo [1/5] Matando processos VBScript (wscript/cscript)...
taskkill /F /IM wscript.exe 2>nul
taskkill /F /IM cscript.exe 2>nul
echo   OK

echo.
echo [2/5] Matando processos Python...
taskkill /F /IM python.exe 2>nul
taskkill /F /IM pythonw.exe 2>nul
taskkill /F /IM py.exe 2>nul
echo   OK

echo.
echo [3/5] Matando processos na porta 5000...
for /f "tokens=5" %%a in ('netstat -ano ^| findstr :5000 ^| findstr LISTENING') do (
    echo   Matando PID: %%a
    taskkill /F /PID %%a 2>nul
)
echo   OK

echo.
echo [4/5] Aguardando processos terminarem...
timeout /t 3 /nobreak >nul
echo   OK

echo.
echo [5/5] Verificando resultado final...
echo.

set LIMPO=1

:: Verificar VBS
tasklist | findstr /I "wscript.exe cscript.exe" >nul 2>&1
if %errorlevel% equ 0 (
    echo   [AVISO] Ainda ha processos VBS rodando!
    set LIMPO=0
)

:: Verificar Python
tasklist | findstr /I "python.exe pythonw.exe" >nul 2>&1
if %errorlevel% equ 0 (
    echo   [AVISO] Ainda ha processos Python rodando!
    set LIMPO=0
)

:: Verificar porta 5000
netstat -ano | findstr :5000 | findstr LISTENING >nul 2>&1
if %errorlevel% equ 0 (
    echo   [AVISO] Porta 5000 ainda esta ocupada!
    echo.
    netstat -ano | findstr :5000 | findstr LISTENING
    set LIMPO=0
)

echo.
if %LIMPO% equ 1 (
    echo ============================================
    echo   SUCESSO TOTAL! Tudo limpo!
    echo ============================================
    echo.
    echo Porta 5000: LIVRE
    echo Processos Python: PARADOS
    echo Processos VBS: PARADOS
    echo.
    echo Agora voce pode gerar os certificados:
    echo   cd ssl
    echo   GERAR_CERTIFICADOS_AUTO.bat
    echo.
) else (
    echo ============================================
    echo   AVISO: Alguns processos ainda ativos
    echo ============================================
    echo.
    echo SOLUCAO:
    echo 1. Abra Gerenciador de Tarefas (Ctrl+Shift+Esc)
    echo 2. Aba "Detalhes"
    echo 3. Finalize MANUALMENTE:
    echo    - python.exe
    echo    - pythonw.exe
    echo    - wscript.exe
    echo.
    echo OU reinicie o computador.
    echo.
)

pause

