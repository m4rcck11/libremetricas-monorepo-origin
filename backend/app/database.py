"""Gerenciador de conexões DuckDB com padrão Singleton.

Responsável por inicializar conexões read-only ao banco DuckDB e registrar views temporárias
para arquivos Parquet (OpenAlex LATAM + Crossref events). Utiliza context manager para
gerenciamento seguro de recursos.

Padrão: Singleton + Dependency Injection
"""
import duckdb
from pathlib import Path
from contextlib import contextmanager
from typing import Generator
from app.config import settings


class DatabaseManager:
    """Manages DuckDB connections and table registration"""

    def __init__(self):
        self.db_path = settings.DUCKDB_PATH
        self.parquet_dir = settings.PARQUET_DIR
        self._ensure_data_directory()
        self._ensure_database_exists()
        self._connection = None

    def _ensure_data_directory(self):
        """Create data directory if it doesn't exist"""
        self.parquet_dir.mkdir(parents=True, exist_ok=True)

    def _ensure_database_exists(self):
        """Create DuckDB file if it doesn't exist (to allow read-only connections)"""
        if not self.db_path.exists():
            # Create an empty database file
            conn = duckdb.connect(str(self.db_path))
            conn.close()

    def _register_parquet_tables(self, conn: duckdb.DuckDBPyConnection):
        """Register parquet files as views in DuckDB

        Note: This uses CREATE TEMP VIEW which works in read-only mode
        since temporary views are stored in memory, not on disk.
        """
        import logging
        logger = logging.getLogger(__name__)

        # Core tables from OpenAlex LATAM
        tables = {
            "oa_works": "works_latam*.parquet",
            "oa_works_locations": "works_locations_latam*.parquet",
            "oa_works_topics": "works_topics_latam*.parquet",
            "oa_works_authorships": "works_authorships_latam*.parquet",
            "oa_authors": "authors_latam*.parquet",
            "oa_sources": "sources_latam*.parquet",
            "oa_institutions": "institutions_latam*.parquet",
            "oa_topics": "topics*.parquet",
            "oa_fields": "fields*.parquet",
            "oa_subfields": "subfields*.parquet",
            "oa_domains": "domains*.parquet",

            # Crossref events table
            "crossref_clean_events": "crossref_clean_events*.parquet",
        }

        registered_views = []
        missing_files = []

        for table_name, pattern in tables.items():
            # Check if parquet files exist (follow symlinks)
            matching_files = []
            for file_path in self.parquet_dir.glob(pattern):
                # Resolve symlinks to get actual file path
                if file_path.is_symlink():
                    resolved = file_path.resolve()
                    if resolved.exists() and resolved.is_file():
                        matching_files.append(resolved)
                        logger.debug(f"Found symlink: {file_path} -> {resolved}")
                elif file_path.is_file():
                    matching_files.append(file_path)
                    logger.debug(f"Found file: {file_path}")
            
            if not matching_files:
                missing_files.append(f"{table_name} ({pattern})")
                logger.warning(f"No parquet files found for {table_name} with pattern {pattern}")
                continue
            
            try:
                # Build file pattern for DuckDB
                if len(matching_files) == 1:
                    # Single file - use direct path (resolved if symlink)
                    file_pattern = str(matching_files[0].absolute())
                    logger.debug(f"Using single file pattern for {table_name}: {file_pattern}")
                else:
                    # Multiple files - use glob pattern
                    file_pattern = str((self.parquet_dir / pattern).absolute())
                    logger.debug(f"Using glob pattern for {table_name}: {file_pattern}")
                
                # Use CREATE TEMP VIEW which works in read-only mode
                conn.execute(f"""
                    CREATE OR REPLACE TEMP VIEW {table_name} AS
                    SELECT * FROM read_parquet('{file_pattern}')
                """)
                registered_views.append(table_name)
                logger.info(f"Registered view: {table_name} from {len(matching_files)} file(s)")
            except Exception as e:
                logger.error(f"Failed to register view {table_name}: {e}", exc_info=True)
                raise
        
        if missing_files:
            logger.warning(f"Missing parquet files for: {', '.join(missing_files)}")
        
        if not registered_views:
            raise RuntimeError("No parquet files found! Cannot create views.")
        
        logger.info(f"Successfully registered {len(registered_views)} views")

    def get_connection(self) -> duckdb.DuckDBPyConnection:
        """Get or create a DuckDB connection with views registered"""
        if self._connection is None:
            # Create connection in read-only mode to allow multiple workers
            # This prevents file lock conflicts when using multiple Gunicorn workers
            self._connection = duckdb.connect(str(self.db_path), read_only=True)

            # Performance optimizations
            self._connection.execute("PRAGMA threads=2")
            self._connection.execute("PRAGMA memory_limit='512MB'")

            # Register parquet files as views
            self._register_parquet_tables(self._connection)

        return self._connection

    @contextmanager
    def get_cursor(self) -> Generator[duckdb.DuckDBPyConnection, None, None]:
        """Context manager for query execution"""
        conn = self.get_connection()
        try:
            yield conn
        except Exception as e:
            # DuckDB auto-rollback on errors
            raise e

    def close(self):
        """Close database connection"""
        if self._connection:
            self._connection.close()
            self._connection = None

    def health_check(self) -> bool:
        """Verify database connectivity and table availability"""
        try:
            with self.get_cursor() as conn:
                # Check if at least one temporary view is accessible
                # (temporary views are created per-connection in read-only mode)
                result = conn.execute("""
                    SELECT COUNT(*) as count
                    FROM information_schema.tables
                    WHERE table_type IN ('VIEW', 'LOCAL TEMPORARY')
                """).fetchone()

                return result[0] > 0
        except Exception:
            return False


# Global database instance
db_manager = DatabaseManager()


def get_db() -> duckdb.DuckDBPyConnection:
    """Dependency injection for FastAPI routes"""
    return db_manager.get_connection()
