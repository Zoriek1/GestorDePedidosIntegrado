@echo off
echo Testando configuracao do servidor...
echo.

cd /d "%~dp0"

echo [1/4] Verificando Python...
python --version
if %errorlevel% neq 0 (
    echo [ERRO] Python nao encontrado!
    pause
    exit /b 1
)
echo [OK] Python encontrado
echo.

echo [2/4] Verificando config_servidor.ini...
if exist "config_servidor.ini" (
    echo [OK] Arquivo existe
    type config_servidor.ini
) else (
    echo [ERRO] Arquivo config_servidor.ini nao encontrado!
)
echo.

echo [3/4] Verificando certificados SSL...
if exist "ssl\cert.pem" (
    echo [OK] cert.pem existe
) else (
    echo [AVISO] cert.pem NAO encontrado
)

if exist "ssl\key.pem" (
    echo [OK] key.pem existe
) else (
    echo [AVISO] key.pem NAO encontrado
)
echo.

echo [4/4] Testando imports Python...
python -c "import sys; import os; import configparser; from pathlib import Path; print('[OK] Todos os modulos importados com sucesso')"
if %errorlevel% neq 0 (
    echo [ERRO] Falha ao importar modulos
    pause
    exit /b 1
)
echo.

echo ============================================
echo   TESTE COMPLETO
echo ============================================
echo.
echo Tudo parece OK. Vou tentar iniciar o servidor...
echo.
echo Pressione qualquer tecla para iniciar...
pause >nul

echo.
echo Iniciando servidor HTTP (teste)...
echo.
python main.py

pause

