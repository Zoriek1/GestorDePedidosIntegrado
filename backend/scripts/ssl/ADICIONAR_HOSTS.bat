@echo off
setlocal enabledelayedexpansion
:: ===================================================
:: Adicionar hostname ao arquivo hosts do Windows
:: ===================================================

title Adicionar Hostname - Plante Uma Flor

echo.
echo ============================================
echo   ADICIONAR HOSTNAME AO ARQUIVO HOSTS
echo ============================================
echo.
echo Este script adiciona o hostname ao arquivo hosts
echo para que o Windows possa resolver gestor-pedidos.local
echo.
echo IMPORTANTE: Precisa ser executado como Administrador!
echo.
pause

cd /d "%~dp0"

:: Ler hostname da configuração
set "HOSTNAME=Gestor-pedidos.local"
if exist "config_servidor.ini" (
    for /f "tokens=2 delims==" %%a in ('findstr "hostname" config_servidor.ini') do (
        set "HOSTNAME=%%a"
        set "HOSTNAME=!HOSTNAME: =!"
    )
)

:: Descobrir IP local
for /f "tokens=2 delims=:" %%a in ('ipconfig ^| findstr /c:"IPv4"') do (
    set IP=%%a
    goto :found_ip
)

:found_ip
set IP=%IP: =%

echo.
echo Hostname: %HOSTNAME%
echo IP Local: %IP%
echo.
echo Vou adicionar esta linha ao arquivo hosts:
echo %IP% %HOSTNAME%
echo.
pause

:: Verificar se já existe
findstr /i "%HOSTNAME%" C:\Windows\System32\drivers\etc\hosts >nul 2>&1
if %errorlevel% equ 0 (
    echo.
    echo [AVISO] Hostname ja existe no arquivo hosts!
    echo.
    echo Deseja substituir? (S/N)
    set /p SUBSTITUIR=
    
    if /i "%SUBSTITUIR%"=="S" (
        :: Remover linha antiga
        findstr /v /i "%HOSTNAME%" C:\Windows\System32\drivers\etc\hosts > C:\Windows\System32\drivers\etc\hosts.tmp
        move /y C:\Windows\System32\drivers\etc\hosts.tmp C:\Windows\System32\drivers\etc\hosts >nul
    ) else (
        echo.
        echo Operacao cancelada.
        pause
        exit /b 0
    )
)

:: Adicionar nova entrada
echo %IP% %HOSTNAME% >> C:\Windows\System32\drivers\etc\hosts

if %errorlevel% equ 0 (
    echo.
    echo [OK] Hostname adicionado com sucesso!
    echo.
    echo Agora voce pode acessar:
    echo   https://%HOSTNAME%:5000
    echo.
) else (
    echo.
    echo [ERRO] Falha ao adicionar hostname!
    echo.
    echo Certifique-se de executar como Administrador:
    echo 1. Clique com botao direito neste arquivo
    echo 2. "Executar como administrador"
    echo.
)

pause

