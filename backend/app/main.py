"""Ponto de entrada da aplicação FastAPI com backend DuckDB.

Define todos os endpoints da API REST para consultas altmétricas, incluindo agregações
por fonte, ano, periódico e área de pesquisa. Implementa padrão de injeção de dependências
para gerenciamento de conexões.

Tecnologias: FastAPI, DuckDB, slowapi (rate limiting)
"""
from fastapi import FastAPI, Depends, HTTPException, Request, Query
from fastapi.responses import JSONResponse, StreamingResponse  # Added StreamingResponse for CSV export
import duckdb
from typing import Dict, List, Any, Optional
from pydantic import BaseModel
from app.config import settings
from app.database import get_db, db_manager
from app.models import HealthResponse
from app.middleware import limiter, configure_cors, configure_rate_limiting
from app import queries


# Initialize FastAPI application
app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    debug=settings.DEBUG
)

# Configure middleware
configure_cors(app)
configure_rate_limiting(app)


# Startup/shutdown events
@app.on_event("startup")
async def startup_event():
    """Initialize database connection on startup"""
    import logging
    logger = logging.getLogger(__name__)
    try:
        logger.info("Initializing database connection...")
        _ = db_manager.get_connection()
        logger.info("Database connection initialized successfully")
    except Exception as e:
        logger.error(f"Failed to initialize database connection: {e}", exc_info=True)
        raise


@app.on_event("shutdown")
async def shutdown_event():
    """Close database connection on shutdown"""
    db_manager.close()


# Root endpoint
@app.get("/", response_model=dict)
@limiter.limit(f"{settings.RATE_LIMIT_PER_MINUTE}/minute")
async def root(request: Request):
    """Welcome message"""
    return {
        "message": f"Welcome to {settings.APP_NAME}",
        "version": settings.APP_VERSION,
        "docs": "/docs"
    }


# Health check endpoint
@app.get("/health", response_model=HealthResponse)
async def health_check():
    """Database connectivity health check"""
    is_healthy = db_manager.health_check()

    return HealthResponse(
        status="healthy" if is_healthy else "unhealthy",
        message="Database connection operational" if is_healthy else "Database connection failed",
        database_connected=is_healthy
    )


# Query endpoints (maintaining original API contract)

@app.get("/sources")
@limiter.limit(f"{settings.RATE_LIMIT_PER_MINUTE}/minute")
async def get_sources(request: Request, conn: duckdb.DuckDBPyConnection = Depends(get_db)) -> Dict[str, List[str]]:
    """Get all sources as a simple list"""
    try:
        sources_list = queries.all_sources_list(conn)
        return {"sources": sources_list}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/events_sources")
@limiter.limit(f"{settings.RATE_LIMIT_PER_MINUTE}/minute")
async def get_events_sources(
    request: Request,
    ya: Optional[int] = Query(None, description="Start year"),
    yb: Optional[int] = Query(None, description="End year"),
    conn: duckdb.DuckDBPyConnection = Depends(get_db)
) -> Dict[str, List[Any]]:
    """Get all event sources with counts, optionally filtered by year range"""
    try:
        if ya is not None and yb is not None:
            return queries.all_sources_filter_years(conn, ya, yb)
        return queries.all_events_sources(conn)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/events_years")
@limiter.limit(f"{settings.RATE_LIMIT_PER_MINUTE}/minute")
async def get_events_years(request: Request, conn: duckdb.DuckDBPyConnection = Depends(get_db)) -> Dict[str, List[Any]]:
    """Get event distribution by year"""
    try:
        return queries.all_events_years(conn)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/events_sources/{ya}/{yb}")
@limiter.limit(f"{settings.RATE_LIMIT_PER_MINUTE}/minute")
async def get_events_sources_filtered(
    request: Request,
    ya: int,
    yb: int,
    conn: duckdb.DuckDBPyConnection = Depends(get_db)
) -> Dict[str, List[Any]]:
    """Get sources filtered by year range"""
    try:
        return queries.all_sources_filter_years(conn, ya, yb)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/events_source_years/{source}")
@limiter.limit(f"{settings.RATE_LIMIT_PER_MINUTE}/minute")
async def get_events_source_years(
    request: Request,
    source: str,
    conn: duckdb.DuckDBPyConnection = Depends(get_db)
) -> Dict[str, List[Any]]:
    """Get years for specific source"""
    try:
        return queries.source_events_years(conn, source)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/source_journals/{source}")
@limiter.limit(f"{settings.RATE_LIMIT_PER_MINUTE}/minute")
async def get_source_journals(
    request: Request,
    source: str,
    conn: duckdb.DuckDBPyConnection = Depends(get_db)
) -> Dict[str, List[Any]]:
    """Get journals for specific source"""
    try:
        return queries.source_journals(conn, source)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/events_journals")
@limiter.limit(f"{settings.RATE_LIMIT_PER_MINUTE}/minute")
async def get_events_journals(request: Request, conn: duckdb.DuckDBPyConnection = Depends(get_db)) -> Dict[str, List[Any]]:
    """Get all journals with event counts"""
    try:
        return queries.events_journals(conn)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/fields_events")
@limiter.limit(f"{settings.RATE_LIMIT_PER_MINUTE}/minute")
async def get_fields_events(
    request: Request,
    ya: Optional[int] = Query(None, description="Start year"),
    yb: Optional[int] = Query(None, description="End year"),
    conn: duckdb.DuckDBPyConnection = Depends(get_db)
) -> Dict[str, List[Any]]:
    """Get research fields with event counts, optionally filtered by year range"""
    try:
        if ya is not None and yb is not None:
            return queries.fields_events_filtered(conn, ya, yb)
        return queries.fields_events(conn)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/fields_source_events/{source}")
@limiter.limit(f"{settings.RATE_LIMIT_PER_MINUTE}/minute")
async def get_fields_source_events(
    request: Request,
    source: str,
    conn: duckdb.DuckDBPyConnection = Depends(get_db)
) -> Dict[str, List[Any]]:
    """Get fields for specific source"""
    try:
        return queries.fields_source_events(conn, source)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/all_events_data_filter_years/{ya}/{yb}")
@limiter.limit(f"{settings.RATE_LIMIT_PER_MINUTE_HEAVY}/minute")
async def get_all_events_data_filtered(
    request: Request,
    ya: int,
    yb: int,
    conn: duckdb.DuckDBPyConnection = Depends(get_db)
) -> Dict[str, List[Any]]:
    """Get all event data filtered by year range (stricter rate limit)"""
    try:
        return queries.all_events_data_filter_years(conn, ya, yb)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/all_events_data_filter_years_enriched/{ya}/{yb}")
@limiter.limit(f"{settings.RATE_LIMIT_PER_MINUTE_HEAVY}/minute")
async def get_all_events_data_enriched(
    request: Request,
    ya: int,
    yb: int,
    conn: duckdb.DuckDBPyConnection = Depends(get_db)
):
    """
    Export all event data with full metadata as CSV file (direct download)
    Includes JOINs with oa_works, oa_sources, and oa_fields
    Returns CSV file with streaming to avoid browser memory issues
    """
    try:
        # Generate CSV using streaming to avoid loading all data in memory
        return StreamingResponse(
            queries.generate_csv_streaming(conn, ya, yb),
            media_type="text/csv",
            headers={
                "Content-Disposition": f"attachment; filename=altmetrics_{ya}_{yb}.csv"
            }
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/all_events_fields_events")
@limiter.limit(f"{settings.RATE_LIMIT_PER_MINUTE}/minute")
async def get_all_events_fields(request: Request, conn: duckdb.DuckDBPyConnection = Depends(get_db)) -> Dict[str, List[Any]]:
    """Get all events joined with fields"""
    try:
        return queries.all_events_fields_events(conn)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))



## Rest do DOI Search

class DOISearchRequest(BaseModel):
    """Request model for DOI search"""
    dois: List[str]


@app.post("/search_dois")
@limiter.limit(f"{settings.RATE_LIMIT_PER_MINUTE}/minute")
async def search_dois_endpoint(
    request: Request,
    search_request: DOISearchRequest,
    conn: duckdb.DuckDBPyConnection = Depends(get_db)
) -> Dict[str, Any]:
    """
    Search for DOIs and return aggregated altmetrics

    Request body:
    {
        "dois": ["10.xxx/xxx", "10.yyy/yyy", ...]
    }

    Returns structured data with events aggregated by source and year for each DOI
    """
    try:
        if not search_request.dois or len(search_request.dois) == 0:
            raise HTTPException(status_code=400, detail="Lista de DOIs não pode estar vazia")

        if len(search_request.dois) > 100:
            raise HTTPException(status_code=400, detail="Máximo de 100 DOIs por consulta")

        return queries.search_dois(conn, search_request.dois)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
