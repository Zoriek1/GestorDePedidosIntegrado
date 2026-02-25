# Script para parar servidor de produção silencioso
# Lê o PID do arquivo servidor.pid e encerra o processo

param(
    [switch]$Force
)

$ErrorActionPreference = "Stop"
$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$PidFile = Join-Path $ScriptDir "servidor.pid"
$LogFile = Join-Path $ScriptDir "servidor_producao.log"

function Write-Log {
    param([string]$Message, [string]$Level = "INFO")
    $Timestamp = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
    $LogMessage = "[$Timestamp] [$Level] $Message"
    Add-Content -Path $LogFile -Value $LogMessage
    Write-Host $LogMessage
}

Write-Log "Parando servidor de produção..."

# Verificar se arquivo PID existe
if (-not (Test-Path $PidFile)) {
    Write-Log "AVISO: Arquivo servidor.pid não encontrado. Tentando encontrar processo por porta..." "WARN"
    
    # Tentar encontrar processo pela porta 5000
    try {
        $netstat = netstat -ano | Select-String ":5000" | Select-String "LISTENING"
        if ($netstat) {
            $pid = ($netstat -split '\s+')[-1]
            Write-Log "Processo encontrado na porta 5000 (PID: $pid)"
        } else {
            Write-Log "Nenhum processo encontrado na porta 5000. Servidor pode não estar rodando." "WARN"
            exit 0
        }
    } catch {
        Write-Log "ERRO ao buscar processo: $_" "ERROR"
        exit 1
    }
} else {
    # Ler PID do arquivo
    try {
        $pid = Get-Content $PidFile -ErrorAction Stop
        Write-Log "PID lido do arquivo: $pid"
    } catch {
        Write-Log "ERRO ao ler arquivo PID: $_" "ERROR"
        exit 1
    }
}

# Verificar se processo existe
try {
    $process = Get-Process -Id $pid -ErrorAction Stop
    Write-Log "Processo encontrado: $($process.ProcessName) (PID: $pid)"
    
    # Parar processo
    if ($Force) {
        Write-Log "Forçando encerramento do processo..."
        Stop-Process -Id $pid -Force
    } else {
        Write-Log "Encerrando processo graciosamente..."
        Stop-Process -Id $pid
    }
    
    Write-Log "Processo encerrado com sucesso"
    
    # Remover arquivo PID
    if (Test-Path $PidFile) {
        Remove-Item $PidFile -Force
        Write-Log "Arquivo PID removido"
    }
    
    Write-Log "Servidor parado com sucesso"
    exit 0
    
} catch [System.Management.Automation.ProcessCommandException] {
    Write-Log "Processo não encontrado (já foi encerrado?)" "WARN"
    
    # Remover arquivo PID se existir
    if (Test-Path $PidFile) {
        Remove-Item $PidFile -Force
        Write-Log "Arquivo PID removido"
    }
    
    exit 0
} catch {
    Write-Log "ERRO ao parar processo: $_" "ERROR"
    exit 1
}
