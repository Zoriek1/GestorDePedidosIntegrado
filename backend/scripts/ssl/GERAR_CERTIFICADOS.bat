@echo off
setlocal enabledelayedexpansion
:: ===================================================
:: PLANTE UMA FLOR - Gerador de Certificados SSL
:: Gera certificados HTTPS para rede local
:: VERSÃO MULTI-IP - Detecta TODOS os IPs
:: ===================================================

title Gerar Certificados SSL

echo.
echo ============================================
echo    GERADOR DE CERTIFICADOS SSL
echo    Plante Uma Flor - HTTPS Local
echo ============================================
echo.

:: Verificar se mkcert está instalado
where mkcert >nul 2>&1
if %errorlevel% neq 0 (
    echo [ERRO] mkcert nao encontrado!
    echo.
    echo Por favor, execute primeiro: INSTALAR_MKCERT.bat
    echo.
    pause
    exit /b 1
)

echo [OK] mkcert encontrado!
echo.
mkcert -version
echo.

:: Ler hostname do arquivo de configuração
set "HOSTNAME=Gestor-pedidos.local"
if exist "..\config_servidor.ini" (
    for /f "tokens=2 delims==" %%a in ('findstr "hostname" ..\config_servidor.ini') do (
        set "HOSTNAME=%%a"
        set "HOSTNAME=!HOSTNAME: =!"
    )
)

echo [INFO] Hostname configurado: %HOSTNAME%
echo.

:: Descobrir TODOS os IPs da máquina
echo [1/4] Detectando TODOS os IPs da maquina...
echo.

set "IP_LIST=localhost 127.0.0.1 ::1"
set "IP_COUNT=0"

for /f "tokens=2 delims=:" %%a in ('ipconfig ^| findstr /c:"IPv4"') do (
    set "CURRENT_IP=%%a"
    set "CURRENT_IP=!CURRENT_IP: =!"
    
    REM Verificar se não é loopback
    echo !CURRENT_IP! | findstr /b /c:"127." >nul
    if errorlevel 1 (
        set /a IP_COUNT+=1
        set "IP_LIST=!IP_LIST! !CURRENT_IP!"
        echo   - IP !IP_COUNT!: !CURRENT_IP!
    )
)

if %IP_COUNT% equ 0 (
    echo.
    echo [AVISO] Nenhum IP de rede encontrado!
    echo Usando apenas localhost...
    set "IP_LIST=localhost 127.0.0.1 ::1"
) else (
    echo.
    echo [OK] Encontrados %IP_COUNT% enderecos de rede!
)

echo.
echo Certificado sera gerado para:
echo   Hostname: %HOSTNAME%
echo   IPs: %IP_LIST%
echo.
echo Este certificado funcionara:
echo   - Via hostname: https://%HOSTNAME%:5000
echo   - Via IP em TODAS as interfaces de rede
echo.
pause

:: Ir para pasta de certificados (config/ssl)
cd /d "%~dp0\..\.."
if not exist "config\ssl" (
    mkdir "config\ssl"
)
cd /d "config\ssl"

echo.
echo [2/4] Instalando CA raiz local (pode pedir senha de admin)...
echo.

:: Instalar CA raiz
mkcert -install

if %errorlevel% neq 0 (
    echo.
    echo [ERRO] Falha ao instalar CA raiz!
    echo Tente executar como Administrador.
    echo.
    pause
    exit /b 1
)

echo.
echo [OK] CA raiz instalado!
echo.

echo [3/4] Gerando certificados SSL multi-IP + hostname...
echo.

:: Gerar certificados com hostname + TODOS os IPs
mkcert -cert-file cert.pem -key-file key.pem %HOSTNAME% %IP_LIST%

if %errorlevel% neq 0 (
    echo.
    echo [ERRO] Falha ao gerar certificados!
    echo.
    pause
    exit /b 1
)

echo.
echo [OK] Certificados gerados com sucesso!
echo.

echo [4/4] Verificando arquivos...
echo.

if exist "cert.pem" (
    echo [OK] cert.pem criado em config\ssl\
) else (
    echo [ERRO] cert.pem NAO encontrado!
)

if exist "key.pem" (
    echo [OK] key.pem criado em config\ssl\
) else (
    echo [ERRO] key.pem NAO encontrado!
)

echo.
echo ============================================
echo   CERTIFICADOS PRONTOS!
echo ============================================
echo.
echo Arquivos criados em config\ssl\:
echo   - cert.pem (certificado publico)
echo   - key.pem (chave privada)
echo.
echo Configuracao:
echo   - Hostname: %HOSTNAME%
echo   - IPs configurados: %IP_COUNT% enderecos de rede
echo.
echo Acesse o servidor via:
echo   - https://%HOSTNAME%:5000 (RECOMENDADO)
echo   - https://localhost:5000
for /f "tokens=2 delims=:" %%a in ('ipconfig ^| findstr /c:"IPv4"') do (
    set "DISPLAY_IP=%%a"
    set "DISPLAY_IP=!DISPLAY_IP: =!"
    echo !DISPLAY_IP! | findstr /b /c:"127." >nul
    if errorlevel 1 (
        echo   - https://!DISPLAY_IP!:5000
    )
)
echo.
echo ============================================
echo   IMPORTANTE - CLIENTES
echo ============================================
echo.
echo Para que outros dispositivos confiem no certificado:
echo.
echo 1. Execute: DISTRIBUIR_CERTIFICADO.bat
echo    (Isso copia o certificado CA para uma pasta compartilhavel)
echo.
echo 2. Instale o certificado CA (rootCA.pem) em cada dispositivo
echo    Veja: ..\docs\INSTALACAO_CERTIFICADO_CLIENTES.md
echo.
echo 3. Acesse via hostname: https://%HOSTNAME%:5000
echo.
echo ============================================
echo.
pause


