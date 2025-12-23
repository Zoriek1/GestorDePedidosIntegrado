@echo off
:: ====================================================
:: VERIFICAR PROCESSOS VBS E PYTHON
:: ====================================================

title Verificar Processos

echo.
echo ============================================
echo   VERIFICAR PROCESSOS VBS E PYTHON
echo ============================================
echo.

echo [1/3] Processos WScript (VBS):
echo.
tasklist | findstr /I "wscript.exe" 
if %errorlevel% neq 0 (
    echo   [OK] Nenhum processo VBS rodando
)

echo.
echo [2/3] Processos Python:
echo.
tasklist | findstr /I "python"
if %errorlevel% neq 0 (
    echo   [OK] Nenhum processo Python rodando
)

echo.
echo [3/3] Porta 5000:
echo.
netstat -ano | findstr :5000 | findstr LISTENING
if %errorlevel% neq 0 (
    echo   [OK] Porta 5000 esta livre
)

echo.
echo ============================================
echo   VERIFICAR INICIALIZACAO AUTOMATICA
echo ============================================
echo.

echo Abrindo pasta de inicializacao...
echo Procure por arquivos .vbs e DELETE!
echo.
pause

explorer shell:startup

echo.
pause

