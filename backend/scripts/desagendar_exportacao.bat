@echo off
chcp 65001 >nul
echo ============================================
echo   REMOVER AGENDAMENTO DE EXPORTAÇÃO
echo ============================================
echo.

schtasks /delete /tn "GestorPedidos_ExportarVendas" /f

if %errorlevel% equ 0 (
    echo.
    echo ✓ Tarefa removida com sucesso!
) else (
    echo.
    echo ✗ Tarefa não encontrada ou erro ao remover.
)

echo.
pause
