@echo off
:: ===================================================
:: PLANTE UMA FLOR - Gerador de Certificados (Local)
:: Usa mkcert.exe local (não precisa estar no PATH)
:: ===================================================

title Gerar Certificados SSL (Local)

echo.
echo ============================================
echo    GERADOR DE CERTIFICADOS SSL (LOCAL)
echo    Plante Uma Flor - HTTPS Local
echo ============================================
echo.

cd /d "%~dp0"

:: Verificar se mkcert existe na pasta local
if not exist "mkcert.exe" (
    echo [ERRO] mkcert.exe nao encontrado nesta pasta!
    echo.
    echo Execute primeiro: INSTALAR_MKCERT_SIMPLES.bat
    echo.
    pause
    exit /b 1
)

echo [OK] mkcert.exe encontrado!
echo.

:: Testar mkcert
.\mkcert.exe -version
echo.

:: Descobrir o IP local
echo [1/4] Descobrindo IP da maquina...
echo.

for /f "tokens=2 delims=:" %%a in ('ipconfig ^| findstr /c:"IPv4"') do (
    set IP=%%a
    goto :found_ip
)

:found_ip
:: Remover espaços
set IP=%IP: =%

echo IP encontrado: %IP%
echo.

echo Este e o IP correto da sua maquina?
echo Se nao, pressione Ctrl+C e edite este arquivo na linha 40.
echo.
pause

:: Ir para pasta de certificados (config/ssl)
cd /d "%~dp0\..\.."
if not exist "config\ssl" (
    mkdir "config\ssl"
)
cd /d "config\ssl"

echo.
echo [2/4] Instalando CA raiz local...
echo (Pode pedir senha de administrador - isso e normal!)
echo.

:: Instalar CA raiz (voltar para pasta ssl para usar mkcert.exe)
cd /d "%~dp0"
.\mkcert.exe -install

if %errorlevel% neq 0 (
    echo.
    echo [ERRO] Falha ao instalar CA raiz!
    echo.
    echo Isso requer permissoes de administrador.
    echo Tente:
    echo 1. Clique com botao direito neste arquivo
    echo 2. "Executar como administrador"
    echo.
    pause
    exit /b 1
)

echo.
echo [OK] CA raiz instalado!
echo.

echo [3/4] Gerando certificados SSL...
echo.

:: Voltar para pasta de certificados e gerar
cd /d "%~dp0\..\..\config\ssl"

:: Gerar certificados (usar caminho completo do mkcert)
cd /d "%~dp0"
.\mkcert.exe -cert-file "..\..\config\ssl\cert.pem" -key-file "..\..\config\ssl\key.pem" localhost 127.0.0.1 %IP% ::1
cd /d "%~dp0\..\..\config\ssl"

if %errorlevel% neq 0 (
    echo.
    echo [ERRO] Falha ao gerar certificados!
    echo.
    pause
    exit /b 1
)

echo.
echo [OK] Certificados gerados!
echo.

echo [4/4] Verificando arquivos...
echo.

if exist "cert.pem" (
    echo [OK] cert.pem criado
) else (
    echo [ERRO] cert.pem NAO encontrado!
)

if exist "key.pem" (
    echo [OK] key.pem criado
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
echo IP configurado: %IP%
echo.
echo Proximos passos:
echo   1. Volte para: ..\
echo   2. Execute: abrir_sistema_https.bat
echo   3. Acesse: https://%IP%:5000
echo.
echo ============================================
echo.
pause


