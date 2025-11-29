# Tools - Data Collection & Synchronization

Scripts para coleta e sincronização de dados OpenAlex LATAM do Google Cloud Storage (GCS) para o Portal de Altmetria.

## 📁 Arquivos

### Scripts Principais

- **`run_data_sync.py`** - Script não-interativo para execução automatizada (cron/systemd)
- **`collect_data_gcp.py`** - Script interativo completo com menu
- **`config.py`** - Configurações centralizadas

### Scripts de Eventos Altmétricos

- **`process_all_events.py`** - Consolida eventos de todas as fontes (Crossref + BORI)
- **`process_crossref_events.py`** - Processa eventos brutos do Crossref
- **`process_bori_events.py`** - Processa eventos brutos do BORI (Agência BORI)
- **`collect_crossref_events.py`** - Coleta eventos da API Crossref (via menu)

### Arquivos de Configuração

- **`.env.example`** - Exemplo de variáveis de ambiente
- **`altmetria-sync.service`** - Exemplo de systemd service para agendamento

---

## 🚀 Quick Start

### 🧪 Teste Local com Docker (Recomendado)

**Usar o script automatizado:**

```bash
cd backend

# Teste completo (build + run + sync)
./test_local.sh test

# Re-executar sync (testa sincronização incremental)
./test_local.sh sync

# Verificar arquivos baixados
ls -lh data/

# Limpar quando terminar
./test_local.sh clean
```

**Fluxo manual:**

```bash
# 1. Build da imagem
docker build -t altmetria-backend:latest .

# 2. Rodar container com volume
docker run -d \
  --name altmetria-test \
  -v $(pwd)/data:/app/data \
  -e GCS_BUCKET_NAME=altmetria_latam_ibict_tables \
  altmetria-backend:latest \
  sleep infinity

# 3. Executar sincronização
docker exec -it altmetria-test python tools/run_data_sync.py

# 4. Verificar resultados
docker exec altmetria-test ls -lh /app/data

# 5. Re-executar (deve pular arquivos existentes)
docker exec altmetria-test python tools/run_data_sync.py

# 6. Cleanup
docker stop altmetria-test && docker rm altmetria-test
```

### Modo Interativo (Desenvolvimento)

```bash
# Instalar dependências
pip install -r requirements.txt

# Executar menu interativo
cd backend/tools
python collect_data_gcp.py
```

### Modo Não-Interativo (Produção - VM Alibaba Cloud)

```bash
# Executar sincronização automatizada
python run_data_sync.py

# Exit codes:
# 0 = Sucesso (com ou sem novos downloads)
# 1 = Erro de configuração
# 2 = Erro no download
# 3 = Erro na validação
# 4 = Outros erros
```

---

## 🔄 Sincronização Incremental

O sistema implementa **sincronização incremental inteligente**:

### Como Funciona

1. **Lista arquivos no GCS** - Obtém lista completa de .parquet no bucket
2. **Verifica arquivos locais** - Lista arquivos em `/app/data`
3. **Calcula diferença** - Identifica apenas arquivos novos
4. **Baixa incrementalmente** - Download apenas do que falta
5. **Valida integridade** - Verifica tabelas críticas e tamanhos

### Comportamento

| Cenário | Ação |
|---------|------|
| 📂 Pasta `/app/data` não existe | Cria automaticamente e baixa tudo |
| ✅ Arquivo já existe localmente | **Pula download** (assume imutabilidade) |
| 🆕 GCS tem arquivos novos | Baixa apenas os novos |
| ⚠️ Local tem arquivos extras | **Não deleta** (preserva dados locais) |

### Exemplo de Output

``` output
==================================================
ETAPA 1: Verificação de Arquivos Locais
==================================================
Arquivos locais encontrados: 25

==================================================
ETAPA 2: Listagem de Arquivos no GCS
==================================================
Encontrados 30 arquivos .parquet

==================================================
ETAPA 3: Cálculo de Sincronização
==================================================
Total de arquivos no GCS: 30
Total de arquivos locais: 25
Arquivos novos a baixar: 5

==================================================
ETAPA 4: Download de Arquivos Novos
==================================================
Baixando authors_latam_05.parquet...
Baixando works_latam_10.parquet...
[...]
✓ Download concluído: 5 arquivo(s) baixado(s)
```

### Re-execução

Ao executar novamente sem mudanças no GCS:

``` output
==================================================
ETAPA 3: Cálculo de Sincronização
==================================================
Total de arquivos no GCS: 30
Total de arquivos locais: 30
Arquivos novos a baixar: 0

✓ Todos os arquivos já estão atualizados. Nada a baixar.
⏭️ Nenhum arquivo novo para baixar. Sistema já está sincronizado.
```

---

## ⚙️ Configuração

### Variáveis de Ambiente

Crie um arquivo `.env` no diretório `backend/` ou defina as variáveis:

```bash
# Google Cloud Storage
GCS_BUCKET_NAME=altmetria_latam_ibict_tables
GCS_FOLDER_PREFIX=

# Local de download (usa /app/data por padrão)
LOCAL_DOWNLOAD_PATH=/app/data

# Performance
CHUNK_SIZE=50000
DOWNLOAD_CHUNK_SIZE=8192
MAX_RETRIES=3
RETRY_BACKOFF=2
REQUEST_TIMEOUT=300

# Logging
LOG_LEVEL=INFO
LOG_FILE=import_biblio.log

# Limpeza automática
CLEANUP_AFTER_IMPORT=false

# MySQL (DESABILITADO POR PADRÃO)
ENABLE_MYSQL_IMPORT=false
```

### Habilitar MySQL (Opcional)

Se você quiser exportar dados para MySQL:

```bash
# Instalar dependência
pip install pymysql

# Configurar no .env
ENABLE_MYSQL_IMPORT=true
MYSQL_HOST=your-host.com
MYSQL_PORT=3306
MYSQL_DATABASE=openalex_latam
MYSQL_USER=admin
MYSQL_PASSWORD=your-password
```

---

## 🐳 Deploy na VM Alibaba Cloud (Docker)

### Arquitetura Simplificada

```
VM Alibaba Cloud
├── Docker Container: backend-api
│   ├── Porta: 8000
│   ├── Volume: /app/data (host → container)
│   └── Arquivos Parquet baixados localmente
│
└── Cron Job ou Systemd Timer
    └── Executa: docker exec backend python tools/run_data_sync.py
        Schedule: Diariamente às 2AM
```

### Passo 1: Preparar o Ambiente

```bash
# SSH na VM Alibaba
ssh user@your-vm-ip

# Criar diretório de dados no host
sudo mkdir -p /opt/altmetria/data
sudo chown $USER:$USER /opt/altmetria/data

# Clonar repositório
cd /opt/altmetria
git clone <your-repo> .
```

### Passo 2: Build da Imagem Docker

```bash
cd /opt/altmetria/backend

# Build da imagem
docker build -t altmetria-backend:latest .

# Verificar se foi criada
docker images | grep altmetria
```

### Passo 3: Executar Container com Volume

```bash
# Rodar container com volume mapeado
docker run -d \
  --name altmetria-backend \
  -p 8000:8000 \
  -v /opt/altmetria/data:/app/data \
  -e GCS_BUCKET_NAME=altmetria_latam_ibict_tables \
  -e LOG_LEVEL=INFO \
  --restart unless-stopped \
  altmetria-backend:latest

# Verificar se está rodando
docker ps | grep altmetria
docker logs altmetria-backend
```

### Passo 4: Download Inicial dos Dados

```bash
# Executar download manual pela primeira vez
docker exec -it altmetria-backend python tools/run_data_sync.py

# Verificar arquivos baixados
docker exec altmetria-backend ls -lh /app/data

# Verificar API
curl http://localhost:8000/health
curl http://localhost:8000/sources
```

### Passo 5: Agendar Sincronização Automática

#### Opção A: Cron Job (Simples)

```bash
# Editar crontab
crontab -e

# Adicionar linha (roda todo dia às 2AM)
0 2 * * * docker exec altmetria-backend python tools/run_data_sync.py >> /var/log/altmetria-sync.log 2>&1

# Salvar e verificar
crontab -l
```

#### Opção B: Systemd Timer (Recomendado)

```bash
# Criar service
sudo nano /etc/systemd/system/altmetria-sync.service
```

Conteúdo do arquivo:

```ini
[Unit]
Description=Altmetria Data Sync
After=docker.service
Requires=docker.service

[Service]
Type=oneshot
ExecStart=/usr/bin/docker exec altmetria-backend python tools/run_data_sync.py
StandardOutput=journal
StandardError=journal
SyslogIdentifier=altmetria-sync

[Install]
WantedBy=multi-user.target
```

Criar timer:

```bash
sudo nano /etc/systemd/system/altmetria-sync.timer
```

Conteúdo:

```ini
[Unit]
Description=Run Altmetria Data Sync daily at 2AM
Requires=altmetria-sync.service

[Timer]
OnCalendar=daily
OnCalendar=*-*-* 02:00:00
Persistent=true

[Install]
WantedBy=timers.target
```

Ativar:

```bash
# Recarregar systemd
sudo systemctl daemon-reload

# Habilitar e iniciar timer
sudo systemctl enable altmetria-sync.timer
sudo systemctl start altmetria-sync.timer

# Verificar status
sudo systemctl status altmetria-sync.timer
sudo systemctl list-timers | grep altmetria

# Testar execução manual
sudo systemctl start altmetria-sync.service
sudo journalctl -u altmetria-sync -f
```

---

## 🔄 Atualização e Manutenção

### Atualizar Código

```bash
cd /opt/altmetria
git pull

# Rebuild da imagem
cd backend
docker build -t altmetria-backend:latest .

# Parar container antigo
docker stop altmetria-backend
docker rm altmetria-backend

# Rodar novo container (os dados em /app/data são preservados)
docker run -d \
  --name altmetria-backend \
  -p 8000:8000 \
  -v /opt/altmetria/data:/app/data \
  -e GCS_BUCKET_NAME=altmetria_latam_ibict_tables \
  --restart unless-stopped \
  altmetria-backend:latest
```

### Atualizar Dados Manualmente

```bash
# Executar sync manualmente
docker exec altmetria-backend python tools/run_data_sync.py

# Ver logs
docker logs altmetria-backend --tail 100
```

### Verificar Espaço em Disco

```bash
# Ver espaço usado pelos dados
du -sh /opt/altmetria/data

# Ver espaço disponível
df -h /opt/altmetria

# Limpar arquivos antigos se necessário
docker exec altmetria-backend rm -rf /app/data/*.parquet
docker exec altmetria-backend python tools/run_data_sync.py
```

---

## 📊 Monitoramento

### Logs

```bash
# Logs do container
docker logs altmetria-backend -f

# Logs do systemd service
sudo journalctl -u altmetria-sync -f

# Logs de sync específicos
tail -f /var/log/altmetria-sync.log  # Se usando cron
```

### Health Checks

```bash
# Verificar API
curl http://localhost:8000/health

# Verificar dados
docker exec altmetria-backend ls -lh /app/data

# Verificar última execução do timer
sudo systemctl status altmetria-sync.timer
```

### Alertas (Opcional)

Criar script de monitoramento:

```bash
#!/bin/bash
# /opt/altmetria/scripts/check-sync.sh

LOG_FILE="/var/log/altmetria-sync.log"
WEBHOOK_URL="your-slack-webhook-url"  # Opcional

# Verificar última linha do log
if tail -1 $LOG_FILE | grep -q "SUCESSO"; then
    echo "Sync OK"
else
    echo "Sync FALHOU"
    # Enviar alerta (opcional)
    curl -X POST -H 'Content-type: application/json' \
      --data '{"text":"❌ Altmetria sync failed!"}' \
      $WEBHOOK_URL
fi
```

Agendar verificação:

```bash
# Adicionar ao cron (roda 30min após sync)
30 2 * * * /opt/altmetria/scripts/check-sync.sh
```

---

## 🔍 Troubleshooting

### Problema: Container não inicia

```bash
# Verificar logs de erro
docker logs altmetria-backend

# Verificar se a porta está disponível
sudo netstat -tlnp | grep 8000

# Verificar permissões do volume
ls -la /opt/altmetria/data
```

**Solução**: Ajustar permissões

```bash
sudo chown -R 1000:1000 /opt/altmetria/data
docker restart altmetria-backend
```

### Problema: Download muito lento

**Solução**: Aumentar timeout

```bash
docker exec altmetria-backend \
  env REQUEST_TIMEOUT=900 \
  python tools/run_data_sync.py
```

### Problema: Sem espaço em disco

```bash
# Ver uso de disco
df -h

# Limpar imagens Docker antigas
docker system prune -a

# Limpar dados antigos
docker exec altmetria-backend rm -rf /app/data/merged
```

### Problema: Dados não aparecem na API

```bash
# Verificar se arquivos existem
docker exec altmetria-backend ls -la /app/data

# Verificar se DuckDB consegue ler
docker exec altmetria-backend python -c "
import duckdb
conn = duckdb.connect(':memory:')
result = conn.execute('SELECT COUNT(*) FROM read_parquet(\"/app/data/works_latam*.parquet\")').fetchone()
print(f'Works count: {result[0]}')
"

# Reiniciar API
docker restart altmetria-backend
```

---

## 🐳 Docker Compose (Alternativa)

Para simplificar o deployment, você pode usar Docker Compose:

```yaml
# docker-compose.yml
version: '3.8'

services:
  backend:
    build: ./backend
    container_name: altmetria-backend
    ports:
      - "8000:8000"
    volumes:
      - /opt/altmetria/data:/app/data
    environment:
      - GCS_BUCKET_NAME=altmetria_latam_ibict_tables
      - LOG_LEVEL=INFO
      - ENABLE_MYSQL_IMPORT=false
    restart: unless-stopped
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8000/health"]
      interval: 30s
      timeout: 10s
      retries: 3
```

Uso:

```bash
# Subir serviço
docker-compose up -d

# Ver logs
docker-compose logs -f

# Parar
docker-compose down

# Executar sync
docker-compose exec backend python tools/run_data_sync.py
```

---

## 📋 Tabelas Esperadas

O sistema espera as seguintes tabelas do OpenAlex LATAM:

1. `authors_latam` - Autores latino-americanos
2. `works_latam` - Trabalhos acadêmicos
3. `works_locations_latam` - Localizações dos trabalhos
4. `works_authorships_latam` - Autorias
5. `works_topics_latam` - Tópicos dos trabalhos
6. `institutions_latam` - Instituições
7. `sources_latam` - Fontes de publicação
8. `topics` - Tópicos globais
9. `fields` - Campos de pesquisa
10. `subfields` - Subcampos
11. `domains` - Domínios
12. `prefixes_latam` - Prefixos de DOI
13. `prefixes_sources_latam` - Fontes por prefixo

---

## 🛡️ Segurança

### Boas Práticas

1. **Firewall**: Restrinja acesso à porta 8000 apenas de IPs confiáveis
2. **SSH**: Use chaves SSH (não senhas) para acesso à VM
3. **Docker**: Rode como usuário não-root (já configurado)
4. **Credenciais**: Nunca commite senhas (use .env)
5. **Atualizações**: Mantenha sistema e Docker atualizados

### Configurar Firewall (iptables)

```bash
# Permitir apenas conexões locais na porta 8000
sudo iptables -A INPUT -p tcp --dport 8000 -s 127.0.0.1 -j ACCEPT
sudo iptables -A INPUT -p tcp --dport 8000 -j DROP

# Salvar regras
sudo iptables-save > /etc/iptables/rules.v4
```

Ou use um reverse proxy (nginx/Cloudflare Tunnel).

---

## 🔐 Backup e Recuperação

### Backup dos Dados

```bash
# Backup manual
tar -czf altmetria-data-$(date +%Y%m%d).tar.gz /opt/altmetria/data

# Mover para storage remoto (Alibaba OSS)
ossutil cp altmetria-data-*.tar.gz oss://your-bucket/backups/

# Agendar backup semanal (cron)
0 3 * * 0 tar -czf /backup/altmetria-data-$(date +\%Y\%m\%d).tar.gz /opt/altmetria/data
```

### Recuperação

```bash
# Restaurar de backup
cd /opt/altmetria
tar -xzf altmetria-data-20250101.tar.gz

# Reiniciar container
docker restart altmetria-backend
```

---

## 📰 Processamento de Eventos BORI

A Agência BORI (Agência Bori) é uma fonte de dados de eventos altmétricos que fornece informações sobre menções de artigos científicos em notícias e mídia.

### Estrutura de Dados BORI

Os arquivos BORI devem estar em formato Parquet e conter as seguintes colunas:
- `labelDOI` - DOI do artigo (formato: `10.xxxx/xxxx`)
- `datePublished` - Data de publicação da notícia (formato ISO: `YYYY-MM-DDTHH:MM:SS+00:00`)
- `headline` - Título da notícia
- `entry-content` - Conteúdo completo
- Outras colunas opcionais

### Preparação dos Dados

1. **Colocar arquivos brutos no diretório correto:**
   ```bash
   # Os arquivos devem estar em:
   data/events/raw/BORI/*.parquet
   ```

2. **Formato esperado:**
   - Arquivos Parquet
   - Campo `labelDOI` deve conter DOIs válidos (formato `10.xxxx/xxxx`)
   - Campo `datePublished` deve estar em formato ISO

### Processamento

#### Via Menu Interativo

```bash
cd plataforma-altmetria-backend
source venv/bin/activate
python3 tools/collect_data_gcp.py
# Escolha opção 15: Processar eventos BORI
```

#### Via Script Direto

```bash
cd plataforma-altmetria-backend
source venv/bin/activate
python3 tools/process_bori_events.py
```

#### Via Docker

```bash
# Usando script helper
./scripts/run_tool.sh process_bori_events.py

# Ou diretamente
docker exec -it altmetria_api_duckdb python /app/tools/process_bori_events.py
```

### Resultado do Processamento

O script gera:
- **Arquivo processado**: `data/events/processed/bori_clean_events.parquet`
- **Formato**: Schema padrão com colunas `id`, `timestamp_`, `year`, `source_`, `prefix`
- **Filtros**: Apenas registros com DOI válido são processados

### Consolidação com Outras Fontes

Para consolidar BORI com Crossref:

```bash
python3 tools/process_all_events.py
```

Isso gerará o arquivo consolidado `data/events/consolidated/all_events.parquet` contendo eventos de todas as fontes.

### Exemplo de Saída

```
======================================================================
🔄 PROCESSAMENTO DE EVENTOS BORI
======================================================================
Arquivos encontrados: 1
Diretório: data/events/raw/BORI
Arquivo de saída: data/events/processed/bori_clean_events.parquet
======================================================================

✓ Eventos processados: 227
✓ Prefixes únicos: 37
✓ Período: 2020 - 2025
```

### Notas Importantes

- Apenas registros com `labelDOI` válido (formato `10.xxxx/xxxx`) são processados
- Registros sem DOI são ignorados
- O campo `id` é construído como `https://doi.org/{labelDOI}`
- O campo `source_` é sempre definido como `'bori'`

---

## 📚 Referências

- [Docker Documentation](https://docs.docker.com/)
- [DuckDB Documentation](https://duckdb.org/docs/)
- [OpenAlex Documentation](https://docs.openalex.org/)
- [Systemd Timers](https://www.freedesktop.org/software/systemd/man/systemd.timer.html)

---

## 🆘 Suporte

Para problemas ou dúvidas:

1. Verifique os logs (`docker logs` ou `journalctl`)
2. Consulte este README
3. Abra uma issue no repositório
4. Contate a equipe do Portal de Altmetria - IBICT

---

**Autor**: Portal de Altmetria - IBICT
**Versão**: 1.0
**Deployment**: VM Alibaba Cloud com Docker
**Última atualização**: 2025-11-06
