#!/bin/bash

echo "Starting deploy process..."

# 1. Entra na pasta do frontend e gera os arquivos estáticos
echo "📦 Building Frontend..."
cd frontend_v2
npm install --silent
npm run build
cd ..

# 2. Garante que os arquivos do build estão no lugar que o Flask espera
# (Ajuste 'backend/static' para a pasta que seu Flask usa)
echo "🚚 Moving static files..."
cp -r frontend_v2/dist/* backend/static/ 2>/dev/null || cp -r frontend_v2/build/* backend/static/

# 3. Reinicia os containers para aplicar mudanças de código Python ou ENV
echo "🔄 Restarting Containers..."
docker compose up -d

# 4. Limpa lixos do Docker para não encher o disco da VPS
docker image prune -f

echo "✅ Deploy Finished! Site updated."
