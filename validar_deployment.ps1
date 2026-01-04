# Script de Validação de Deployment
# Execute: .\validar_deployment.ps1

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "Validação de Deployment - Plante Uma Flor" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

$baseUrl = "http://localhost:5000"
$errors = @()
$warnings = @()

# 1. Verificar se porta 5000 está em uso
Write-Host "[1/8] Verificando porta 5000..." -ForegroundColor Yellow
$port5000 = netstat -an | Select-String ":5000.*LISTENING"
if ($port5000) {
    Write-Host "  ✓ Porta 5000 está em uso (servidor rodando)" -ForegroundColor Green
} else {
    $errors += "Porta 5000 não está em uso - servidor não está rodando"
    Write-Host "  ✗ Porta 5000 não está em uso" -ForegroundColor Red
}

# 2. Verificar se porta 3000 NÃO está em uso
Write-Host "[2/8] Verificando porta 3000 (deve estar livre)..." -ForegroundColor Yellow
$port3000 = netstat -an | Select-String ":3000.*LISTENING"
if ($port3000) {
    $warnings += "Porta 3000 está em uso - servidor antigo ainda rodando?"
    Write-Host "  ⚠ Porta 3000 está em uso (deveria estar livre)" -ForegroundColor Yellow
} else {
    Write-Host "  ✓ Porta 3000 está livre (correto)" -ForegroundColor Green
}

# 3. Verificar build do frontend
Write-Host "[3/8] Verificando build do frontend..." -ForegroundColor Yellow
$distPath = "frontend_v2\dist\index.html"
if (Test-Path $distPath) {
    Write-Host "  ✓ Build do frontend existe" -ForegroundColor Green
} else {
    $errors += "Build do frontend não encontrado - execute: cd frontend_v2 && npm run build"
    Write-Host "  ✗ Build do frontend não encontrado" -ForegroundColor Red
}

# 4. Health Check da API
Write-Host "[4/8] Testando /api/health..." -ForegroundColor Yellow
try {
    $healthResponse = Invoke-RestMethod -Uri "$baseUrl/api/health" -Method Get -ErrorAction Stop
    if ($healthResponse.status -eq "healthy" -or $healthResponse.success -eq $true) {
        Write-Host "  ✓ API health check OK" -ForegroundColor Green
        Write-Host "    Status: $($healthResponse.status)" -ForegroundColor Gray
    } else {
        $warnings += "API health check retornou status não saudável"
        Write-Host "  ⚠ API health check retornou status não saudável" -ForegroundColor Yellow
    }
} catch {
    $errors += "Falha ao conectar em /api/health: $($_.Exception.Message)"
    Write-Host "  ✗ Falha ao conectar: $($_.Exception.Message)" -ForegroundColor Red
}

# 5. Frontend sendo servido
Write-Host "[5/8] Testando frontend (/)..." -ForegroundColor Yellow
try {
    $frontendResponse = Invoke-WebRequest -Uri "$baseUrl/" -Method Get -ErrorAction Stop
    if ($frontendResponse.StatusCode -eq 200) {
        if ($frontendResponse.Content -match "<!DOCTYPE html|<!doctype html") {
            Write-Host "  ✓ Frontend sendo servido corretamente" -ForegroundColor Green
        } else {
            $warnings += "Frontend retornou HTML mas formato pode estar incorreto"
            Write-Host "  ⚠ Frontend retornou resposta mas formato pode estar incorreto" -ForegroundColor Yellow
        }
    } else {
        $errors += "Frontend retornou status $($frontendResponse.StatusCode)"
        Write-Host "  ✗ Frontend retornou status $($frontendResponse.StatusCode)" -ForegroundColor Red
    }
} catch {
    $errors += "Falha ao conectar no frontend: $($_.Exception.Message)"
    Write-Host "  ✗ Falha ao conectar: $($_.Exception.Message)" -ForegroundColor Red
}

# 6. Deep Link (SPA Routing)
Write-Host "[6/8] Testando deep link (/pedidos)..." -ForegroundColor Yellow
try {
    $deepLinkResponse = Invoke-WebRequest -Uri "$baseUrl/pedidos" -Method Get -ErrorAction Stop
    if ($deepLinkResponse.StatusCode -eq 200) {
        if ($deepLinkResponse.Content -match "<!DOCTYPE html|<!doctype html|index") {
            Write-Host "  ✓ Deep link funciona (retorna index.html)" -ForegroundColor Green
        } else {
            $warnings += "Deep link retornou 200 mas não parece ser HTML"
            Write-Host "  ⚠ Deep link retornou 200 mas formato pode estar incorreto" -ForegroundColor Yellow
        }
    } else {
        $errors += "Deep link retornou status $($deepLinkResponse.StatusCode) (deveria ser 200)"
        Write-Host "  ✗ Deep link retornou status $($deepLinkResponse.StatusCode)" -ForegroundColor Red
    }
} catch {
    if ($_.Exception.Response.StatusCode -eq 404) {
        $errors += "Deep link retorna 404 - SPA routing não está funcionando"
        Write-Host "  ✗ Deep link retorna 404" -ForegroundColor Red
    } else {
        $errors += "Falha ao testar deep link: $($_.Exception.Message)"
        Write-Host "  ✗ Falha: $($_.Exception.Message)" -ForegroundColor Red
    }
}

# 7. Headers de Segurança
Write-Host "[7/8] Verificando headers de segurança..." -ForegroundColor Yellow
try {
    $headersResponse = Invoke-WebRequest -Uri "$baseUrl/" -Method Head -ErrorAction Stop
    $securityHeaders = @(
        "X-Content-Type-Options",
        "X-Frame-Options",
        "Content-Security-Policy",
        "Referrer-Policy"
    )
    $foundHeaders = @()
    foreach ($header in $securityHeaders) {
        if ($headersResponse.Headers[$header]) {
            $foundHeaders += $header
        }
    }
    if ($foundHeaders.Count -eq $securityHeaders.Count) {
        Write-Host "  ✓ Todos os headers de segurança presentes" -ForegroundColor Green
    } elseif ($foundHeaders.Count -gt 0) {
        $warnings += "Alguns headers de segurança estão faltando: $($securityHeaders | Where-Object { $foundHeaders -notcontains $_ } | Join-String -Separator ', ')"
        Write-Host "  ⚠ Apenas $($foundHeaders.Count)/$($securityHeaders.Count) headers presentes" -ForegroundColor Yellow
        Write-Host "    Faltando: $($securityHeaders | Where-Object { $foundHeaders -notcontains $_ } | Join-String -Separator ', ')" -ForegroundColor Gray
    } else {
        $errors += "Nenhum header de segurança encontrado"
        Write-Host "  ✗ Nenhum header de segurança encontrado" -ForegroundColor Red
    }
} catch {
    $warnings += "Não foi possível verificar headers de segurança: $($_.Exception.Message)"
    Write-Host "  ⚠ Não foi possível verificar headers" -ForegroundColor Yellow
}

# 8. Verificar CORS
Write-Host "[8/8] Verificando CORS..." -ForegroundColor Yellow
try {
    $corsResponse = Invoke-WebRequest -Uri "$baseUrl/api/health" -Method Options -ErrorAction Stop
    if ($corsResponse.Headers["Access-Control-Allow-Origin"]) {
        Write-Host "  ✓ CORS configurado" -ForegroundColor Green
        Write-Host "    Allow-Origin: $($corsResponse.Headers['Access-Control-Allow-Origin'])" -ForegroundColor Gray
    } else {
        $warnings += "CORS pode não estar configurado corretamente"
        Write-Host "  ⚠ CORS pode não estar configurado" -ForegroundColor Yellow
    }
} catch {
    # OPTIONS pode não estar implementado, não é crítico
    Write-Host "  ⚠ Não foi possível verificar CORS (OPTIONS não implementado?)" -ForegroundColor Yellow
}

# Resumo
Write-Host ""
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "Resumo da Validação" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan

if ($errors.Count -eq 0 -and $warnings.Count -eq 0) {
    Write-Host "✓ Todas as validações passaram!" -ForegroundColor Green
    exit 0
} else {
    if ($errors.Count -gt 0) {
        Write-Host ""
        Write-Host "ERROS encontrados:" -ForegroundColor Red
        foreach ($error in $errors) {
            Write-Host "  ✗ $error" -ForegroundColor Red
        }
    }
    if ($warnings.Count -gt 0) {
        Write-Host ""
        Write-Host "AVISOS:" -ForegroundColor Yellow
        foreach ($warning in $warnings) {
            Write-Host "  ⚠ $warning" -ForegroundColor Yellow
        }
    }
    Write-Host ""
    Write-Host "Consulte DEPLOYMENT_VALIDATION.md para mais detalhes" -ForegroundColor Cyan
    exit 1
}
