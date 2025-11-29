#!/bin/bash
# Script para configurar SSL com Certbot (Let's Encrypt) - GRATUITO!
# Uso: sudo ./scripts/setup-ssl.sh

set -e

DOMAIN="libremetricas.markdev.dev"
EMAIL="marcelo@markdev.dev"

echo "=========================================="
echo "Configuração SSL com Let's Encrypt (GRATUITO)"
echo "=========================================="
echo ""
echo "Domínio: $DOMAIN"
echo "Email: $EMAIL"
echo ""
echo "IMPORTANTE: Certifique-se de que:"
echo "1. O domínio $DOMAIN aponta para o IP deste servidor"
echo "2. As portas 80 e 443 estão abertas no firewall"
echo "3. O Nginx está instalado e rodando"
echo ""

read -p "Continuar? (s/n) " -n 1 -r
echo ""
if [[ ! $REPLY =~ ^[Ss]$ ]]; then
    echo "Cancelado."
    exit 1
fi

# Verificar se está rodando como root
if [ "$EUID" -ne 0 ]; then 
    echo "ERRO: Este script precisa ser executado como root (use sudo)"
    exit 1
fi

# Instalar Certbot se não estiver instalado
if ! command -v certbot &> /dev/null; then
    echo "Instalando Certbot..."
    apt update
    apt install -y certbot python3-certbot-nginx
else
    echo "Certbot já está instalado."
fi

# Verificar se o Nginx está rodando
if ! systemctl is-active --quiet nginx; then
    echo "Iniciando Nginx..."
    systemctl start nginx
fi

# Verificar se o arquivo de configuração do Nginx existe
NGINX_CONFIG="/etc/nginx/sites-available/$DOMAIN"
if [ ! -f "$NGINX_CONFIG" ]; then
    echo "ERRO: Arquivo de configuração do Nginx não encontrado: $NGINX_CONFIG"
    echo "Copie o arquivo nginx/$DOMAIN.conf para $NGINX_CONFIG primeiro"
    exit 1
fi

# Obter certificado SSL
echo ""
echo "Obtendo certificado SSL do Let's Encrypt..."
echo "Isso pode levar alguns minutos..."
echo ""

certbot --nginx -d "$DOMAIN" --non-interactive --agree-tos --email "$EMAIL" --redirect

# Verificar renovação automática
echo ""
echo "Verificando renovação automática..."
if certbot renew --dry-run &> /dev/null; then
    echo "✓ Renovação automática configurada corretamente!"
else
    echo "⚠ Aviso: Verifique a renovação automática manualmente"
fi

# Testar configuração do Nginx
echo ""
echo "Testando configuração do Nginx..."
if nginx -t; then
    echo "✓ Configuração do Nginx está correta!"
    echo "Recarregando Nginx..."
    systemctl reload nginx
else
    echo "ERRO: Configuração do Nginx inválida!"
    exit 1
fi

echo ""
echo "=========================================="
echo "✓ SSL configurado com sucesso!"
echo "=========================================="
echo ""
echo "Seu site agora está disponível em: https://$DOMAIN"
echo ""
echo "O certificado será renovado automaticamente pelo Certbot."
echo "Para verificar: sudo certbot certificates"
echo "Para renovar manualmente: sudo certbot renew"
echo ""

