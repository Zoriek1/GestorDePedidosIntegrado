@echo off
REM Atualizar/forçar recarregamento de cache do frontend (Service Worker + Python __pycache__)
REM Uso: execute este .bat enquanto o servidor estiver rodando. Os clientes vão pegar o novo SW ao recarregar a página.

setlocal enabledelayedexpansion

REM Caminho do Service Worker
set SW_FILE=frontend\sw.js

if not exist "%SW_FILE%" (
  echo [ERRO] Nao encontrei %SW_FILE% (execute a partir da raiz do projeto)
  goto :end
)

REM Gerar versao unica baseada em data/hora
for /f "tokens=1-4 delims=/ " %%a in ("%date%") do set TODAY=%%d%%b%%c
set TODAY=%date:~-4%%date:~3,2%%date:~0,2%
set NOW=%time: =0%
set NOW=%NOW::=%
set VERSION=%TODAY%%NOW%

echo [INFO] Nova versao de cache: %VERSION%

REM Atualizar constante CACHE_NAME no sw.js (usa PowerShell para replace por regex)
powershell -NoProfile -Command ^
  "$p='%SW_FILE%'; ^
   $c=Get-Content $p -Raw; ^
   $ts='%VERSION%'; ^
   $c=$c -replace "const CACHE_NAME = 'plante-uma-flor-v[^']+';", ('const CACHE_NAME = ''plante-uma-flor-v' + $ts + ''';'); ^
   Set-Content -Path $p -Value $c -Encoding UTF8; ^
   Write-Host '[OK] CACHE_NAME atualizado para v'$ts"

if errorlevel 1 (
  echo [ERRO] Falha ao atualizar CACHE_NAME no %SW_FILE%
  goto :end
)

REM Limpar pastas __pycache__ (Python bytecode)
echo [INFO] Limpando __pycache__...
for /d /r %%G in (__pycache__) do (
  rd /s /q "%%G" 2>nul
)
echo [OK] __pycache__ limpo.

REM Opcional: limpar cache do navegador NAO e feito aqui para evitar impacto no usuario
REM Opcional: abrir navegador com cache-bust para forcar registrar novo SW
set URL=http://localhost:5000/?cache_bust=%VERSION%
echo [INFO] Para forcar o navegador a pegar o novo SW, acesse: %URL%
REM start "" %URL%

echo.
echo [PRONTO] Versao do Service Worker atualizada. Recarregue a pagina do app (Ctrl+F5).

:end
endlocal

