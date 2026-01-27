$ErrorActionPreference = "Stop"

Write-Host "== Auto-fix (format/lint) ==" -ForegroundColor Cyan

# Backend (Python) - auto fix
Write-Host "`n-- Backend: ruff --fix + black --" -ForegroundColor Yellow
Push-Location "backend"
try {
  python -m pip install -r "requirements.txt" | Out-Null
  ruff check . --fix
  black .
} finally {
  Pop-Location
}

# Frontend (Node) - auto fix
Write-Host "`n-- Frontend: eslint --fix --" -ForegroundColor Yellow
Push-Location "frontend_v2"
try {
  npm install
  npm run lint:fix
} finally {
  Pop-Location
}

Write-Host "`nPronto: rode 'scripts\\check.ps1' antes de subir." -ForegroundColor Green

