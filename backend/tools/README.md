# Backend - ETL e API

Scripts de ETL (Extract, Transform, Load) para coleta e processamento de dados altmétricos, e API REST para consultas analíticas.

## Arquitetura

- **API REST**: FastAPI + DuckDB (leitura analítica sobre Parquet)
- **ETL**: Scripts Python para coleta e transformação de dados
- **Dados**: Arquivos Parquet armazenados em `/data`

## Estrutura de Diretórios

```
backend/
├── app/              # Código da API FastAPI
├── tools/            # Scripts de ETL
│   ├── run_data_sync.py          # Sincroniza dados do GCS (automatizado)
│   ├── collect_data_gcp.py       # Menu interativo para coleta
│   ├── process_all_events.py     # Consolida eventos
│   ├── process_crossref_events.py
│   ├── process_bori_events.py
│   ├── collect_crossref_events.py
│   └── config.py                 # Configurações centralizadas
├── data/             # Dados Parquet (volume Docker)
└── docker-compose.yml
```

## Iniciar o Backend

### Via Docker Compose

```bash
cd backend

# Subir a API
docker compose up --build

# Em outro terminal, popular dados iniciais
docker exec -it altmetria_api_duckdb python tools/run_data_sync.py
```

A API estará disponível em `http://localhost:8000`

### Desenvolvimento Local (sem Docker)

```bash
cd backend

# Instalar dependências
pip install -r requirements.txt

# Executar API
uvicorn app.main:app --reload --port 8000
```

## Scripts de ETL

### Sincronizar Dados do GCS (OpenAlex LATAM)

```bash
# Modo automatizado (produção)
docker exec -it altmetria_api_duckdb python tools/run_data_sync.py

# Modo interativo (desenvolvimento)
docker exec -it altmetria_api_duckdb python tools/collect_data_gcp.py
```

O sistema implementa sincronização incremental: apenas arquivos novos são baixados. Arquivos existentes são preservados.

### Processar Eventos Altmétricos

```bash
# Processar eventos Crossref
docker exec -it altmetria_api_duckdb python tools/process_crossref_events.py

# Processar eventos BORI
docker exec -it altmetria_api_duckdb python tools/process_bori_events.py

# Consolidar todas as fontes
docker exec -it altmetria_api_duckdb python tools/process_all_events.py
```

### Coletar Novos Eventos

```bash
# Coletar eventos via API Crossref
docker exec -it altmetria_api_duckdb python tools/collect_crossref_events.py
```

## Configuração

### Variáveis de Ambiente

Principais variáveis configuráveis no `.env` ou no `docker-compose.yml`:

```bash
# Google Cloud Storage
GCS_BUCKET_NAME=altmetria_latam_ibict_tables
LOCAL_DOWNLOAD_PATH=/app/data

# API
DEBUG=False
RATE_LIMIT_ENABLED=true
RATE_LIMIT_PER_MINUTE=100
CACHE_ENABLED=true
CACHE_TTL_SECONDS=300

# Performance
CHUNK_SIZE=50000
MAX_RETRIES=3
REQUEST_TIMEOUT=300
```

## Deploy em Produção

### Via Docker Compose

```bash
cd backend

# Subir serviço
docker compose up -d

# Download inicial de dados
docker exec altmetria_api_duckdb python tools/run_data_sync.py

# Verificar saúde da API
curl http://localhost:8000/health
```

### Agendar Sincronização Automática

Adicione ao crontab do host ou dentro do container:

```bash
# Executar diariamente às 2h
0 2 * * * docker exec altmetria_api_duckdb python tools/run_data_sync.py
```

### Monitoramento

```bash
# Logs da API
docker logs -f altmetria_api_duckdb

# Verificar arquivos de dados
docker exec altmetria_api_duckdb ls -lh /app/data

# Health check
curl http://localhost:8000/health
```

## Estrutura de Dados

O sistema trabalha com arquivos Parquet organizados em:

- `/data/*.parquet` - Tabelas OpenAlex LATAM (autores, obras, instituições)
- `/data/events/raw/` - Eventos altmétricos brutos (Crossref, BORI)
- `/data/events/processed/` - Eventos processados
- `/data/events/consolidated/` - Eventos consolidados de todas as fontes
