"""Configuração de middlewares para rate limiting e CORS.

Implementa proteção contra abuso com slowapi (rate limiting baseado em IP) e habilita
CORS configurável para permitir requisições cross-origin do frontend.

Padrão: Middleware pattern com configuração centralizada
"""
from fastapi import Request, Response
from fastapi.middleware.cors import CORSMiddleware
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
from app.config import settings


# Initialize rate limiter
limiter = Limiter(
    key_func=get_remote_address,
    enabled=settings.RATE_LIMIT_ENABLED,
    storage_uri="memory://",  # In-memory storage (use Redis for distributed systems)
)


def add_rate_limit_headers(response: Response, limit_info: dict):
    """Add rate limit information to response headers"""
    response.headers["X-RateLimit-Limit"] = str(limit_info.get("limit", ""))
    response.headers["X-RateLimit-Remaining"] = str(limit_info.get("remaining", ""))
    response.headers["X-RateLimit-Reset"] = str(limit_info.get("reset", ""))


def configure_cors(app):
    """Configure CORS middleware"""
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.CORS_ORIGINS,
        allow_credentials=settings.CORS_ALLOW_CREDENTIALS,
        allow_methods=settings.CORS_ALLOW_METHODS,
        allow_headers=settings.CORS_ALLOW_HEADERS,
    )


def configure_rate_limiting(app):
    """Configure rate limiting"""
    app.state.limiter = limiter
    app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)
