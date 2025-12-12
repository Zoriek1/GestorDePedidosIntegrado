@echo off
chcp 65001 > nul
REM ============================================================
REM Backup Manual do Banco de Dados
REM Executa backup imediato do database.db
REM ============================================================

echo.
echo ============================================================
echo   BACKUP MANUAL - Gestor de Pedidos
echo ============================================================
echo.

REM Navegar para o diretório do backend
cd /d "%~dp0.."

REM Executar script de backup
echo [INFO] Iniciando backup...
echo.
python scripts\backup.py

if %errorLevel% equ 0 (
    echo.
    echo ============================================================
    echo [OK] Backup concluído!
    echo ============================================================
) else (
    echo.
    echo [ERRO] Erro ao executar backup!
    echo.
)

echo.
pause

