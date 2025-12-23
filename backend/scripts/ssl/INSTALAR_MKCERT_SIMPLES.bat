@echo off
:: ===================================================
:: PLANTE UMA FLOR - Instalador Simplificado do mkcert
:: Instala direto na pasta do projeto (não requer admin)
:: ===================================================

title Instalar mkcert (Simples)

echo.
echo ============================================
echo    INSTALADOR SIMPLIFICADO DO MKCERT
echo    Plante Uma Flor - HTTPS Local
echo ============================================
echo.

:: Verificar se já está instalado
where mkcert >nul 2>&1
if %errorlevel% equ 0 (
    echo [OK] mkcert ja esta instalado!
    echo.
    mkcert -version
    echo.
    pause
    exit /b 0
)

:: Verificar se já existe na pasta local
cd /d "%~dp0"
if exist "mkcert.exe" (
    echo [OK] mkcert.exe ja existe nesta pasta!
    echo.
    echo Testando...
    .\mkcert.exe -version
    echo.
    echo Para usar, execute: .\mkcert.exe [comando]
    echo Ou execute: GERAR_CERTIFICADOS_LOCAL.bat
    echo.
    pause
    exit /b 0
)

echo [INFO] Baixando mkcert v1.4.4 para esta pasta...
echo (Nao requer permissoes de administrador)
echo.

:: URL do mkcert para Windows
set MKCERT_VERSION=v1.4.4
set MKCERT_URL=https://github.com/FiloSottile/mkcert/releases/download/%MKCERT_VERSION%/mkcert-%MKCERT_VERSION%-windows-amd64.exe

echo Baixando de: %MKCERT_URL%
echo.

:: Baixar usando PowerShell
powershell -Command "& {[Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12; Invoke-WebRequest -Uri '%MKCERT_URL%' -OutFile 'mkcert.exe'}"

if not exist "mkcert.exe" (
    echo.
    echo [ERRO] Falha ao baixar mkcert!
    echo.
    echo Verifique sua conexao com a internet.
    echo Ou baixe manualmente:
    echo.
    echo 1. Acesse: https://github.com/FiloSottile/mkcert/releases
    echo 2. Baixe: mkcert-v1.4.4-windows-amd64.exe
    echo 3. Salve como: mkcert.exe
    echo 4. Cole nesta pasta: %~dp0
    echo.
    pause
    exit /b 1
)

echo.
echo [OK] mkcert baixado com sucesso!
echo.

:: Testar
echo Testando...
.\mkcert.exe -version

if %errorlevel% neq 0 (
    echo.
    echo [ERRO] mkcert nao esta funcionando!
    echo.
    pause
    exit /b 1
)

echo.
echo ============================================
echo   INSTALACAO CONCLUIDA!
echo ============================================
echo.
echo mkcert instalado em: %~dp0mkcert.exe
echo.
echo Proximos passos:
echo   Execute: GERAR_CERTIFICADOS_LOCAL.bat
echo.
echo ============================================
echo.
pause


