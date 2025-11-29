"""Gerenciamento de configurações via variáveis de ambiente.

Centraliza todas as configurações da aplicação usando Pydantic BaseSettings, incluindo
paths do banco de dados, rate limiting, CORS e cache. Suporta arquivo .env e validação
automática de tipos.

Padrão: Settings pattern com validação Pydantic
"""
import os
import json
from pathlib import Path
from pydantic_settings import BaseSettings
from pydantic import field_validator
from typing import List, Union


class Settings(BaseSettings):
    """Application configuration from environment variables"""

    # Application
    APP_NAME: str = "Portal Altmetria API"
    APP_VERSION: str = "0.0.1"
    DEBUG: bool = False

    # Database
    DATA_DIR: Path = Path(__file__).parent.parent / "data"
    DUCKDB_PATH: Path = DATA_DIR / "analytics.duckdb"
    PARQUET_DIR: Path = DATA_DIR

    # Rate Limiting
    RATE_LIMIT_ENABLED: bool = True
    RATE_LIMIT_PER_MINUTE: int = 100
    RATE_LIMIT_PER_MINUTE_HEAVY: int = 10  # For SELECT * queries

    # CORS Configuration
    # Pode ser configurado via CORS_ORIGINS env var como JSON string ou lista separada por virgula
    # Exemplo JSON: CORS_ORIGINS=["https://libremetricas.markdev.dev","https://outro.com"]
    # Exemplo CSV: CORS_ORIGINS=https://libremetricas.markdev.dev,https://outro.com
    CORS_ORIGINS: Union[List[str], str] = [
        "http://localhost:3000",      # Next.js/React default dev port
        "http://localhost:5173",     # Vite default dev port
        "https://libremetricas.markdev.dev",  # Production frontend
        "https://portal-altmetria-frontend.vercel.app"
    ]
    
    CORS_ALLOW_CREDENTIALS: bool = True
    CORS_ALLOW_METHODS: List[str] = ["GET", "POST", "OPTIONS"]
    CORS_ALLOW_HEADERS: List[str] = ["*"]

    # Query Cache
    CACHE_ENABLED: bool = True
    CACHE_TTL_SECONDS: int = 300  # 5 minutes
    CACHE_MAX_SIZE: int = 128

    # Server
    HOST: str = "0.0.0.0"
    PORT: int = 8000
    WORKERS: int = 4

    @field_validator('CORS_ORIGINS', mode='before')
    @classmethod
    def parse_cors_origins(cls, v):
        """Parse CORS_ORIGINS from environment variable"""
        # Se ja for uma lista, retorna como esta
        if isinstance(v, list):
            return v
        
        # Se for string, tenta fazer parse
        if isinstance(v, str):
            # Tenta parse como JSON primeiro
            try:
                parsed = json.loads(v)
                if isinstance(parsed, list):
                    return parsed
            except (json.JSONDecodeError, TypeError):
                pass
            
            # Se nao for JSON valido, tenta split por virgula
            origins = [origin.strip() for origin in v.split(",") if origin.strip()]
            if origins:
                return origins
        
        # Se nao conseguir parsear, retorna valor original
        return v

    class Config:
        env_file = ".env"
        case_sensitive = True


settings = Settings()
