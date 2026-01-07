# Script para iniciar servidor de produção de forma invisível
# Executa wsgi.py sem abrir janela do CMD e sem interação

param(
    [switch]$Verbose
)

# Configurações
$ErrorActionPreference = "Stop"
$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$LogFile = Join-Path $ScriptDir "servidor_producao.log"
$StartTime = Get-Date

# Função para log
function Write-Log {
    param([string]$Message, [string]$Level = "INFO")
    $Timestamp = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
    $LogMessage = "[$Timestamp] [$Level] $Message"
    Add-Content -Path $LogFile -Value $LogMessage
    if ($Verbose) {
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
    
    Write-Log "Servidor finalizado após $($Duration.TotalSeconds.ToString('F2')) segundos"
    
    exit $ExitCode
}

# Iniciar log
Write-Log "=========================================="
Write-Log "Iniciando servidor de produção (silencioso)"
Write-Log "=========================================="

# Verificar se estamos no diretório correto
$wsgiPath = Join-Path $ScriptDir "wsgi.py"
if (-not (Test-Path $wsgiPath)) {
    Write-Log "ERRO: wsgi.py não encontrado em $ScriptDir" "ERROR"
    Exit-Script 1 "Arquivo wsgi.py não encontrado"
}

# Verificar se Python está instalado
try {
    $pythonVersion = python --version 2>&1
    Write-Log "Python detectado: $pythonVersion"
} catch {
    Write-Log "ERRO: Python não encontrado. Instale Python antes de executar o servidor" "ERROR"
    Exit-Script 1 "Python não instalado"
}

# Verificar se Waitress está instalado
try {
    $waitressCheck = python -c "import waitress" 2>&1
    if ($LASTEXITCODE -ne 0) {
        Write-Log "Waitress não encontrado. Instalando..." "WARN"
        $installOutput = pip install waitress 2>&1
        if ($LASTEXITCODE -ne 0) {
            Write-Log "ERRO ao instalar Waitress: $installOutput" "ERROR"
            Exit-Script 1 "Falha na instalação do Waitress"
        }
        Write-Log "Waitress instalado com sucesso"
    } else {
        Write-Log "Waitress já instalado"
    }
} catch {
    Write-Log "ERRO ao verificar Waitress: $_" "ERROR"
    Exit-Script 1 "Falha ao verificar Waitress"
}

# Verificar se a porta já está em uso
try {
    $portCheck = netstat -an | Select-String ":5000" | Select-String "LISTENING"
    if ($portCheck) {
        Write-Log "AVISO: Porta 5000 já está em uso. Servidor pode já estar rodando." "WARN"
        Write-Log "Continuando mesmo assim (modo silencioso)" "INFO"
    }
} catch {
    Write-Log "AVISO: Não foi possível verificar porta 5000: $_" "WARN"
}

# Configurar variáveis de ambiente para produção
$env:FLASK_ENV = "production"
$env:FORCE_START = "true"

# Navegar para o diretório backend
Set-Location $ScriptDir

Write-Log "Iniciando servidor Waitress (wsgi.py)..."
Write-Log "Logs do servidor serão salvos em: $LogFile"

# Executar wsgi.py em background e redirecionar output para log
try {
    # Iniciar processo em background sem janela
    # Redireciona stdout e stderr para o mesmo arquivo de log
    $process = Start-Process -FilePath "python" `
        -ArgumentList "wsgi.py" `
        -WorkingDirectory $ScriptDir `
        -NoNewWindow `
        -WindowStyle Hidden `
        -RedirectStandardOutput $LogFile `
        -RedirectStandardError $LogFile `
        -PassThru `
        -ErrorAction Stop
    
    Write-Log "Servidor iniciado (PID: $($process.Id))"
    
    # Salvar PID em arquivo para facilitar parada
    $pidFile = Join-Path $ScriptDir "servidor.pid"
    $process.Id | Out-File -FilePath $pidFile -Encoding ASCII -Force
    Write-Log "PID salvo em: $pidFile"
    
    # Aguardar um pouco para verificar se iniciou corretamente
    Start-Sleep -Seconds 3
    
    if ($process.HasExited) {
        $exitCode = $process.ExitCode
        $errorOutput = ""
        if (Test-Path $LogFile) {
            $errorOutput = Get-Content $LogFile -Tail 20 -Raw -ErrorAction SilentlyContinue
        }
        Write-Log "ERRO: Servidor encerrou imediatamente (Exit Code: $exitCode)" "ERROR"
        if ($errorOutput) {
            Write-Log "Últimas linhas do log: $errorOutput" "ERROR"
        }
        Exit-Script 1 "Servidor falhou ao iniciar"
    }
    
    Write-Log "Servidor está rodando corretamente"
    Write-Log "Para parar: Execute parar_servidor_silencioso.ps1 ou Get-Process -Id $($process.Id) | Stop-Process"
    Write-Log "Logs sendo salvos em: $LogFile"
    
    # Aguardar processo (bloqueia até servidor parar)
    $process.WaitForExit()
    
    $exitCode = $process.ExitCode
    Write-Log "Servidor encerrado (Exit Code: $exitCode)"
    
    # Limpar arquivo PID
    if (Test-Path $pidFile) {
        Remove-Item $pidFile -Force -ErrorAction SilentlyContinue
    }
    
    Exit-Script $exitCode "Servidor encerrado"
    
} catch {
    Write-Log "ERRO ao iniciar servidor: $_" "ERROR"
    Write-Log "Stack trace: $($_.ScriptStackTrace)" "ERROR"
    Exit-Script 1 "Falha ao iniciar servidor"
}
