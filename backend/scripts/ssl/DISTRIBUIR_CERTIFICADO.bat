@echo off
setlocal enabledelayedexpansion
:: ===================================================
:: PLANTE UMA FLOR - Distribuir Certificado CA
:: Copia o certificado CA para compartilhamento
:: ===================================================

title Distribuir Certificado CA

echo.
echo ============================================
echo    DISTRIBUIR CERTIFICADO CA
echo    Plante Uma Flor - HTTPS
echo ============================================
echo.

cd /d "%~dp0"

:: Ler hostname do arquivo de configuração
set "HOSTNAME=Gestor-pedidos.local"
if exist "..\config_servidor.ini" (
    for /f "tokens=2 delims==" %%a in ('findstr "hostname" ..\config_servidor.ini') do (
        set "HOSTNAME=%%a"
        set "HOSTNAME=!HOSTNAME: =!"
    )
)

echo [INFO] Hostname do servidor: %HOSTNAME%
echo.

:: Verificar se mkcert está disponível
where mkcert >nul 2>&1
if %errorlevel% equ 0 (
    set MKCERT_CMD=mkcert
    goto :mkcert_found
)

if exist "mkcert.exe" (
    set MKCERT_CMD=.\mkcert.exe
    goto :mkcert_found
)

echo [ERRO] mkcert nao encontrado!
echo.
echo Execute primeiro: INSTALAR_MKCERT_SIMPLES.bat
echo.
pause
exit /b 1

:mkcert_found

:: Obter localização do certificado CA
echo [1/3] Localizando certificado CA...
echo.

for /f "delims=" %%a in ('%MKCERT_CMD% -CAROOT') do set "CAROOT=%%a"

if not exist "%CAROOT%\rootCA.pem" (
    echo [ERRO] Certificado CA nao encontrado!
    echo.
    echo Execute primeiro: GERAR_CERTIFICADOS_AUTO.bat
    echo.
    pause
    exit /b 1
)

echo [OK] CA encontrado em: %CAROOT%
echo.

:: Criar pasta de distribuição
echo [2/3] Criando pasta de distribuicao...
echo.

if not exist "PARA_CLIENTES" mkdir "PARA_CLIENTES"

:: Copiar certificado CA
copy "%CAROOT%\rootCA.pem" "PARA_CLIENTES\rootCA.pem" >nul

if %errorlevel% neq 0 (
    echo [ERRO] Falha ao copiar certificado!
    pause
    exit /b 1
)

echo [OK] Certificado copiado para: ssl\PARA_CLIENTES\
echo.

:: Criar arquivo README com instruções
echo [3/3] Gerando instrucoes...
echo.

(
echo # Certificado CA - Plante Uma Flor
echo.
echo ## Informacoes do Servidor
echo.
echo - **Hostname:** %HOSTNAME%
echo - **Porta:** 5000
echo - **Acesso:** https://%HOSTNAME%:5000
echo.
echo ---
echo.
echo ## Como Instalar este Certificado
echo.
echo ### Android
echo.
echo 1. Copie o arquivo `rootCA.pem` para o celular
echo 2. Abra **Configuracoes** ^> **Seguranca**
echo 3. Toque em **Instalar certificado** ou **Credenciais**
echo 4. Escolha **Certificado CA** ^> **Instalar mesmo assim**
echo 5. Navegue ate o arquivo `rootCA.pem`
echo 6. De um nome ^(ex: "Gestor Pedidos CA"^)
echo 7. Pronto! Acesse: https://%HOSTNAME%:5000
echo.
echo ### iOS / iPhone / iPad
echo.
echo 1. Envie o arquivo `rootCA.pem` por email ou AirDrop
echo 2. Abra o arquivo no dispositivo
echo 3. Va em **Ajustes** ^> **Geral** ^> **Perfis**
echo 4. Toque no perfil "mkcert"
echo 5. Toque em **Instalar** ^(digite a senha se pedido^)
echo 6. Va em **Ajustes** ^> **Geral** ^> **Sobre** ^> **Confianca do Certificado**
echo 7. Ative o certificado "mkcert"
echo 8. Pronto! Acesse: https://%HOSTNAME%:5000
echo.
echo ### Windows ^(Outros PCs^)
echo.
echo 1. Copie o arquivo `rootCA.pem` para o PC
echo 2. Clique duas vezes no arquivo
echo 3. Clique em **Instalar Certificado...**
echo 4. Escolha **Maquina Local** ^> **Avançar**
echo 5. Escolha **Colocar todos os certificados no repositorio a seguir**
echo 6. Clique em **Procurar** ^> Selecione **Autoridades de Certificacao Raiz Confiaveis**
echo 7. Clique em **Avançar** ^> **Concluir**
echo 8. Confirme o aviso de seguranca
echo 9. Pronto! Acesse: https://%HOSTNAME%:5000
echo.
echo ---
echo.
echo ## Solucao de Problemas
echo.
echo ### "Certificado nao e confiavel" / "Sua conexao nao e particular"
echo.
echo - Certifique-se de que o certificado foi instalado corretamente
echo - No Android/iOS, verifique se o certificado esta **ativo**
echo - Reinicie o navegador apos instalar
echo.
echo ### "Nao consigo acessar o servidor"
echo.
echo - Certifique-se de estar na mesma rede que o servidor
echo - Teste primeiro via IP: https://[IP-DO-SERVIDOR]:5000
echo - Verifique se o servidor esta rodando
echo.
echo ### "Nome nao pode ser resolvido" / "Hostname nao encontrado"
echo.
echo - mDNS pode nao funcionar em algumas redes
echo - Use o IP do servidor ao inves do hostname
echo - Em redes corporativas, pode estar bloqueado
echo.
echo ---
echo.
echo **Gerado em:** %date% %time%
echo **Servidor:** %HOSTNAME%
) > "PARA_CLIENTES\INSTRUCOES.md"

echo [OK] Instrucoes criadas: ssl\PARA_CLIENTES\INSTRUCOES.md
echo.

:: Mostrar resumo
echo ============================================
echo   CERTIFICADO PRONTO PARA DISTRIBUIR!
echo ============================================
echo.
echo Local: ssl\PARA_CLIENTES\
echo.
echo Arquivos criados:
echo   - rootCA.pem (certificado CA)
echo   - INSTRUCOES.md (como instalar)
echo.
echo ============================================
echo   PROXIMOS PASSOS
echo ============================================
echo.
echo 1. Compartilhe a pasta "PARA_CLIENTES" com os usuarios
echo    ^(via rede, pendrive, email, etc.^)
echo.
echo 2. Cada usuario deve instalar o rootCA.pem
echo    seguindo as instrucoes do arquivo INSTRUCOES.md
echo.
echo 3. Apos instalar, acessar: https://%HOSTNAME%:5000
echo.
echo ============================================
echo   DICA IMPORTANTE
echo ============================================
echo.
echo Use o HOSTNAME sempre que possivel:
echo   https://%HOSTNAME%:5000
echo.
echo Isso permite que o servidor mude de IP
echo sem precisar reinstalar certificados!
echo.
echo ============================================
echo.

:: Abrir pasta no Explorer
echo Deseja abrir a pasta PARA_CLIENTES agora? ^(S/N^)
set /p ABRIR=

if /i "%ABRIR%"=="S" (
    start explorer "PARA_CLIENTES"
)

echo.
echo Concluido!
pause

