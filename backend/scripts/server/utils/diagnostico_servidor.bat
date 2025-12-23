@echo off
:: ===================================================
:: PLANTE UMA FLOR - Diagnóstico do Servidor
:: Verifica status e possíveis problemas
:: ===================================================

title Plante Uma Flor - Diagnóstico

echo.
echo ============================================
echo    DIAGNOSTICO DO SERVIDOR
echo ============================================
echo.

cd /d "%~dp0\.."

echo [1/6] Verificando Python...
where python >nul 2>&1
if %errorlevel% equ 0 (
    echo [OK] Python encontrado
    python --version
) else (
    echo [ERRO] Python nao encontrado no PATH!
    goto :fim
)

echo.
echo [2/6] Verificando dependencias...
pip show Flask >nul 2>&1
if %errorlevel% equ 0 (
    echo [OK] Flask instalado
    pip show Flask | findstr "Version"
) else (
    echo [ERRO] Flask nao instalado!
    echo    Execute: pip install -r requirements.txt
    goto :fim
)

echo.
echo [3/6] Verificando certificados SSL...
if exist "config\ssl\cert.pem" (
    echo [OK] Certificado encontrado: config\ssl\cert.pem
) else (
    echo [AVISO] Certificado nao encontrado
    echo    Execute: scripts\ssl\GERAR_CERTIFICADOS.bat
)

if exist "config\ssl\key.pem" (
    echo [OK] Chave privada encontrada: config\ssl\key.pem
) else (
    echo [AVISO] Chave privada nao encontrada
    echo    Execute: scripts\ssl\GERAR_CERTIFICADOS.bat
)

echo.
echo [4/6] Verificando banco de dados...
if exist "database.db" (
    echo [OK] Banco de dados encontrado: database.db
) else (
    echo [INFO] Banco de dados sera criado na primeira execucao
)

echo.
echo [5/6] Verificando porta 5000...
netstat -ano | findstr ":5000" | findstr "LISTENING" >nul 2>&1
if %errorlevel% equ 0 (
    echo [AVISO] Porta 5000 JA ESTA EM USO!
    echo.
    echo Detalhes:
    netstat -ano | findstr ":5000" | findstr "LISTENING"
    echo.
    echo O servidor pode ja estar rodando.
    echo Para parar: Execute parar_servidor.bat
) else (
    echo [OK] Porta 5000 disponivel
)

echo.
echo [6/6] Verificando processos Python...
tasklist /FI "IMAGENAME eq python.exe" /FI "IMAGENAME eq python3.12.exe" 2>nul | findstr "python" >nul 2>&1
if %errorlevel% equ 0 (
    echo [INFO] Processos Python encontrados:
    tasklist /FI "IMAGENAME eq python.exe" 2>nul | findstr "python"
    tasklist /FI "IMAGENAME eq python3.12.exe" 2>nul | findstr "python"
) else (
    echo [OK] Nenhum processo Python em execucao
)

echo.
echo ============================================
echo    DIAGNOSTICO CONCLUIDO
echo ============================================
echo.

:fim
pause

