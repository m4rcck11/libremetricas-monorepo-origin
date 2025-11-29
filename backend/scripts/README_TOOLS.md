# Executando Scripts dentro do Container Docker

Agora todos os scripts em `tools/` podem ser executados diretamente dentro do container Docker, que já tem todas as dependências instaladas.

## Modificações Realizadas

1. **Dockerfile**: Inclui `tools/` no build
2. **docker-compose.yml** e **docker-compose.prod.yml**: Montam `tools/` como volume
3. **requirements.txt**: Adicionadas dependências necessárias (pandas, pyarrow, requests, tqdm, atproto)

## Como Usar

### Opção 1: Script Helper (Recomendado)

```bash
# Rodar script de consolidação
./scripts/run_tool.sh process_all_events.py

# Rodar menu interativo
./scripts/run_tool.sh collect_data_gcp.py

# Ver ajuda
./scripts/run_tool.sh
```

### Opção 2: Docker Exec Direto

```bash
# Rodar script de consolidação
docker exec -it altmetria_api_duckdb python /app/tools/process_all_events.py

# Rodar processamento Crossref
docker exec -it altmetria_api_duckdb python /app/tools/process_crossref_events.py

# Rodar processamento Bluesky
docker exec -it altmetria_api_duckdb python /app/tools/process_bluesky_events.py

# Rodar processamento BORI
docker exec -it altmetria_api_duckdb python /app/tools/process_bori_events.py

# Rodar menu interativo
docker exec -it altmetria_api_duckdb python /app/tools/collect_data_gcp.py
```

### Opção 3: Entrar no Container

```bash
# Entrar no container interativamente
docker exec -it altmetria_api_duckdb bash

# Dentro do container:
cd /app/tools
python process_all_events.py
```

## Scripts Disponíveis

- **`process_all_events.py`** - Consolida eventos de todas as fontes (Crossref + Bluesky + BORI)
- **`process_crossref_events.py`** - Processa eventos brutos do Crossref
- **`process_bluesky_events.py`** - Processa eventos brutos do Bluesky
- **`process_bori_events.py`** - Processa eventos brutos do BORI (Agência BORI)
- **`collect_crossref_events.py`** - Coleta eventos da API Crossref (via menu)
- **`collect_bluesky_events.py`** - Coleta eventos do Bluesky Firehose (streaming)
- **`collect_data_gcp.py`** - Menu interativo completo

## Exemplo: Migração de Dados Existentes

```bash
# 1. Copiar arquivo completo para processed/
docker exec -it altmetria_api_duckdb cp /app/data/crossref_clean_events.parquet /app/data/events/processed/crossref_clean_events.parquet

# 2. Rodar consolidação
./scripts/run_tool.sh process_all_events.py

# 3. Verificar resultado
docker exec -it altmetria_api_duckdb ls -lh /app/data/events/consolidated/
docker exec -it altmetria_api_duckdb ls -lh /app/data/crossref_clean_events.parquet
```

## Vantagens

✅ Não precisa instalar Python/venv no servidor  
✅ Todas as dependências já estão instaladas  
✅ Ambiente isolado e consistente  
✅ Fácil de manter e atualizar  


