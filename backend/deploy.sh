#!/bin/bash

set -e

echo "Iniciando deploy..."

# Pull latest code
echo "Atualizando codigo..."
git pull origin main

# Verificar se .env existe
if [ ! -f .env ]; then
    echo "Arquivo .env nao encontrado. Copiando de .env.example..."
    cp .env.example .env
    echo "ATENCAO: Configure as variaveis em .env antes de continuar!"
    echo "Especialmente importante: adicione o dominio de producao em CORS_ORIGINS"
    exit 1
fi

# Build e restart
echo "Buildando e reiniciando containers..."
docker compose -f docker-compose.prod.yml down
docker compose -f docker-compose.prod.yml build --no-cache
docker compose -f docker-compose.prod.yml up -d

# Limpar imagens antigas
echo "Limpando imagens antigas..."
docker image prune -f

# Verificar status
echo "Aguardando inicializacao..."
sleep 5

# Verificar health
echo "Verificando saude da aplicacao..."
if curl -f http://localhost:8000/health > /dev/null 2>&1; then
    echo "Aplicacao esta saudavel!"
else
    echo "Aplicacao nao esta respondendo corretamente"
    echo "Ultimos logs:"
    docker compose -f docker-compose.prod.yml logs --tail=50
    exit 1
fi

echo "Deploy concluido com sucesso!"
echo "Logs: docker compose -f docker-compose.prod.yml logs -f"

