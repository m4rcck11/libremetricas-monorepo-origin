# Backend - API e ETL

API REST de alta performance para métricas altmétricas de publicações acadêmicas da América Latina. Arquitetura OLAP baseada em DuckDB e Parquet.

## Tecnologias

- **Runtime:** Python 3.11+
- **Framework Web:** FastAPI
- **Engine Analítica:** DuckDB (Zero-copy sobre Parquet)
- **Servidor:** Gunicorn + Uvicorn
- **Performance:** SlowAPI (Rate Limiting), Cachetools (Cache L1)

## Arquitetura

O sistema segue uma arquitetura segregada:

1. **API (Stateless):** Leitura e agregação de dados. Sem gravações em tempo de execução.
2. **Dados (Persistência):** Arquivos `.parquet` montados via volume Docker.
3. **ETL (Tools):** Scripts de coleta e processamento desacoplados da API.

## Estrutura

```
backend/
├── app/              # Código da API FastAPI
│   ├── main.py       # Endpoints da API
│   ├── database.py   # Conexão DuckDB
│   └── queries.py    # Queries analíticas
├── tools/            # Scripts de ETL
│   ├── run_data_sync.py          # Sincroniza dados do GCS
│   ├── collect_data_gcp.py       # Menu interativo
│   ├── process_all_events.py     # Consolida eventos
│   ├── process_crossref_events.py
│   ├── process_bori_events.py
│   └── collect_crossref_events.py
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

A API estará em `http://localhost:8000`

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

O sistema implementa sincronização incremental: apenas arquivos novos são baixados.

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

## Endpoints Principais

Documentação completa em `/docs` (Swagger)

### Sistema
- `GET /health` - Status da API e conexão com DuckDB

### Métricas e Agregações
- `GET /events_sources` - Eventos por fonte
- `GET /events_years` - Distribuição por anos
- `GET /fields_events` - Eventos por área de conhecimento

### Busca
- `POST /search_dois` - Recuperação de métricas por DOI

### Exportação
- `GET /all_events_data_filter_years_enriched/{ya}/{yb}` - Exportar CSV com dados enriquecidos

## Deploy em Produção

### Variáveis de Ambiente

```bash
# Docker Compose
DEBUG=False
RATE_LIMIT_ENABLED=true
RATE_LIMIT_PER_MINUTE=100
CACHE_ENABLED=true
CACHE_TTL_SECONDS=300

# GCS
GCS_BUCKET_NAME=altmetria_latam_ibict_tables
LOCAL_DOWNLOAD_PATH=/app/data

# Performance
CHUNK_SIZE=50000
MAX_RETRIES=3
REQUEST_TIMEOUT=300
```

### Deploy via Docker

```bash
cd backend

# Build e iniciar
docker compose up -d

# Download inicial de dados
docker exec altmetria_api_duckdb python tools/run_data_sync.py

# Verificar saúde
curl http://localhost:8000/health
```

### Agendar Sincronização Automática

Adicione ao crontab:

```bash
# Executar diariamente às 2h
0 2 * * * docker exec altmetria_api_duckdb python tools/run_data_sync.py
```

### Monitoramento

```bash
# Logs da API
docker logs -f altmetria_api_duckdb

# Verificar dados
docker exec altmetria_api_duckdb ls -lh /app/data

# Health check
curl http://localhost:8000/health
```

## Arquitetura de Dados (OLAP)

### Por que DuckDB?

OLAP (Online Analytical Processing) é processamento analítico, diferente de OLTP (transacional).

**Vantagens:**
1. **Zero-Copy:** Lê diretamente dos Parquets sem copiar dados
2. **Stateless:** Arquivo `.duckdb` tem apenas metadados (12KB)
3. **Vetorizado:** Lê colunas inteiras em vetores (CPU SIMD)
4. **Performance:** Queries em milissegundos sobre GBs de dados

### Exemplo de Performance

Query tradicional (linha por linha):
```
ID, Titulo, Ano, Autor
1, "Artigo A", 2023, "Dr. Silva"  <- lê linha inteira
2, "Artigo B", 2022, "Dra. Santos"
```

DuckDB (colunar):
```
Coluna Ano: [2023, 2022, 2024, ...]
Coluna Titulo: ["Artigo A", "Artigo B", ...]
```

Para `SELECT Titulo WHERE Ano = 2023`:
1. Escaneia apenas coluna `Ano` → encontra índices [0, 5, 12]
2. Busca apenas essas posições em `Titulo`
3. Retorna resultado em milissegundos

## Estrutura de Dados

Arquivos Parquet organizados em:

- `/data/*.parquet` - Tabelas OpenAlex LATAM (autores, obras, instituições)
- `/data/events/raw/` - Eventos brutos (Crossref, BORI, Bluesky)
- `/data/events/processed/` - Eventos processados
- `/data/events/consolidated/` - Eventos consolidados

## Segurança

- **Rate Limiting:** Configurável por endpoint
- **Read-Only Database:** DuckDB aberto em modo leitura
- **Container:** Executa sem privilégios root
- **SQL Injection:** Queries parametrizadas com placeholders

## Performance das Queries

### Categoria A: Dashboard Inicial
- Funções: `all_sources`, `all_events_years`
- Performance: < 50ms
- Leitura: Apenas arquivo de eventos

### Categoria B: Joins Complexos
- Funções: `event_journals`, `fields_events`
- Performance: 200-500ms
- Leitura: Eventos + metadados OpenAlex (7 tabelas)

### Categoria C: Exportação CSV
- Função: `all_events_data_filter_years_enriched`
- Performance: 800ms - 1.5s
- Dados escaneados: ~1.75 GB
- Rate limit: 10 requests/min
