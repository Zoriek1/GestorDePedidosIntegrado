@echo off
chcp 65001 > nul
REM ============================================================
REM Restaurar Backup do Banco de Dados
REM Interface para restauração interativa
REM ============================================================

echo.
echo ============================================================
echo   RESTAURAÇÃO DE BACKUP - Gestor de Pedidos
echo ============================================================
echo.
echo [AVISO] Esta operação irá SUBSTITUIR o banco de dados atual!
echo         Um backup preventivo será criado antes.
echo.
pause

REM Navegar para o diretório do backend
cd /d "%~dp0.."

REM Executar script de restauração
python scripts\restore.py

echo.
pause

