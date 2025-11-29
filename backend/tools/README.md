# ETL Tools - Processamento de Dados

Scripts para coleta e processamento de dados altmetricos.

## Estrutura de Arquivos

```
tools/
├── run_data_sync.py              # Sync automatizado OpenAlex LATAM
├── collect_data_gcp.py           # Menu interativo para operacoes manuais
├── collect_crossref_events.py    # Coletor de eventos Crossref
├── process_crossref_events.py    # Processador de eventos Crossref
├── process_bori_events.py        # Processador de eventos BORI
├── process_all_events.py         # Consolidador de todas as fontes
└── config.py                     # Configuracoes centralizadas
```

## Localizacao dos Dados

```
data/
├── *.parquet                           # OpenAlex LATAM (works, authors, institutions, etc)
├── analytics.duckdb                    # Catalogo de metadados DuckDB
├── events/
│   ├── raw/
│   │   ├── crossref/                   # Eventos brutos Crossref
│   │   └── BORI/                       # Eventos brutos BORI
│   ├── processed/
│   │   ├── crossref_clean_events.parquet
│   │   └── bori_clean_events.parquet
│   └── consolidated/
│       └── all_events.parquet          # Arquivo final consolidado
└── crossref_clean_events.parquet       # Symlink para consolidated/all_events.parquet
```

## Passo a Passo - Setup Inicial

### Opcao 1: Com Docker (Recomendado)

1. Baixar dados OpenAlex LATAM:
```bash
docker compose -f docker-compose.etl.yml run --rm etl python /app/tools/run_data_sync.py
```

2. Verificar download:
```bash
docker compose -f docker-compose.etl.yml run --rm etl ls -lh /app/data
```

3. Coletar eventos Crossref:
```bash
docker compose -f docker-compose.etl.yml run --rm etl python /app/tools/collect_crossref_events.py
```

4. Processar eventos Crossref:
```bash
docker compose -f docker-compose.etl.yml run --rm etl python /app/tools/process_crossref_events.py
```

5. Consolidar eventos (CRITICO - sempre executar por ultimo):
```bash
docker compose -f docker-compose.etl.yml run --rm etl python /app/tools/process_all_events.py
```

### Opcao 2: Sem Docker

1. Instalar dependencias:
```bash
pip install -r requirements.txt
```

2. Configurar variaveis de ambiente (criar .env ou exportar):
```bash
export GCS_BUCKET_NAME=altmetria_latam_ibict_tables
export LOCAL_DOWNLOAD_PATH=./data
export CROSSREF_MAILTO=seu@email.com
```

3. Executar scripts:
```bash
python tools/run_data_sync.py
python tools/collect_crossref_events.py
python tools/process_crossref_events.py
python tools/process_all_events.py
```

## Pipeline de Processamento

### 1. Dados OpenAlex LATAM

Script: run_data_sync.py
Fonte: GCS bucket (Google Cloud Storage)
Destino: /data/*.parquet
Frequencia: Diario

O que faz:
- Sincronizacao incremental (so baixa arquivos novos)
- Valida integridade dos dados
- API le automaticamente os .parquet via DuckDB

### 2. Eventos Crossref

Coleta:
```bash
python tools/collect_crossref_events.py
```
Entrada: API Crossref Event Data
Saida: /data/events/raw/crossref/p*_*.parquet

Processamento:
```bash
python tools/process_crossref_events.py
```
Entrada: /data/events/raw/crossref/
Saida: /data/events/processed/crossref_clean_events.parquet

### 3. Eventos BORI

Upload manual:
- Colocar arquivos .parquet em /data/events/raw/BORI/

Processamento:
```bash
python tools/process_bori_events.py
```
Entrada: /data/events/raw/BORI/*.parquet
Saida: /data/events/processed/bori_clean_events.parquet

### 4. Consolidacao (SEMPRE EXECUTAR POR ULTIMO)

```bash
python tools/process_all_events.py
```

O que faz:
- Carrega eventos de todas as fontes processadas
- Combina tudo (UNION ALL)
- Remove duplicatas
- Cria /data/events/consolidated/all_events.parquet
- Cria symlink crossref_clean_events.parquet apontando para o consolidado

IMPORTANTE: A API le o arquivo via symlink. Sempre execute este script apos atualizar qualquer fonte.

## Menu Interativo (Desenvolvimento)

Para operacoes manuais, use o menu interativo:

```bash
docker compose -f docker-compose.etl.yml run --rm etl python /app/tools/collect_data_gcp.py
```

Ou sem Docker:
```bash
python tools/collect_data_gcp.py
```

Opcoes do menu:
- 1: Baixar dados OpenAlex
- 2: Listar arquivos baixados
- 3: Concatenar dados
- 10: Coletar eventos Crossref
- 11: Processar eventos Crossref
- 13: Processar eventos BORI
- 14: Consolidar todos os eventos

## Automacao para Producao

Criar cronjob ou task scheduler:

```bash
# Sync diario OpenAlex as 2h
0 2 * * * cd /path/to/backend && docker compose -f docker-compose.etl.yml run --rm etl python /app/tools/run_data_sync.py >> /var/log/etl_sync.log 2>&1

# Coletar eventos Crossref as 3h
0 3 * * * cd /path/to/backend && docker compose -f docker-compose.etl.yml run --rm etl python /app/tools/collect_crossref_events.py >> /var/log/etl_crossref.log 2>&1

# Processar Crossref as 4h
0 4 * * * cd /path/to/backend && docker compose -f docker-compose.etl.yml run --rm etl python /app/tools/process_crossref_events.py >> /var/log/etl_process.log 2>&1

# Consolidar as 5h
0 5 * * * cd /path/to/backend && docker compose -f docker-compose.etl.yml run --rm etl python /app/tools/process_all_events.py >> /var/log/etl_consolidate.log 2>&1
```

Ou criar script unico:

```bash
#!/bin/bash
# daily_etl.sh
set -e

docker compose -f docker-compose.etl.yml run --rm etl python /app/tools/run_data_sync.py
docker compose -f docker-compose.etl.yml run --rm etl python /app/tools/collect_crossref_events.py
docker compose -f docker-compose.etl.yml run --rm etl python /app/tools/process_crossref_events.py
docker compose -f docker-compose.etl.yml run --rm etl python /app/tools/process_all_events.py

echo "ETL pipeline concluido: $(date)"
```

Agendar:
```bash
0 2 * * * /path/to/backend/scripts/daily_etl.sh >> /var/log/daily_etl.log 2>&1
```

## Configuracao

Arquivo: tools/config.py

Principais variaveis:
- GCS_BUCKET_NAME: Bucket GCS com dados OpenAlex LATAM
- LOCAL_DOWNLOAD_PATH: Diretorio local para dados (/app/data em Docker)
- CROSSREF_MAILTO: Email para API Crossref
- CROSSREF_ROWS_PER_REQUEST: Eventos por requisicao (padrao: 200)
- CROSSREF_REQUEST_DELAY: Delay entre requests (padrao: 1.0s)
- CHUNK_SIZE: Linhas por batch (padrao: 50000)

Override via .env ou variaveis de ambiente.

## Troubleshooting

Verificar estrutura de dados:
```bash
docker compose -f docker-compose.etl.yml run --rm etl ls -lhR /app/data/events
```

Verificar symlink:
```bash
docker compose -f docker-compose.etl.yml run --rm etl ls -l /app/data/crossref_clean_events.parquet
```

Logs do processamento:
```bash
cat tools/import_biblio.log
```

Permissoes (se necessario):
```bash
sudo chown -R 1000:1000 ./data
```

## Ordem de Execucao Recomendada

1. run_data_sync.py - Baixa OpenAlex LATAM
2. collect_crossref_events.py - Coleta eventos Crossref
3. process_crossref_events.py - Processa eventos Crossref
4. process_bori_events.py - Processa eventos BORI (se houver novos dados)
5. process_all_events.py - Consolida tudo (SEMPRE POR ULTIMO)

A API estara pronta para servir dados assim que os arquivos estiverem em /data.
