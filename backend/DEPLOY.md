# Guia Rápido de Deploy - Prioridade Alta

## ✅ Arquivos Criados

1. **nginx/libremetricas.markdev.dev.conf** - Configuração do Nginx
2. **scripts/setup-ssl.sh** - Script para configurar SSL com Certbot (GRATUITO!)
3. **scripts/setup-firewall.sh** - Script para configurar firewall

## 🚀 Passos para Colocar a API no Ar

### 1. Configurar Firewall (PRIMEIRO!)
```bash
chmod +x scripts/setup-firewall.sh
sudo ./scripts/setup-firewall.sh
```

### 2. Instalar Nginx
```bash
sudo apt update
sudo apt install -y nginx
```

### 3. Copiar e Ativar Configuração do Nginx
```bash
sudo cp nginx/libremetricas.markdev.dev.conf /etc/nginx/sites-available/libremetricas.markdev.dev
sudo ln -s /etc/nginx/sites-available/libremetricas.markdev.dev /etc/nginx/sites-enabled/
sudo rm /etc/nginx/sites-enabled/default  # Remover config padrão
sudo nginx -t  # Testar configuração
sudo systemctl reload nginx
```

### 4. Configurar SSL com Certbot (GRATUITO!)
```bash
# IMPORTANTE: Editar o script e adicionar seu email
nano scripts/setup-ssl.sh
# Altere: EMAIL="seu-email@exemplo.com"

chmod +x scripts/setup-ssl.sh
sudo ./scripts/setup-ssl.sh
```

## ⚠️ Pré-requisitos Importantes

Antes de executar o setup-ssl.sh, certifique-se de que:
- ✅ O domínio `libremetricas.markdev.dev` aponta para o IP do servidor (DNS configurado)
- ✅ As portas 80 e 443 estão abertas no firewall
- ✅ O Nginx está instalado e rodando

## 📝 Sobre o Certbot

**SIM, o Certbot é 100% GRATUITO!** Ele usa certificados Let's Encrypt, que são:
- ✅ Completamente gratuitos
- ✅ Renovados automaticamente
- ✅ Reconhecidos por todos os navegadores
- ✅ Válidos por 90 dias (renovação automática)

## 🔍 Verificações

Após configurar tudo:
```bash
# Verificar status do Nginx
sudo systemctl status nginx

# Verificar certificados SSL
sudo certbot certificates

# Verificar firewall
sudo ufw status verbose

# Testar site
curl -I https://libremetricas.markdev.dev/health
```

## 📚 Documentação Completa

Veja o README.md para instruções detalhadas e troubleshooting.

