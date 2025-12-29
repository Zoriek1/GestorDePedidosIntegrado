@echo off
:: ===================================================
:: PLANTE UMA FLOR - Abrir Sistema HTTPS
:: Inicia o servidor HTTPS e abre no navegador
:: ===================================================

title Plante Uma Flor - Inicializando...

:: Ir para o diretório do backend (subir 3 níveis: start -> server -> scripts -> backend)
cd /d "%~dp0\..\..\.."

echo.
echo ============================================
echo    PLANTE UMA FLOR - Sistema HTTPS
echo ============================================
echo.

:: Verificar certificados (agora em instance/ssl/)
if not exist "instance\ssl\cert.pem" (
    :: Fallback: verificar no local antigo (config/ssl/) para compatibilidade
    if not exist "config\ssl\cert.pem" (
        if not exist "config\ssl\localhost+2.pem" (
            echo [ERRO] Certificados nao encontrados!
            echo.
            echo Execute primeiro:
            echo   1. scripts\ssl\INSTALAR_MKCERT_SIMPLES.bat
            echo   2. scripts\ssl\GERAR_CERTIFICADOS_AUTO.bat
            echo.
            echo Os certificados serao salvos em: instance\ssl\
            echo.
            pause
            exit /b 1
        )
    ) else (
        echo [AVISO] Certificados encontrados no local antigo (config\ssl\)
        echo Por favor, mova para instance\ssl\ ou gere novos certificados
        echo.
    )
)

:: Iniciar servidor invisível
echo [1/2] Iniciando servidor HTTPS em background...
start /min "" wscript.exe "%~dp0iniciar_servidor_https_invisivel.vbs"

:: Aguardar servidor iniciar
echo [2/2] Aguardando servidor inicializar...
timeout /t 5 /nobreak >nul

:: Descobrir IP local
for /f "tokens=2 delims=:" %%a in ('ipconfig ^| findstr /c:"IPv4"') do (
    set IP=%%a
    goto :found_ip
)

:found_ip
set IP=%IP: =%

echo.
echo [OK] Servidor HTTPS iniciado!
echo.
echo Abrindo navegador...

:: Abrir no navegador padrão
start https://localhost:5000

echo.
echo ============================================
echo   SERVIDOR RODANDO EM BACKGROUND
echo ============================================
echo.
echo Acesse de outros dispositivos:
echo   https://%IP%:5000
echo.
echo Para parar o servidor:
echo   Execute: scripts\server\stop\parar_tudo_incluindo_vbs.bat
echo.
echo ============================================
echo.

timeout /t 3
exit


