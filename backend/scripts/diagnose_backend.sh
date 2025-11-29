#!/bin/bash
# Script de diagnóstico para verificar status do backend

echo "=== Status do Container ==="
docker ps -a | grep altmetria

echo ""
echo "=== Últimos 50 logs do container ==="
docker logs altmetria_api_duckdb --tail=50

echo ""
echo "=== Verificando arquivo crossref_clean_events.parquet ==="
docker exec altmetria_api_duckdb ls -lh /app/data/crossref_clean_events.parquet || echo "Arquivo não encontrado"

echo ""
echo "=== Verificando link simbólico ==="
docker exec altmetria_api_duckdb readlink -f /app/data/crossref_clean_events.parquet || echo "Link não encontrado"

echo ""
echo "=== Testando leitura DuckDB direta ==="
docker exec altmetria_api_duckdb python3 -c "
import duckdb
conn = duckdb.connect()
try:
    result = conn.execute('SELECT COUNT(*) FROM read_parquet(\"/app/data/events/consolidated/all_events.parquet\")').fetchone()
    print(f'✓ Arquivo legível: {result[0]:,} eventos')
except Exception as e:
    print(f'✗ Erro ao ler arquivo: {e}')
finally:
    conn.close()
"

echo ""
echo "=== Testando health endpoint ==="
curl -s http://localhost:8000/health || echo "Backend não está respondendo na porta 8000"


