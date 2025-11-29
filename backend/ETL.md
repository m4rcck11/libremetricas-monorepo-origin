# ETL Tools - Execução em Produção

## Overview

Os tools de ETL foram **removidos do container da API** para manter a imagem de produção limpa e segura. Para executar jobs de coleta e processamento de dados, use os comandos abaixo.

## Opção 1: Docker Compose (Recomendado)

### Executar job único

```bash
# Coleta interativa de dados
docker compose -f docker-compose.etl.yml run --rm etl

# Sync automático de dados
docker compose -f docker-compose.etl.yml run --rm etl python /app/tools/run_data_sync.py

# Processar todos os eventos
docker compose -f docker-compose.etl.yml run --rm etl python /app/tools/process_all_events.py

# Processar eventos específicos
docker compose -f docker-compose.etl.yml run --rm etl python /app/tools/process_crossref_events.py
```

### Cronjob exemplo

Adicionar ao crontab do servidor:

```bash
# Sync diário às 2:00 AM
0 2 * * * cd /path/to/backend && docker compose -f docker-compose.etl.yml run --rm etl python /app/tools/run_data_sync.py >> /var/log/etl_sync.log 2>&1

# Processar eventos às 3:00 AM
0 3 * * * cd /path/to/backend && docker compose -f docker-compose.etl.yml run --rm etl python /app/tools/process_all_events.py >> /var/log/etl_process.log 2>&1
```

## Opção 2: Docker Run (Sem Compose)

```bash
# Build da imagem ETL
docker build -f Dockerfile.etl -t altmetria_etl .

# Executar job
docker run --rm \
  -v $(pwd)/data:/app/data \
  -v $(pwd)/tools:/app/tools \
  --env-file .env \
  altmetria_etl python /app/tools/run_data_sync.py
```

## Opção 3: Ambiente Virtual Local

Para desenvolvimento local:

```bash
# Criar ambiente virtual
python -m venv venv
source venv/bin/activate

# Instalar dependências
pip install -r requirements.txt

# Executar tools
python tools/collect_data_gcp.py
python tools/run_data_sync.py
```

## Estrutura dos Tools

```
tools/
├── config.py                    # Configuração dos tools
├── collect_data_gcp.py          # Menu interativo para coleta
├── run_data_sync.py             # Sync automático (não-interativo)
├── process_all_events.py        # Consolidador de eventos
├── process_crossref_events.py   # Processador Crossref
├── process_bluesky_events.py    # Processador Bluesky
└── collect_*_events.py          # Coletores por fonte
```

## Arquivos de Configuração

Variáveis de ambiente necessárias em `.env`:

```bash
# GCP
GCP_PROJECT_ID=your_project
GCP_BUCKET_NAME=your_bucket

# Crossref (se aplicável)
CROSSREF_API_EMAIL=your@email.com

# Bluesky (se aplicável)
BLUESKY_API_KEY=your_key
```

## Logs

Logs dos jobs ETL devem ser redirecionados para arquivos no host:

```bash
# Exemplo com log rotation
docker compose -f docker-compose.etl.yml run --rm etl \
  python /app/tools/run_data_sync.py 2>&1 | \
  tee -a /var/log/altmetria/etl_$(date +%Y%m%d).log
```

## Troubleshooting

### Permissões de dados

Se houver erro de permissão no diretório `/app/data`:

```bash
sudo chown -R 1000:1000 ./data
```

### Container não encontra tools

Verificar se o volume está montado corretamente:

```bash
docker compose -f docker-compose.etl.yml run --rm etl ls -la /app/tools
```

## Diferença entre Arquivos

| Arquivo | Uso |
|---------|-----|
| `Dockerfile` | Imagem de produção da API (NÃO inclui tools) |
| `Dockerfile.etl` | Imagem para jobs ETL (apenas tools) |
| `docker-compose.yml` | Desenvolvimento local (inclui hot reload) |
| `docker-compose.prod.yml` | Produção da API (apenas /data) |
| `docker-compose.etl.yml` | Jobs ETL em produção |
