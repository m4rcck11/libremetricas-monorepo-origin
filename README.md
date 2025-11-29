# Plataforma Altmetria - Backend API (v0.0.2)

API REST de alta performance desenvolvida para fornecer métricas altmétricas de publicações acadêmicas da América Latina. O sistema utiliza uma arquitetura **OLAP (Online Analytical Processing)** baseada em DuckDB e arquivos Parquet, garantindo respostas rápidas com baixo custo computacional.

## Tecnologias

- **Runtime:** Python 3.11 (ou superior).
- **Framework Web:** FastAPI
- **Engine Analítica:** DuckDB (Zero-copy sobre Parquet)
- **Servidor de Aplicação:** Gunicorn + Uvicorn (Production Grade)
- **Segurança & Performance:** - SlowAPI (para Rate Limiting)
  - Pydantic 
  - Cachetools (Cache em memória L1)

## 🏗️ Arquitetura

O projeto segue uma arquitetura segregada para garantir estabilidade em ambiente governamental/institucional:

1.  **API (Stateless):** Responsável apenas pela leitura e agregação dos dados. Não realiza gravações no banco principal em tempo de execução.
2.  **Dados (Persistência):** Os dados residem em arquivos `.parquet` e um catálogo DuckDB montados via Volume.
3.  **Ferramentas (ETL):** Scripts de coleta e processamento (`tools/`), atualmente desacoplados da execução da API.


## Executar localmente:

**Pré-requisitos**:
- Docker e Docker-Compose
- Python 3.11+

**Via Docker**

Configure as variáveis de ambiente
> O projeto inclui um .env.example. Você pode copiá-lo e configurá-lo manualmente ou usá-lo para a configuração no Kubernetes. 

**Prepare os Dados**: Depois da configuração do container, é preciso configurar o container etl ou rodar manualmente os programas de atualização do banco de dados. Os downloads consultam nossos buckets para baixar os arquivos parquets necessários para exibir a análise.

4. Executar:
> docker compose up --build

A API já está disponível em http://localhost:8000


# Deploy em produção (Local/Cloud)

A aplicação é container first. 

1. Variáveis de ambiente segregadas (.env)

O container precisa das seguintes variáveis de ambiente:

> DATA_DIR -----> Caminho absoluto dentro do container -----> /app/data (default)
> DUCKDB_PATH -----> Caminho do arquivo de banco ------> /app/data/analytics.duckdb
> CORS_ORIGINS --> Configurações de domínio (como não sei, tudo está liberado) -> siteoficial.com.bre
> WORKERS ------> Número de processos em paralelo no gunicorn ---> 4 (default)

## Segurança da API 

#### Rate Limiting (configurável na env)
#### Read-Only Database: Conexão com o DuckDB é aberta estritamente em modo leitura (read_only=True), previne corrupção de dados por concorrência.
#### Privilégios: o container roda como usuário (sem root).

## Manutenção e Atualização dos dados

A pasta tools/ contém scripts para coleta de novas métricas oriundas do CrossRef e BORI 

-> Arquivos CrossRef disponíveis em: (Arquivos pesados, servidor lento)
-> Arquivos Bori disponíveis em: "" ---> No alibaba Cloud (Bucket Público) (Arquivos leves)
-> Arquivos OpenAlex disponíveis em: "" --> No Google Cloud (Bucket Público) (Dados gigantes, servidor "rápido")

### Os scripts tem tratamento de erro, retry e os dados são salvos incrementalmente para contornar eventuais falhas de rede.


**Nota**: Estes scripts devem ser executados em um processo separado (Worker ou CronJob) e não no container da API, para evitar degradação de performance. 



## Inserção dos Dados para Análise via DuckDB (em casos de atualização)

Com o DuckDB temos um banco de dados de 12KB. Com o DuckDB, separamos a lógica do banco de dados, que já está dividido em parquets. O arquivo >analyitics.duckdb é apenas o código.

## Frontend
´´bash

cd frontend 
npm run build 

´´

**Configure a rota da API**: A rota da api (Frontend > src > api > AxiosConfig.js services está temporariamente em um domínio MARKDEV. Para utilizar localmente, insira o endereço local (localhost:8000) ou o CNAME de hospedagem da API.


### O frontend então estará disponível em :5173.
