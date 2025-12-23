@echo off
:: ===================================================
:: PLANTE UMA FLOR - Instalador do mkcert
:: Script para baixar e instalar mkcert no Windows
:: ===================================================

title Instalar mkcert

echo.
echo ============================================
echo    INSTALADOR DO MKCERT
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
    echo Pressione qualquer tecla para continuar...
    pause >nul
    exit /b 0
)

echo [INFO] mkcert nao encontrado. Instalando...
echo.

:: Criar diretório temporário
set TEMP_DIR=%TEMP%\mkcert_install
if not exist "%TEMP_DIR%" mkdir "%TEMP_DIR%"

:: URL do mkcert para Windows
set MKCERT_VERSION=v1.4.4
set MKCERT_URL=https://github.com/FiloSottile/mkcert/releases/download/%MKCERT_VERSION%/mkcert-%MKCERT_VERSION%-windows-amd64.exe

echo [1/3] Baixando mkcert %MKCERT_VERSION%...
echo URL: %MKCERT_URL%
echo.

:: Baixar usando PowerShell
powershell -Command "& {[Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12; Invoke-WebRequest -Uri '%MKCERT_URL%' -OutFile '%TEMP_DIR%\mkcert.exe'}"

if not exist "%TEMP_DIR%\mkcert.exe" (
    echo.
    echo [ERRO] Falha ao baixar mkcert!
    echo.
    echo OPCAO MANUAL:
    echo 1. Acesse: https://github.com/FiloSottile/mkcert/releases
    echo 2. Baixe: mkcert-v1.4.4-windows-amd64.exe
    echo 3. Renomeie para: mkcert.exe
    echo 4. Mova para: C:\Windows\System32\
    echo.
    pause
    exit /b 1
)

echo [2/3] Copiando para C:\Windows\System32\...
echo.

:: Copiar para pasta do sistema (requer admin)
copy "%TEMP_DIR%\mkcert.exe" "C:\Windows\System32\mkcert.exe" >nul 2>&1

if %errorlevel% neq 0 (
    echo [AVISO] Nao foi possivel copiar para System32 (requer admin).
    echo Instalando localmente...
    echo.
    
    :: Criar pasta local
    set LOCAL_BIN=%USERPROFILE%\bin
    if not exist "%LOCAL_BIN%" mkdir "%LOCAL_BIN%"
    
    copy "%TEMP_DIR%\mkcert.exe" "%LOCAL_BIN%\mkcert.exe"
    
    if %errorlevel% neq 0 (
        echo [ERRO] Falha ao copiar mkcert!
        echo.
        echo SOLUCAO ALTERNATIVA - Execute como ADMINISTRADOR:
        echo 1. Clique com botao direito neste arquivo
        echo 2. Escolha "Executar como administrador"
        echo.
        pause
        exit /b 1
    )
    
    :: Adicionar ao PATH
    echo [INFO] Adicionando ao PATH do usuario...
    powershell -Command "[Environment]::SetEnvironmentVariable('Path', [Environment]::GetEnvironmentVariable('Path', 'User') + ';%LOCAL_BIN%', 'User')"
    
    echo.
    echo [OK] mkcert instalado em: %LOCAL_BIN%
    echo.
    echo IMPORTANTE: Feche e abra o CMD/PowerShell novamente!
) else (
    echo [OK] mkcert instalado em System32 com sucesso!
)

echo.
echo [3/3] Limpando arquivos temporarios...
del "%TEMP_DIR%\mkcert.exe" >nul 2>&1

echo.
echo ============================================
echo   INSTALACAO CONCLUIDA!
echo ============================================
echo.
echo Proximos passos:
echo   1. Feche este terminal
echo   2. Abra um NOVO terminal
echo   3. Execute: GERAR_CERTIFICADOS.bat
echo.
echo ============================================
echo.
pause

