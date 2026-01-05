# Script de Build de Produção Invisível
# Executa o build do frontend sem abrir janela do CMD e sem interação

param(
    [switch]$Verbose
)

# Configurações
$ErrorActionPreference = "Stop"
$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$LogFile = Join-Path $ScriptDir "build_prod.log"
$StartTime = Get-Date

# Função para log
function Write-Log {
    param([string]$Message, [string]$Level = "INFO")
    $Timestamp = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
    $LogMessage = "[$Timestamp] [$Level] $Message"
    Add-Content -Path $LogFile -Value $LogMessage
    if ($Verbose -or $Level -eq "ERROR") {
        Write-Host $LogMessage
    }
}

# Função para limpar ao sair
function Exit-Script {
    param([int]$ExitCode = 0, [string]$Message = "")
    
    $EndTime = Get-Date
    $Duration = $EndTime - $StartTime
    
    if ($Message) {
        Write-Log $Message ($ExitCode -eq 0 ? "INFO" : "ERROR")
    }
    
    Write-Log "Build finalizado em $($Duration.TotalSeconds.ToString('F2')) segundos"
    
    exit $ExitCode
}

# Iniciar log
Write-Log "=========================================="
Write-Log "Iniciando build de produção"
Write-Log "=========================================="

# Verificar se estamos no diretório correto
if (-not (Test-Path (Join-Path $ScriptDir "package.json"))) {
    Write-Log "ERRO: package.json não encontrado. Execute este script a partir do diretório frontend_v2" "ERROR"
    Exit-Script 1 "Script executado no diretório incorreto"
}

# Verificar se Node.js está instalado
try {
    $nodeVersion = node --version 2>&1
    Write-Log "Node.js detectado: $nodeVersion"
} catch {
    Write-Log "ERRO: Node.js não encontrado. Instale Node.js antes de executar o build" "ERROR"
    Exit-Script 1 "Node.js não instalado"
}

# Verificar se npm está instalado
try {
    $npmVersion = npm --version 2>&1
    Write-Log "npm detectado: $npmVersion"
} catch {
    Write-Log "ERRO: npm não encontrado. Instale npm antes de executar o build" "ERROR"
    Exit-Script 1 "npm não instalado"
}

# Verificar se node_modules existe
if (-not (Test-Path (Join-Path $ScriptDir "node_modules"))) {
    Write-Log "node_modules não encontrado. Instalando dependências..."
    try {
        $installOutput = npm install 2>&1
        if ($LASTEXITCODE -ne 0) {
            Write-Log "ERRO ao instalar dependências: $installOutput" "ERROR"
            Exit-Script 1 "Falha na instalação de dependências"
        }
        Write-Log "Dependências instaladas com sucesso"
    } catch {
        Write-Log "ERRO ao instalar dependências: $_" "ERROR"
        Exit-Script 1 "Falha na instalação de dependências"
    }
}

# Limpar build anterior (opcional, mas recomendado)
Write-Log "Limpando build anterior..."
try {
    if (Test-Path (Join-Path $ScriptDir "dist")) {
        Remove-Item -Path (Join-Path $ScriptDir "dist") -Recurse -Force -ErrorAction SilentlyContinue
        Write-Log "Build anterior removido"
    }
} catch {
    Write-Log "AVISO: Não foi possível limpar build anterior: $_" "WARN"
}

# Executar build
Write-Log "Executando build de produção (npm run build)..."
try {
    # Redirecionar saída para capturar erros
    $buildOutput = npm run build 2>&1
    
    if ($LASTEXITCODE -ne 0) {
        Write-Log "ERRO no build: $buildOutput" "ERROR"
        Exit-Script 1 "Falha no build"
    }
    
    Write-Log "Build executado com sucesso"
    if ($Verbose) {
        Write-Host $buildOutput
    }
} catch {
    Write-Log "ERRO ao executar build: $_" "ERROR"
    Exit-Script 1 "Falha no build"
}

# Verificar se dist foi criado
if (-not (Test-Path (Join-Path $ScriptDir "dist"))) {
    Write-Log "ERRO: Diretório dist não foi criado após o build" "ERROR"
    Exit-Script 1 "Build não gerou arquivos"
}

# Verificar se index.html existe
if (-not (Test-Path (Join-Path $ScriptDir "dist\index.html"))) {
    Write-Log "ERRO: index.html não encontrado em dist" "ERROR"
    Exit-Script 1 "Build incompleto"
}

Write-Log "Build concluído com sucesso!"
Write-Log "Arquivos gerados em: $(Join-Path $ScriptDir 'dist')"

Exit-Script 0 "Build finalizado com sucesso"
