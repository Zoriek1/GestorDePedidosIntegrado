#!/usr/bin/env bash
#
# Analise de complexidade do backend com radon.
#   - CC (Complexidade Ciclomatica) por funcao/metodo
#   - MI (Indice de Manutenibilidade) por arquivo
#
# Roda dentro do container `backend` via docker compose. Como a imagem de
# producao instala apenas requirements.txt (nao o requirements-dev.txt), o
# radon e instalado sob demanda no container caso ainda nao exista.
#
# Uso (a partir de qualquer lugar):
#   ./backend/scripts/maintenance/analise_complexidade.sh          # resumo (CC + MI)
#   ./backend/scripts/maintenance/analise_complexidade.sh --full   # inclui blocos B (>5)
#
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd "$SCRIPT_DIR/../../.." && pwd)"   # .../GestorDePedidosIntegrado (onde esta o docker-compose.yml)
cd "$ROOT_DIR"

SERVICE="backend"
EXCLUDE='*/migrations/*'

# Por padrao mostra apenas C ou pior (CC > 10). Com --full, mostra B tambem (CC > 5).
MIN_RANK="C"
if [ "${1:-}" = "--full" ]; then
  MIN_RANK="B"
fi

echo ">> Garantindo radon no container '${SERVICE}'..."
# radon nao esta na imagem de producao; instala sob demanda (versao pinada em requirements-dev.txt).
# Sem aspas no '>=' o sh interpretaria como redirecionamento, entao instala sem specifier aqui.
docker compose exec -T "$SERVICE" sh -c 'python -m radon --version >/dev/null 2>&1 || pip install --quiet radon'

echo ""
echo "=============================================================="
echo " COMPLEXIDADE CICLOMATICA (CC) — blocos nota ${MIN_RANK} ou pior"
echo "=============================================================="
docker compose exec -T "$SERVICE" \
  python -m radon cc app --exclude "$EXCLUDE" -s -a --order SCORE --min "$MIN_RANK"

echo ""
echo "=============================================================="
echo " INDICE DE MANUTENIBILIDADE (MI) — arquivos nota B ou pior"
echo "=============================================================="
docker compose exec -T "$SERVICE" \
  python -m radon mi app --exclude "$EXCLUDE" -s --min B --max C

echo ""
echo ">> Referencia de metas e plano: docs/qualidade/complexidade-2026-07.md"
