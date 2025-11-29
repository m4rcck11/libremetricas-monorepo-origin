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

O sistema faz um mapeamento dinâmico dos arquivos na inicialização. Se o volume de arquivos crescer muito (10k+), podemos otimizar, mas para o volume atual é instantâneo. Cold Start de até 5 segundos, queries em milissegundos. 

O projeto segue uma arquitetura segregada para garantir estabilidade em ambiente governamental/institucional:

1.  **API (Stateless):** Responsável apenas pela leitura e agregação dos dados. Não realiza gravações no banco principal em tempo de execução.
2.  **Dados (Persistência):** Os dados residem em arquivos `.parquet` e um catálogo DuckDB montados via Volume.
3.  **Ferramentas (ETL):** Scripts de coleta e processamento (`tools/`), atualmente desacoplados da execução da API.


## Executar localmente:

**Pré-requisitos**:
- Docker e Docker-Compose
- Python 3.11^

**Via Docker**

Configure as variáveis de ambiente
> O projeto inclui um .env.example. Você pode copiá-lo e configurá-lo manualmente ou usá-lo para a configuração no Kubernetes. 

**Prepare os Dados**: Coloque os arquivos .parquet e o banco analytics.duckdb  na pasta ./data local. 

4. Executar:
> docker compose up --build

Pronto! A API já está disponível em http://localhost:8000


# Deploy em produção (Local/Cloud)

A aplicação é container first. 

1. Variáveis de ambiente segregadas (.env)

O container precisa das seguintes variáveis de ambiente:

> DATA_DIR -----> Caminho absoluto dentro do container -----> /app/data (default)
> DUCKDB_PATH -----> Caminho do arquivo de banco ------> /app/data/analytics.duckdb
> CORS_ORIGINS --> Configurações de domínio (como não sei, tudo está liberado) -> siteoficial.com.bre
> WORKERS ------> Número de processos em paralelo no gunicorn ---> 4 (default)

## Persistência dos dados

A pasta /app/data dentro do container precisa ser um volume montado com arquivos .parquet. A api não popula esses dados sozinha. A atualização precisa ser feita em jobs agendados que escrevem no mesmo volume.

**Para isso, temos scripts de apoio**

Em scripts/ incluí utilitários de referência para ambientes Linux/Debian, testados na minha máquina. Os shelss devem rodar em qualquer serviço em servidores até bare-metal.

- setup-firewall.sh -> configuração de firewall básica (rever com infra do IBICT)
- setup-ssl.sh (automação de certbot para certificado ssl)
- deploy.sh (exemplo de esteira local)

## Endpoints principais

Os endpoints principais estão na documentação swagger em /docs. Seguimos o contrato estabelecido pelo frontend. 

### Sistema
- GET /health - Status da API e conexão com o 'Banco de Dados'
### Métricas e Agregações
- GET /events_sources - Eventos por fonte
- GET /events_years - Distribuição por anos
- GET /fields_events - Eventos por área de conhecimen to (OpenAlex)

### Busca
- POST /search_dois - Recuperação de Métricas. Terminamos a implementação no frontend.

### Exportação

- **PRECISA DE CORREÇÃO** - Extração de dados brutos com rate limiting restritivo. A intenção é modificar para extrair dados brutos, e não apenas os disponíveis no frontend. 



## Segurança da API 

#### Rate Limiting (configurável na env)
#### Read-Only Database: Conexão com o DuckDB é aberta estritamente em modo leitura (read_only=True), previne corrupção de dados por concorrência.
#### Privilégios: o container roda como usuário (sem root).

## Manutenção e Atualização dos dados

A pasta tools/ contém scripts para coleta de novas métricas oriundas do CrossRef, Bluesky e BORI 

-> Arquivos CrossRef disponíveis em: (Arquivos pesados, servidor lento)
-> Arquivos Bluesky e Bori disponíveis em: "" ---> No alibaba Cloud (Bucket Público) (Arquivos leves)
-> Arquivos OpenAlex disponíveis em: "" --> No Google Cloud (Bucket Público) (Dados gigantes, servidor "rápido")

### Os scripts tem tratamento de erro, retry e os dados são salvos incrementalmente para contornar eventuais falhas de rede.


**Nota**: Estes scripts devem ser executados em um processo separado (Worker ou CronJob) e não no container da API, para evitar degradação de performance. 



## Inserção dos Dados para Análise via DuckDB (em casos de atualização)

Com o DuckDB temos um banco de dados de 12KB. Com o DuckDB, separamos a lógica do banco de dados, que já está dividido em parquets. O arquivo >analyitics.duckdb é apenas o código.


### O que é OLAP no nosso caso?

OLAP é o porcessamento analítico online, diferente de OLTP (transacional).

Com o duckDB (engine vetorizada): com o python puro podemos ler uma linha, processar, ler outra e assim sucetivamente. Agora, com o DuckDB, o processo é: ele lê todos os ítens de uma coluna e processa em vetores com instruções da CPU, isso faz com que ele entregue os arquivos mais digeridos em poucos milissegundos. 

### Qual é a arquitetura de dados?

Com DuckDB, a arquitetura de dados é uma Lakehouse moderna. O banco de dados é apenas um motor de processamento (DuckDB) que apenas lê os dados.

1. Arquitetura Zero-Cópia: O banco não copia os dados para dentro dele. Tudo é lido diretamente dos parquets. 
2. Computação sem estado (Stateless): Como o  arquivo de banco (.duckdb) guarda só os metadados, ele é leve (12KB) e descartável. Se o servidor parar de funcionar, os dados são mantidos porque tudo está dentro dos arquivos parquet, esses, imutáveis e baixados de fontes externas.
3. Performance OLAP: O DuckDB surgiu nas trends mais modernas entre desenvolvedores por usar execução vetorizada e sua inclinação de uso para leitura de dados de IA. O DuckDB consulta parquets em milissegundos e nos isenta de estruturar SQL transacional, o que seria um exagero para apenas visualizar dados. Ex: ele lê apenas a coluna 'Ano' do arquivo parquet e ignora o resto.

### Exemplo de funcionamento

O duckdb usa índices implícitos para fazer o alinhamento posicional. Veja essa consulta:

> ID, Titulo, Ano, Autor
> 1, "A Cura do Câncer", 2023, "Dr. Silva"  <-- O computador lê a linha inteira
> 2, "Estudo de IA", 2022, "Dra. Santos"

Se você quer saber, por ex, quantos artigos são de 2023, o computador lê a linha inteira do artigo em questão (neste exemplo, o artigo A) joga fora o que não precisa e guarda o ano. 

> No duckDB isso não acontece

O duckDB desmonta a tabela e guarda cada coluna em um lugar separado do arquivo. Por ex:

> Coluna ID [1, 2, 3, 4 ...]
> Coluna Título: ["DOI-Numero-Etc-2023" - "Pesquisa Sobre: ...", ...]
> Coluna Ano: [2023, 2024, 2025]
> Coluna Fonte: ["Bluesky", "wikipedia", ...]

E para conectar as pontas ele usa o Index. O DuckDB sabe que o primeiro item da coluna ano corresponde ao primeiro item da coluna Título. 

> Pseudocódigo com a query SELECT Titulo FROM artigos WHERE Ano = 2023

1. O DuckDB escaneia o arquivo da coluna ano. Ele carrega o vetor de números ( [ 2000, ... 2023, 2024, 2025]) e aplica um filtro sobre onde há, neste exemplo, 2023. A resposta do filtro é **0 e 2**. 

2. Agora o DuckDB sabe que precisa das posições 0 e 2. Ele vai apenas no arquivo da coluna título. Pula as posições 1 e 3, lê o que interessa e dá a resposta.

Note: Para filtrar por ano, com os nossos arquivos em gigabytes, o POSTGRES gastaria muito em texto desnecessário para chegar na coluna ano. 


## Estrututra de Dados e comunicação entre arquivos

### database.py: Arquitetura dos dados

O dabase.py é um virtual data lake. Ele caminha pela pasta data/, acha os arquivos .parquet e diz pro DuckDB quais precisamos tratar como tabela SQL sem carregar na memória. 

Nas linhas 67 até a 85 usamos glob. Se mais arquivos parquet forem adicionados (como Alysson sugeriu de mais fontes), pode demorar levar ainda mais tempo para a inicializar a API. 

### queries.py 

Aqui temos todas as queries já estruturadas pelo Dr. Alysson. Adicionamos "três categorias de peso" para explicar sobre a velocidade das consultas. 

### Categoria A: Dashboard Incial

Queries leem apenas o arquivo de eventos
- Funções: all_sources, all_events_years, all_sources_filter_years.
- Performance: < 50ms entre todas.

Essas métricas de visão geral lêem direto do disco semp precisar de pré processamento. 

### Categoria B: Os Joins Pesados (previamente estrturados)

As queries elaboradas pelo Alysson no BigQuery entram aqui. São queries complexaas com os metadados gigantescos do OpenAlex. 

- Funções: event_journals, fields_events.
- A lógica do Join: 
> ON LOWER(SUBSTRING(a.id FROM 17)) = LOWER(b.doi)

**O problema é** que o evento vem como "https://doi.org/10.1234/x", o OpenAlex só 10.12345. 
**A solução que usamos** O DuckDB corta os primeiros 16 caracteres da URL em tempo de execução para bater com o DOI.
**Trade-Off**: Gasta bem mais CPU, mas é um valor irrisório se comparado a velocidade em que é executado.

**Filtro de Qualidade**

> WHERE c.score >= 0.95

Não mostramos qualquer classificação. Sóáreas do conhecimento onde o algoritmo tem 95% ou mais de confiança.

### Categoria C: Exportação (WIP)

24/11/2025:

Modificamos o endpoint GET /all_events_data_filter_years_enriched/{ya}{yb} para retornar arquivo CSV direto para download. Anteriormente, o endpoint retornava JSON em formato colunar que precisava ser processado no cliente. Para concretizar a atualização, alteramos as chamadas no arquivo que centraliza as queries: adicionamos a função generate_csv_streaming() em queries.py (428-469). 

Também adicionamos na main.py o import do StreamingResponse, o Endpoint agora retorna StreamingResponse com media_type="text/csv" + header Content-Disposition, que faz o download automático. **Para isso, alteramos o uso do botão no frontend de JSON MAP para href simples.

Com isso, a exportação traz as colunas DOI, Timestamp, Year, Source, Prefix, Title, Publication year, Journal, Field.

Resumo:
  Tabelas consultadas: 7 (eventos + works + locations + sources + topics + fields)
  Dados escaneados: ~1.75 GB por request (Parquet)
  Tempo de processamento: 800ms - 1.5s (dependendo do range de anos)
  Rate limit: 10 requests/min (protege servidor)
  Uso de CPU: ~20% do tempo (com rate limit ativo)

  Trade-off: Query pesada no servidor, mas browser não trava e funciona em qualquer dispositivo.

- Função: all_events_data_filter_years_enriched

Essa é a função que estamos trabalhando. Por ser um pouco mais crítica, ainda é preciso cautela na implementação. Ela faz 6 Left Joins que varrem todas as tabelas. A exportação é completa e a operação mais custosa do sistema porque enriquecemos cada evento com todos os metadados disponíveis. Por esse mesmo motivo, colocamos um rate limit mais restritivo, mas os dados ainda estão indisponíveis para finalizarmos a implementação com data streaming para criação do csv -> data streaming é essencial porque, por conta do volume dos dados, esse processo se realizado no cliente pode quebrar o navegador. 

Categoria D: Busca por doi: search_dois

- Função search_dois (n12)

Ao invés de fazer um SQL maluco que retorna um JSON aninhado, optei por buscar os dados brutos no banco e montar o dicionário/JSON no python de maneira segura.

> placeholders = ', '.join(['?' for _ in normalized_dois])

**Garanti que todos os parâmetros usassem "?" para impedir qualquer tipo de SQL Injection via API**.
