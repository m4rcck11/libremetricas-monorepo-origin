#!/bin/bash
# Helper script para rodar scripts de tools/ dentro do container Docker

set -e

CONTAINER_NAME="altmetria_api_duckdb"
SCRIPT_NAME="$1"

if [ -z "$SCRIPT_NAME" ]; then
    echo "Uso: $0 <script_name> [args...]"
    echo ""
    echo "Scripts disponíveis:"
    echo "  - process_all_events.py          - Consolidar todos os eventos"
    echo "  - process_crossref_events.py     - Processar eventos Crossref"
    echo "  - process_bluesky_events.py      - Processar eventos Bluesky"
    echo "  - process_bori_events.py         - Processar eventos BORI"
    echo "  - collect_crossref_events.py     - Coletar eventos Crossref (via menu)"
    echo "  - collect_bluesky_events.py     - Coletar eventos Bluesky (streaming)"
    echo "  - collect_data_gcp.py           - Menu interativo completo"
    echo ""
    echo "Exemplos:"
    echo "  $0 process_all_events.py"
    echo "  $0 collect_data_gcp.py"
    exit 1
fi

# Verificar se container está rodando
if ! docker ps | grep -q "$CONTAINER_NAME"; then
    echo "❌ Container $CONTAINER_NAME não está rodando!"
    echo "   Execute: docker compose -f docker-compose.prod.yml up -d"
    exit 1
fi

# Verificar se script existe
if [ ! -f "tools/$SCRIPT_NAME" ]; then
    echo "❌ Script tools/$SCRIPT_NAME não encontrado!"
    exit 1
fi

# Rodar script dentro do container
shift  # Remove primeiro argumento (script name)
echo "🚀 Executando: python /app/tools/$SCRIPT_NAME $@"
echo ""

docker exec -it "$CONTAINER_NAME" python /app/tools/$SCRIPT_NAME "$@"


