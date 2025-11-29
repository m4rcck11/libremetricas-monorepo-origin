#!/bin/bash
# Script para configurar firewall (UFW) - Alta Prioridade
# Uso: sudo ./scripts/setup-firewall.sh

set -e

echo "=========================================="
echo "Configuração de Firewall (UFW)"
echo "=========================================="
echo ""
echo "Este script irá:"
echo "1. Permitir SSH (porta 22) - IMPORTANTE!"
echo "2. Permitir HTTP (porta 80) - para Certbot"
echo "3. Permitir HTTPS (porta 443) - para o site"
echo "4. Bloquear acesso direto à porta 8000 de fora"
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

# Verificar se UFW está instalado
if ! command -v ufw &> /dev/null; then
    echo "Instalando UFW..."
    apt update
    apt install -y ufw
fi

# Resetar regras (cuidado!)
echo "Resetando regras do firewall..."
ufw --force reset

# Permitir SSH (IMPORTANTE - faça isso primeiro!)
echo "Permitindo SSH (porta 22)..."
ufw allow 22/tcp

# Permitir HTTP e HTTPS
echo "Permitindo HTTP (porta 80)..."
ufw allow 80/tcp

echo "Permitindo HTTPS (porta 443)..."
ufw allow 443/tcp

# Bloquear acesso direto à porta 8000 de fora
# (A porta 8000 só deve ser acessível via localhost, o que já está configurado no docker-compose)
echo "Bloqueando acesso direto à porta 8000..."
ufw deny 8000/tcp

# Habilitar firewall
echo ""
echo "Habilitando firewall..."
ufw --force enable

# Mostrar status
echo ""
echo "=========================================="
echo "✓ Firewall configurado!"
echo "=========================================="
echo ""
echo "Status do firewall:"
ufw status verbose
echo ""
echo "IMPORTANTE: Certifique-se de que você tem acesso SSH antes de fechar esta sessão!"
echo "Se perder acesso, você pode precisar acessar via console do servidor."
echo ""

