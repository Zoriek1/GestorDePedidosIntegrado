@echo off
setlocal enabledelayedexpansion
:: ===================================================
:: PLANTE UMA FLOR - Configuração Inicial do Servidor
:: Script interativo para configurar o servidor
:: ===================================================

title Configuracao Inicial - Plante Uma Flor

color 0A

echo.
echo ====================================================
echo.
echo       PLANTE UMA FLOR - Configuracao Inicial
echo       Sistema de Gestao de Pedidos PWA
echo.
echo ====================================================
echo.
echo Este assistente vai configurar seu servidor HTTPS
echo com hostname personalizado para acesso em rede local.
echo.
echo Pressione qualquer tecla para comecar...
pause >nul
cls

:: ===================================================
:: PASSO 1: Verificar mkcert
:: ===================================================

echo.
echo ====================================================
echo   PASSO 1/4 - Verificando mkcert
echo ====================================================
echo.

cd /d "%~dp0"

where mkcert >nul 2>&1
if %errorlevel% equ 0 (
    echo [OK] mkcert encontrado no sistema!
    set MKCERT_OK=1
    goto :passo2
)

if exist "ssl\mkcert.exe" (
    echo [OK] mkcert encontrado na pasta ssl!
    set MKCERT_OK=1
    goto :passo2
)

echo [!] mkcert NAO encontrado!
echo.
echo O mkcert e necessario para gerar certificados SSL.
echo.
echo Deseja instalar o mkcert agora? (S/N)
set /p INSTALAR_MKCERT=

if /i "%INSTALAR_MKCERT%"=="S" (
    echo.
    echo Abrindo instalador do mkcert...
    cd ssl
    call INSTALAR_MKCERT_SIMPLES.bat
    cd ..
    
    echo.
    echo Pressione qualquer tecla para continuar...
    pause >nul
) else (
    echo.
    echo [!] mkcert e obrigatorio para continuar.
    echo Execute: ssl\INSTALAR_MKCERT_SIMPLES.bat
    echo.
    pause
    exit /b 1
)

:passo2
cls

:: ===================================================
:: PASSO 2: Configurar Hostname
:: ===================================================

echo.
echo ====================================================
echo   PASSO 2/4 - Configurar Hostname
echo ====================================================
echo.
echo O hostname permite que dispositivos na rede acessem
echo o servidor por um nome fixo ao inves de um IP.
echo.
echo Exemplo: https://Gestor-pedidos.local:5000
echo.
echo ====================================================
echo.

:: Verificar se ja existe configuracao
if exist "config_servidor.ini" (
    echo [!] Configuracao existente encontrada!
    echo.
    
    for /f "tokens=2 delims==" %%a in ('findstr "hostname" config_servidor.ini') do (
        set "HOSTNAME_ATUAL=%%a"
        set "HOSTNAME_ATUAL=!HOSTNAME_ATUAL: =!"
    )
    
    echo Hostname atual: !HOSTNAME_ATUAL!
    echo.
    echo Deseja manter este hostname? (S/N)
    set /p MANTER_HOSTNAME=
    
    if /i "!MANTER_HOSTNAME!"=="S" (
        set "HOSTNAME=!HOSTNAME_ATUAL!"
        goto :passo3
    )
)

echo.
echo Escolha o hostname do servidor:
echo.
echo 1. Gestor-pedidos.local (RECOMENDADO)
echo 2. Servidor-flores.local
echo 3. Personalizado
echo.
set /p ESCOLHA_HOSTNAME=Digite o numero (1-3): 

if "%ESCOLHA_HOSTNAME%"=="1" (
    set "HOSTNAME=Gestor-pedidos.local"
    goto :confirmar_hostname
)

if "%ESCOLHA_HOSTNAME%"=="2" (
    set "HOSTNAME=Servidor-flores.local"
    goto :confirmar_hostname
)

if "%ESCOLHA_HOSTNAME%"=="3" (
    echo.
    echo Digite o hostname desejado:
    echo (Use apenas letras, numeros e hifens, termine com .local)
    echo.
    set /p HOSTNAME=Hostname: 
    
    :: Verificar se termina com .local
    echo %HOSTNAME% | findstr /i ".local" >nul
    if errorlevel 1 (
        echo.
        echo [!] ATENCAO: Hostname deve terminar com .local
        echo Adicionando .local automaticamente...
        set "HOSTNAME=%HOSTNAME%.local"
    )
    
    goto :confirmar_hostname
)

echo.
echo [!] Opcao invalida. Usando padrao: Gestor-pedidos.local
set "HOSTNAME=Gestor-pedidos.local"

:confirmar_hostname
echo.
echo ====================================================
echo   Hostname configurado: %HOSTNAME%
echo ====================================================
echo.
echo Clientes poderao acessar via:
echo   https://%HOSTNAME%:5000
echo.
echo Confirmar? (S/N)
set /p CONFIRMAR_HOST=

if /i not "%CONFIRMAR_HOST%"=="S" (
    goto :passo2
)

:: Salvar configuracao
echo.
echo Salvando configuracao...

(
echo [SERVIDOR]
echo # Hostname mDNS do servidor (usado para acesso via nome ao inves de IP)
echo # Este hostname sera incluido nos certificados SSL
echo # Padrao: Gestor-pedidos.local
echo # 
echo # IMPORTANTE: 
echo # - Use apenas letras, numeros e hifens
echo # - Sempre termine com .local
echo # - Exemplo: Minha-Loja.local
echo #
echo hostname = %HOSTNAME%
echo.
echo [REDE]
echo # Porta do servidor (padrao: 5000)
echo porta = 5000
) > config_servidor.ini

echo [OK] Configuracao salva em config_servidor.ini
echo.
echo Pressione qualquer tecla para continuar...
pause >nul

:passo3
cls

:: ===================================================
:: PASSO 3: Gerar Certificados SSL
:: ===================================================

echo.
echo ====================================================
echo   PASSO 3/4 - Gerar Certificados SSL
echo ====================================================
echo.
echo Gerando certificados SSL com:
echo   - Hostname: %HOSTNAME%
echo   - Todos os IPs da maquina
echo.
echo Este processo pode pedir senha de administrador.
echo.
echo Pressione qualquer tecla para continuar...
pause >nul

echo.
cd ssl
call GERAR_CERTIFICADOS_AUTO.bat

if %errorlevel% neq 0 (
    echo.
    echo [ERRO] Falha ao gerar certificados!
    echo.
    pause
    exit /b 1
)

cd ..

:passo4
cls

:: ===================================================
:: PASSO 4: Distribuir Certificado CA
:: ===================================================

echo.
echo ====================================================
echo   PASSO 4/4 - Preparar Certificado para Clientes
echo ====================================================
echo.
echo Para que outros dispositivos confiem no servidor,
echo eles precisam instalar o certificado CA.
echo.
echo Deseja preparar o certificado para distribuicao? (S/N)
set /p PREPARAR_CA=

if /i "%PREPARAR_CA%"=="S" (
    echo.
    cd ssl
    call DISTRIBUIR_CERTIFICADO.bat
    cd ..
)

cls

:: ===================================================
:: CONCLUIDO!
:: ===================================================

echo.
echo ====================================================
echo.
echo      CONFIGURACAO CONCLUIDA COM SUCESSO!
echo.
echo ====================================================
echo.
echo Hostname configurado: %HOSTNAME%
echo Porta: 5000
echo.
echo ====================================================
echo   PROXIMOS PASSOS
echo ====================================================
echo.
echo [SERVIDOR]
echo.
echo 1. Inicie o servidor HTTPS:
echo    Execute: run\abrir_sistema_https.bat
echo.
echo 2. Acesse no servidor:
echo    https://localhost:5000
echo    ou
echo    https://%HOSTNAME%:5000
echo.
echo ====================================================
echo   CLIENTES (outros dispositivos)
echo ====================================================
echo.
echo 1. Compartilhe a pasta:
echo    ssl\PARA_CLIENTES\
echo.
echo 2. Em cada dispositivo, instale o certificado:
echo    rootCA.pem
echo.
echo 3. Siga as instrucoes em:
echo    docs\INSTALACAO_CERTIFICADO_CLIENTES.md
echo.
echo 4. Acesse no dispositivo:
echo    https://%HOSTNAME%:5000
echo.
echo 5. Instale o PWA normalmente!
echo.
echo ====================================================
echo   DOCUMENTACAO
echo ====================================================
echo.
echo - INICIO_RAPIDO.md
echo - docs\HTTPS.md
echo - docs\INSTALACAO_CERTIFICADO_CLIENTES.md
echo - docs\PORTABILIDADE.md
echo.
echo ====================================================
echo.
echo Pressione qualquer tecla para finalizar...
pause >nul

:: Perguntar se quer iniciar o servidor
echo.
echo Deseja iniciar o servidor agora? (S/N)
set /p INICIAR_SERVIDOR=

if /i "%INICIAR_SERVIDOR%"=="S" (
    echo.
    echo Iniciando servidor...
    cd run
    call abrir_sistema_https.bat
)

echo.
echo Obrigado por usar Plante Uma Flor! 🌺
echo.
pause

