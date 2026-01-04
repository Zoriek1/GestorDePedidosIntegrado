# Script de DiagnÃ³stico de Performance do Build
# Execute: .\diagnostico_build.ps1

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "DiagnÃ³stico de Performance do Build" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

$errors = @()
$warnings = @()
$info = @()

# 1. Verificar tamanho do node_modules
Write-Host "[1/7] Verificando node_modules..." -ForegroundColor Yellow
if (Test-Path "node_modules") {
    $nodeModulesSize = (Get-ChildItem node_modules -Recurse -ErrorAction SilentlyContinue | Measure-Object -Property Length -Sum).Sum / 1GB
    $nodeModulesCount = (Get-ChildItem node_modules -Recurse -ErrorAction SilentlyContinue | Measure-Object).Count
    Write-Host "  Tamanho: $([math]::Round($nodeModulesSize, 2)) GB" -ForegroundColor Gray
    Write-Host "  Arquivos: $nodeModulesCount" -ForegroundColor Gray
    if ($nodeModulesSize -gt 1) {
        $warnings += "node_modules muito grande ($([math]::Round($nodeModulesSize, 2)) GB) - considere limpar"
    }
} else {
    $errors += "node_modules nÃ£o encontrado - execute: npm install"
    Write-Host "  âœ— node_modules nÃ£o encontrado" -ForegroundColor Red
}

# 2. Verificar cache do Vite
Write-Host "[2/7] Verificando cache do Vite..." -ForegroundColor Yellow
$viteCache = "node_modules\.vite"
if (Test-Path $viteCache) {
    $cacheSize = (Get-ChildItem $viteCache -Recurse -ErrorAction SilentlyContinue | Measure-Object -Property Length -Sum).Sum / 1MB
    Write-Host "  Cache: $([math]::Round($cacheSize, 2)) MB" -ForegroundColor Gray
    if ($cacheSize -gt 500) {
        $warnings += "Cache do Vite muito grande ($([math]::Round($cacheSize, 2)) MB) - considere limpar: npm run clean"
    }
} else {
    Write-Host "  âœ“ Cache do Vite nÃ£o existe (normal se nunca buildou)" -ForegroundColor Green
}

# 3. Verificar dist
Write-Host "[3/7] Verificando dist..." -ForegroundColor Yellow
if (Test-Path "dist") {
    $distSize = (Get-ChildItem dist -Recurse -ErrorAction SilentlyContinue | Measure-Object -Property Length -Sum).Sum / 1MB
    $distCount = (Get-ChildItem dist -Recurse -ErrorAction SilentlyContinue | Measure-Object).Count
    Write-Host "  Tamanho: $([math]::Round($distSize, 2)) MB" -ForegroundColor Gray
    Write-Host "  Arquivos: $distCount" -ForegroundColor Gray
} else {
    Write-Host "  âœ“ dist nÃ£o existe (normal se nunca buildou)" -ForegroundColor Green
}

# 4. Verificar TypeScript
Write-Host "[4/7] Testando TypeScript type checking..." -ForegroundColor Yellow
try {
    $tscTime = Measure-Command { npm run type-check 2>&1 | Out-Null }
    Write-Host "  Tempo: $([math]::Round($tscTime.TotalSeconds, 2))s" -ForegroundColor Gray
    if ($tscTime.TotalSeconds -gt 30) {
        $warnings += "TypeScript type checking estÃ¡ lento ($([math]::Round($tscTime.TotalSeconds, 2))s) - considere usar build:fast"
    }
} catch {
    $warnings += "NÃ£o foi possÃ­vel executar type checking: $($_.Exception.Message)"
    Write-Host "  âš  Erro ao executar type checking" -ForegroundColor Yellow
}

# 5. Verificar processos Node
Write-Host "[5/7] Verificando processos Node..." -ForegroundColor Yellow
$nodeProcesses = Get-Process node -ErrorAction SilentlyContinue
if ($nodeProcesses) {
    Write-Host "  Processos Node rodando: $($nodeProcesses.Count)" -ForegroundColor Gray
    foreach ($proc in $nodeProcesses) {
        $memMB = [math]::Round($proc.WorkingSet64 / 1MB, 2)
        Write-Host "    PID $($proc.Id): $memMB MB" -ForegroundColor Gray
    }
    if ($nodeProcesses.Count -gt 3) {
        $warnings += "Muitos processos Node rodando ($($nodeProcesses.Count)) - pode estar causando lentidÃ£o"
    }
} else {
    Write-Host "  âœ“ Nenhum processo Node rodando" -ForegroundColor Green
}

# 6. Verificar espaÃ§o em disco
Write-Host "[6/7] Verificando espaÃ§o em disco..." -ForegroundColor Yellow
try {
    $drive = (Get-Location).Drive.Name
    $disk = Get-PSDrive $drive
    $freeGB = [math]::Round($disk.Free / 1GB, 2)
    $totalGB = [math]::Round(($disk.Used + $disk.Free) / 1GB, 2)
    $usedGB = [math]::Round($disk.Used / 1GB, 2)
    $usedPercent = [math]::Round(($usedGB / $totalGB) * 100, 2)
    $diskInfo = "  Livre: $freeGB GB de $totalGB GB - $usedPercent pct usado"
    Write-Host $diskInfo -ForegroundColor Gray
    if ($freeGB -lt 5) {
        $errorMsg = "Pouco espaco em disco - $freeGB GB livre - pode causar lentidao"
        $errors += $errorMsg
        Write-Host "  âœ— Pouco espaÃ§o em disco" -ForegroundColor Red
    }
    if ($freeGB -ge 5 -and $freeGB -lt 10) {
        $warningMsg = "Espaco em disco baixo - $freeGB GB livre"
        $warnings += $warningMsg
        Write-Host "  âš  EspaÃ§o em disco baixo" -ForegroundColor Yellow
    }
} catch {
    $warnings += "Nao foi possivel verificar espaco em disco: $($_.Exception.Message)"
    Write-Host "  âš  Erro ao verificar espaÃ§o em disco" -ForegroundColor Yellow
}

# 7. Verificar memÃ³ria disponÃ­vel
Write-Host "[7/7] Verificando memÃ³ria..." -ForegroundColor Yellow
try {
    $mem = Get-CimInstance Win32_OperatingSystem
    $freeMemGB = [math]::Round($mem.FreePhysicalMemory / 1MB, 2)
    $totalMemGB = [math]::Round($mem.TotalVisibleMemorySize / 1MB, 2)
    $usedMemGB = $totalMemGB - $freeMemGB
    $memPercent = [math]::Round(($usedMemGB / $totalMemGB) * 100, 2)
    $memInfo = "  Livre: $freeMemGB GB de $totalMemGB GB - $memPercent pct usado"
    Write-Host $memInfo -ForegroundColor Gray
    if ($freeMemGB -lt 2) {
        $warningMsg = "Pouca memoria livre - $freeMemGB GB - pode causar lentidao no build"
        $warnings += $warningMsg
        Write-Host "  âš  Pouca memÃ³ria livre" -ForegroundColor Yellow
    }
} catch {
    $warnings += "Nao foi possivel verificar memoria: $($_.Exception.Message)"
    Write-Host "  âš  Erro ao verificar memÃ³ria" -ForegroundColor Yellow
}

# Resumo
Write-Host ""
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "Resumo do DiagnÃ³stico" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan

if ($errors.Count -eq 0 -and $warnings.Count -eq 0) {
    Write-Host "âœ“ Sistema parece estar OK" -ForegroundColor Green
    Write-Host ""
    Write-Host "Se o build ainda estiver lento, tente:" -ForegroundColor Cyan
    Write-Host "  1. npm run clean (limpar cache)" -ForegroundColor Gray
    Write-Host "  2. npm run build:fast (pular type checking)" -ForegroundColor Gray
    Write-Host "  3. Verificar antivÃ­rus (adicionar exclusÃµes)" -ForegroundColor Gray
} else {
    if ($errors.Count -gt 0) {
        Write-Host ""
        Write-Host "ERROS encontrados:" -ForegroundColor Red
        foreach ($error in $errors) {
            Write-Host "  âœ— $error" -ForegroundColor Red
        }
    }
    if ($warnings.Count -gt 0) {
        Write-Host ""
        Write-Host "AVISOS:" -ForegroundColor Yellow
        foreach ($warning in $warnings) {
            Write-Host "  âš  $warning" -ForegroundColor Yellow
        }
    }
    Write-Host ""
    Write-Host "AÃ§Ãµes recomendadas:" -ForegroundColor Cyan
    Write-Host "  1. npm run clean:full (limpar tudo)" -ForegroundColor Gray
    Write-Host "  2. npm run build:fast (build sem type checking)" -ForegroundColor Gray
    Write-Host "  3. Verificar BUILD_PERFORMANCE_FIX.md" -ForegroundColor Gray
}
