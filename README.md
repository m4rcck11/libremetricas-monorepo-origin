# LibreMétricas - Monorepo IBICT

Plataforma de Altmetria para América Latina desenvolvida pelo Instituto Brasileiro de Informação em Ciência e Tecnologia (IBICT).

## 📚 Sobre o Projeto

LibreMétricas é uma plataforma open-source para análise e visualização de métricas alternativas (altmetria) de produção científica da América Latina, integrando dados do OpenAlex LATAM com eventos altmétricos de múltiplas fontes.

## 🏗️ Estrutura do Monorepo

```
libremetricas-ibict-monorepo/
├── backend/          # API FastAPI + Scripts de sincronização de dados
├── frontend/         # Interface web (a adicionar)
├── docs/            # Documentação geral do projeto
└── README.md        # Este arquivo
```

## 🚀 Quick Start

### Backend

O backend é uma API FastAPI que utiliza DuckDB para consultas analíticas sobre dados Parquet.

**Documentação completa:**
- [Backend README](backend/README.md) - Documentação da API
- [Tools README](backend/tools/README.md) - Scripts de sincronização e processamento

**Início rápido com Docker:**
```bash
cd backend
docker-compose up
```

A API estará disponível em `http://localhost:8000`

### Frontend

_Em desenvolvimento - a ser adicionado_

## 🛠️ Tecnologias

### Backend
- **Framework:** FastAPI 0.104.1
- **Banco de Dados:** DuckDB 0.9.2 (analítico)
- **Formato de Dados:** Apache Parquet
- **Servidor:** Gunicorn + Uvicorn
- **Deploy:** Docker, Alibaba Cloud

### Fontes de Dados
- **OpenAlex LATAM:** Dados bibliográficos da América Latina
- **Crossref Event Data:** Eventos altmétricos
- **BORI:** Menções em mídia (Agência BORI)

## 📊 Funcionalidades

- ✅ API REST para consulta de dados bibliométricos
- ✅ Agregação de eventos altmétricos de múltiplas fontes
- ✅ Export de dados em CSV via streaming
- ✅ Cache de queries para performance
- ✅ Rate limiting configurável
- ✅ Sincronização automática com Google Cloud Storage

## 🔧 Configuração

O projeto utiliza variáveis de ambiente para configuração. Veja:
- [`backend/.env.example`](backend/.env.example) - Todas as variáveis documentadas

## 📖 Documentação

- [Documentação da API](backend/README.md)
- [Scripts de Processamento](backend/tools/README.md)
- [Deploy](backend/DEPLOY.md)
- [Changelog](backend/CHANGELOG)

## 🤝 Contribuindo

Este é um projeto do IBICT. Para contribuir:

1. Fork o repositório
2. Crie uma branch para sua feature (`git checkout -b feature/MinhaFeature`)
3. Commit suas mudanças (`git commit -m 'feat: adiciona MinhaFeature'`)
4. Push para a branch (`git push origin feature/MinhaFeature`)
5. Abra um Pull Request

## 📝 Licença

[A definir]

## 🏛️ Créditos

Desenvolvido pelo **Instituto Brasileiro de Informação em Ciência e Tecnologia (IBICT)**

---

**Versão:** 0.1
**Status:** Em desenvolvimento ativo
