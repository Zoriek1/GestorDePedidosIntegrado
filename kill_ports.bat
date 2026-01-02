@echo off
chcp 65001 > nul
setlocal enabledelayedexpansion

echo ============================================================
echo   ENCERRAR PROCESSOS NAS PORTAS 5000 E 3000
echo ============================================================
echo.

REM Função para matar processo em uma porta específica
set PORT_5000_FOUND=0
set PORT_3000_FOUND=0

echo [INFO] Verificando porta 5000...
for /f "tokens=5" %%a in ('netstat -ano ^| findstr :5000 ^| findstr LISTENING') do (
    set PID=%%a
    echo [INFO] Processo encontrado na porta 5000 (PID: !PID!)
    taskkill /PID !PID! /F >nul 2>&1
    if !errorlevel! equ 0 (
        echo [OK] Processo na porta 5000 encerrado com sucesso
        set PORT_5000_FOUND=1
    ) else (
        echo [AVISO] Falha ao encerrar processo na porta 5000 (PID: !PID!)
    )
)

if !PORT_5000_FOUND! equ 0 (
    echo [INFO] Nenhum processo encontrado na porta 5000
)

echo.
echo [INFO] Verificando porta 3000...
for /f "tokens=5" %%a in ('netstat -ano ^| findstr :3000 ^| findstr LISTENING') do (
    set PID=%%a
    echo [INFO] Processo encontrado na porta 3000 (PID: !PID!)
    taskkill /PID !PID! /F >nul 2>&1
    if !errorlevel! equ 0 (
        echo [OK] Processo na porta 3000 encerrado com sucesso
        set PORT_3000_FOUND=1
    ) else (
        echo [AVISO] Falha ao encerrar processo na porta 3000 (PID: !PID!)
    )
)

if !PORT_3000_FOUND! equ 0 (
    echo [INFO] Nenhum processo encontrado na porta 3000
)

echo.
echo ============================================================
echo   PROCESSO CONCLUÍDO
echo ============================================================
echo.
pause

