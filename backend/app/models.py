"""Modelos Pydantic para validação de requisições e respostas da API.

Define schemas de resposta incluindo HealthResponse, ColumnarResponse e RateLimitInfo.
Garante contrato de API consistente com validação automática de tipos.

Padrão: Data Transfer Objects (DTOs)
"""
from pydantic import BaseModel
from typing import List, Any, Dict


class HealthResponse(BaseModel):
    """Health check endpoint response"""
    status: str
    message: str
    database_connected: bool


class ColumnarResponse(BaseModel):
    """Generic columnar response format (matches existing API contract)"""
    class Config:
        # Allow arbitrary field names (column names from queries)
        extra = "allow"

    def __init__(self, **data):
        super().__init__(**data)


class RateLimitInfo(BaseModel):
    """Rate limit information in response headers"""
    limit: int
    remaining: int
    reset: int
