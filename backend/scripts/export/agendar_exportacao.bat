@echo off
chcp 65001 >nul
echo ============================================
echo   AGENDAR EXPORTAÇÃO DIÁRIA ÀS 19:00
echo ============================================
echo.

REM Obtém o diretório do script
set "SCRIPT_DIR=%~dp0"
set "BACKEND_DIR=%SCRIPT_DIR%.."
set "PYTHON_SCRIPT=%SCRIPT_DIR%exportar_vendas_sheets.py"

echo Diretório: %BACKEND_DIR%
echo Script: %PYTHON_SCRIPT%
echo.

REM Cria a tarefa agendada
schtasks /create /tn "GestorPedidos_ExportarVendas" /tr "python \"%PYTHON_SCRIPT%\"" /sc daily /st 19:00 /f

if %errorlevel% equ 0 (
    echo.
    echo ✓ Tarefa agendada com sucesso!
    echo   Nome: GestorPedidos_ExportarVendas
    echo   Horário: 19:00 diariamente
    echo.
    echo Para verificar: schtasks /query /tn "GestorPedidos_ExportarVendas"
    echo Para remover: schtasks /delete /tn "GestorPedidos_ExportarVendas" /f
) else (
    echo.
    echo ✗ Erro ao criar tarefa. Execute como Administrador.
)

echo.
pause
