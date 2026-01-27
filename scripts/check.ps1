$ErrorActionPreference = "Stop"

Write-Host "== CI local check (Windows) ==" -ForegroundColor Cyan

# Backend (Python)
Write-Host "`n-- Backend: ruff/black/pytest --" -ForegroundColor Yellow
Push-Location "backend"
try {
  python -m pip install -r "requirements.txt" | Out-Null
  ruff check .
  black --check .
  pytest "tests/" -v --cov=app --cov-report=term-missing -m "not integration and not slow"
  pytest "tests/" -v -m "integration" --tb=short
} finally {
  Pop-Location
}

# Frontend (Node)
Write-Host "`n-- Frontend: typecheck/lint/build --" -ForegroundColor Yellow
Push-Location "frontend_v2"
try {
  npm ci --prefer-offline --no-audit --no-fund
  npx tsc --noEmit
  npm run lint
  npm run build
} finally {
  Pop-Location
}

Write-Host "`nOK: tudo passou (igual CI)." -ForegroundColor Green

