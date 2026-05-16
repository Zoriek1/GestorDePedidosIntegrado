#!/usr/bin/env bash
# Deploy manual na VPS (fora do GitHub Actions).
# Alinha ao fluxo do CI: um build Vite local e Docker com USE_PREBUILT_DIST=1
# (menos RAM/CPU na VPS do que npm dentro do container).
#
# Pré-requisitos: Node 20+, Docker Compose v2, estar na raiz do repositório.
# Variáveis Vite: exporte VITE_GOOGLE_MAPS_API_KEY antes se necessário (igual ao .env de produção).

set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$ROOT"

echo "📦 Build do frontend → docker/prebuilt-dist/"
cd frontend
npm ci --no-audit --no-fund
export VITE_API_BASE_URL="${VITE_API_BASE_URL:-/api}"
npm run build
cd "$ROOT"

mkdir -p docker/prebuilt-dist
find docker/prebuilt-dist -mindepth 1 -delete
cp -a frontend/dist/. docker/prebuilt-dist/

echo "🐳 docker compose (USE_PREBUILT_DIST=1)"
export USE_PREBUILT_DIST=1
docker compose up -d --build
docker image prune -f

echo "✅ Deploy concluído."
