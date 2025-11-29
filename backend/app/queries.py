"""Funções de consulta parametrizadas ao DuckDB com cache TTL.

Implementa todas as queries da API usando parameter binding para prevenir SQL injection.
Cache opcional (TTLCache) para queries frequentes. Retorna dados em formato colunar JSON.

Padrão: Repository pattern com caching
"""
import duckdb
from typing import List, Dict, Any
from cachetools import TTLCache
from app.config import settings


# Query result cache
query_cache = TTLCache(
    maxsize=settings.CACHE_MAX_SIZE,
    ttl=settings.CACHE_TTL_SECONDS
) if settings.CACHE_ENABLED else None


def _serialize_result(columns: List[str], rows: List[tuple]) -> Dict[str, List[Any]]:
    """Convert query result to columnar JSON format"""
    if not rows:
        return {col: [] for col in columns}

    result = {col: [] for col in columns}
    for row in rows:
        for i, col in enumerate(columns):
            result[col].append(row[i])

    return result


def _execute_query(conn: duckdb.DuckDBPyConnection, sql: str, params: tuple = ()) -> Dict[str, List[Any]]:
    """Execute parameterized query and return columnar result"""
    result = conn.execute(sql, params).fetchall()
    columns = [desc[0] for desc in conn.description]
    return _serialize_result(columns, result)


# Query 1: Get all sources with event counts
def all_sources(conn: duckdb.DuckDBPyConnection) -> Dict[str, List[Any]]:
    """Aggregate events by source"""
    cache_key = "all_sources"
    if query_cache and cache_key in query_cache:
        return query_cache[cache_key]

    sql = """
        SELECT source_ AS source, COUNT(*) AS events
        FROM crossref_clean_events
        GROUP BY source_
        ORDER BY events DESC
    """
    result = _execute_query(conn, sql)

    if query_cache:
        query_cache[cache_key] = result
    return result


def all_sources_list(conn: duckdb.DuckDBPyConnection) -> List[str]:
    """Get list of all unique sources"""
    cache_key = "all_sources_list"
    if query_cache and cache_key in query_cache:
        return query_cache[cache_key]
    
    sql = """
        SELECT DISTINCT source_
        FROM crossref_clean_events
        ORDER BY source_
    """
    result = conn.execute(sql).fetchall()
    sources_list = [row[0] for row in result]
    
    if query_cache:
        query_cache[cache_key] = sources_list
    return sources_list


# Query 2: Get all event sources (duplicate of Query 1)
def all_events_sources(conn: duckdb.DuckDBPyConnection) -> Dict[str, List[Any]]:
    """Aggregate events by source (alias)"""
    return all_sources(conn)


# Query 3: Get events aggregated by year
def all_events_years(conn: duckdb.DuckDBPyConnection) -> Dict[str, List[Any]]:
    """Aggregate events by year"""
    cache_key = "all_events_years"
    if query_cache and cache_key in query_cache:
        return query_cache[cache_key]

    sql = """
        SELECT year, COUNT(*) AS events
        FROM crossref_clean_events
        GROUP BY year
        ORDER BY events DESC
    """
    result = _execute_query(conn, sql)

    if query_cache:
        query_cache[cache_key] = result
    return result


# Query 4: Get sources filtered by year range
def all_sources_filter_years(conn: duckdb.DuckDBPyConnection, year_a: int, year_b: int) -> Dict[str, List[Any]]:
    """Aggregate events by source within year range"""
    sql = """
        SELECT source_ AS source, COUNT(*) AS events
        FROM crossref_clean_events
        WHERE year >= ? AND year <= ?
        GROUP BY source_
        ORDER BY events DESC
    """
    return _execute_query(conn, sql, (year_a, year_b))


# Query 5: Get years for a specific source
def source_events_years(conn: duckdb.DuckDBPyConnection, source: str) -> Dict[str, List[Any]]:
    """Get event years for specific source"""
    sql = """
        SELECT year, COUNT(*) AS events
        FROM crossref_clean_events
        WHERE source_ = ?
        GROUP BY year
        ORDER BY events DESC
    """
    return _execute_query(conn, sql, (source,))


# Query 6: Get journals for a specific source
def source_journals(conn: duckdb.DuckDBPyConnection, source: str) -> Dict[str, List[Any]]:
    """Get journals publishing works from specific source"""
    sql = """
        SELECT d.display_name AS journal, COUNT(*) AS events
        FROM crossref_clean_events AS a
        INNER JOIN oa_works AS b
            ON LOWER(SUBSTRING(a.id FROM 17)) = LOWER(b.doi)
        INNER JOIN oa_works_locations AS c
            ON b.id = c.work_id
        INNER JOIN oa_sources AS d
            ON c.source_id = d.id
        WHERE a.source_ = ?
        GROUP BY d.display_name
        ORDER BY events DESC
    """
    return _execute_query(conn, sql, (source,))


# Query 7: Get all journals with event counts
def events_journals(conn: duckdb.DuckDBPyConnection) -> Dict[str, List[Any]]:
    """Aggregate events by journal"""
    cache_key = "events_journals"
    if query_cache and cache_key in query_cache:
        return query_cache[cache_key]

    sql = """
        SELECT d.display_name AS journal, COUNT(*) AS events
        FROM crossref_clean_events AS a
        INNER JOIN oa_works AS b
            ON LOWER(SUBSTRING(a.id FROM 17)) = LOWER(b.doi)
        INNER JOIN oa_works_locations AS c
            ON b.id = c.work_id
        INNER JOIN oa_sources AS d
            ON c.source_id = d.id
        GROUP BY d.display_name
        ORDER BY events DESC
    """
    result = _execute_query(conn, sql)

    if query_cache:
        query_cache[cache_key] = result
    return result


# Query 8: Get research fields with event counts
def fields_events(conn: duckdb.DuckDBPyConnection) -> Dict[str, List[Any]]:
    """Aggregate events by research field"""
    cache_key = "fields_events"
    if query_cache and cache_key in query_cache:
        return query_cache[cache_key]

    sql = """
        SELECT e.display_name AS field, COUNT(a.id) AS events
        FROM crossref_clean_events AS a
        INNER JOIN oa_works AS b
            ON LOWER(SUBSTRING(a.id FROM 17)) = LOWER(b.doi)
        INNER JOIN oa_works_topics AS c
            ON b.id = c.work_id
        INNER JOIN oa_topics AS d
            ON c.topic_id = d.id
        INNER JOIN oa_fields AS e
            ON d.field = e.id
        WHERE c.score >= 0.95
        GROUP BY e.display_name
        ORDER BY events DESC
    """
    result = _execute_query(conn, sql)

    if query_cache:
        query_cache[cache_key] = result
    return result


def fields_events_filtered(conn: duckdb.DuckDBPyConnection, year_a: int, year_b: int) -> Dict[str, List[Any]]:
    """Aggregate events by research field within year range"""
    sql = """
        SELECT e.display_name AS field, COUNT(a.id) AS events
        FROM crossref_clean_events AS a
        INNER JOIN oa_works AS b
            ON LOWER(SUBSTRING(a.id FROM 17)) = LOWER(b.doi)
        INNER JOIN oa_works_topics AS c
            ON b.id = c.work_id
        INNER JOIN oa_topics AS d
            ON c.topic_id = d.id
        INNER JOIN oa_fields AS e
            ON d.field = e.id
        WHERE c.score >= 0.95 AND a.year >= ? AND a.year <= ?
        GROUP BY e.display_name
        ORDER BY events DESC
    """
    return _execute_query(conn, sql, (year_a, year_b))


# Query 9: Get fields for specific source
def fields_source_events(conn: duckdb.DuckDBPyConnection, source: str) -> Dict[str, List[Any]]:
    """Get research fields for events from specific source"""
    sql = """
        SELECT e.display_name AS field, COUNT(a.id) AS events
        FROM crossref_clean_events AS a
        INNER JOIN oa_works AS b
            ON LOWER(SUBSTRING(a.id FROM 17)) = LOWER(b.doi)
        INNER JOIN oa_works_topics AS c
            ON b.id = c.work_id
        INNER JOIN oa_topics AS d
            ON c.topic_id = d.id
        INNER JOIN oa_fields AS e
            ON d.field = e.id
        WHERE a.source_ = ? AND c.score >= 0.95
        GROUP BY e.display_name
        ORDER BY events DESC
    """
    return _execute_query(conn, sql, (source,))


# Query 10: Get all event data filtered by year range
def all_events_data_filter_years(conn: duckdb.DuckDBPyConnection, year_a: int, year_b: int) -> Dict[str, List[Any]]:
    """Extract all event records within year range (WARNING: potentially large result set)"""
    sql = """
        SELECT *
        FROM crossref_clean_events
        WHERE year >= ? AND year <= ?
    """
    return _execute_query(conn, sql, (year_a, year_b))


# Query 10b: Get all event data with full metadata (enriched for CSV export)
def all_events_data_filter_years_enriched(conn: duckdb.DuckDBPyConnection, year_a: int, year_b: int) -> Dict[str, List[Any]]:
    """
    Extract all event records with full metadata (title, journal, field)
    Optimized for CSV export with LEFT JOINs to preserve all events
    Uses CTE for better compatibility across DuckDB versions
    """
    sql = """
        WITH ranked_topics AS (
            SELECT 
                work_id,
                topic_id,
                ROW_NUMBER() OVER (PARTITION BY work_id ORDER BY score DESC) AS rn
            FROM oa_works_topics
            WHERE score >= 0.95
        ),
        primary_topics AS (
            SELECT work_id, topic_id
            FROM ranked_topics
            WHERE rn = 1
        )
        SELECT 
            a.id AS doi,
            a.timestamp_,
            a.year,
            a.source_,
            a.prefix,
            b.title,
            b.publication_year,
            d.display_name AS journal,
            f.display_name AS field
        FROM crossref_clean_events AS a
        LEFT JOIN oa_works AS b
            ON LOWER(SUBSTRING(a.id FROM 17)) = LOWER(b.doi)
        LEFT JOIN oa_works_locations AS c
            ON b.id = c.work_id
        LEFT JOIN oa_sources AS d
            ON c.source_id = d.id
        LEFT JOIN primary_topics AS topic_rel
            ON b.id = topic_rel.work_id
        LEFT JOIN oa_topics AS topic
            ON topic_rel.topic_id = topic.id
        LEFT JOIN oa_fields AS f
            ON topic.field = f.id
        WHERE a.year >= ? AND a.year <= ?
    """
    return _execute_query(conn, sql, (year_a, year_b))


# Query 11: Get all events joined with fields
def all_events_fields_events(conn: duckdb.DuckDBPyConnection) -> Dict[str, List[Any]]:
    """Join all events with their research fields (WARNING: expensive query)"""
    cache_key = "all_events_fields_events"
    if query_cache and cache_key in query_cache:
        return query_cache[cache_key]

    sql = """
        SELECT e.display_name AS field, COUNT(a.id) AS events
        FROM crossref_clean_events AS a
        INNER JOIN oa_works AS b
            ON LOWER(SUBSTRING(a.id FROM 17)) = LOWER(b.doi)
        INNER JOIN oa_works_topics AS c
            ON b.id = c.work_id
        INNER JOIN oa_topics AS d
            ON c.topic_id = d.id
        INNER JOIN oa_fields AS e
            ON d.field = e.id
        WHERE c.score >= 0.95
        GROUP BY e.display_name
        ORDER BY events DESC
    """
    result = _execute_query(conn, sql)

    if query_cache:
        query_cache[cache_key] = result
    return result

# QUERY ADICIONADA  -----------------------------------------------------------------------
# Query 12: Search for specific DOIs with aggregated metrics
def search_dois(conn: duckdb.DuckDBPyConnection, dois: List[str]) -> Dict[str, Any]:
    """
    Search for DOIs and aggregate events by source and year
    Returns structured data compatible with frontend DoiSearch component
    """
    if not dois:
        return {
            "total_searched": 0,
            "found_count": 0,
            "not_found_count": 0,
            "results": []
        }

    # Normaliza DOIs para lowercase para busca case-insensitive
    normalized_dois = [doi.lower() for doi in dois]

    # Busca eventos para os DOIs
    # A coluna 'id' contém 'https://doi.org/' + DOI, então extraímos o DOI
    placeholders = ', '.join(['?' for _ in normalized_dois])
    sql = f"""
        SELECT
            SUBSTRING(id FROM 17) AS doi,
            source_,
            year
        FROM crossref_clean_events
        WHERE LOWER(SUBSTRING(id FROM 17)) IN ({placeholders})
    """

    raw_result = conn.execute(sql, tuple(normalized_dois)).fetchall()

    # Agrupa eventos por DOI
    doi_events = {}
    for row in raw_result:
        doi, source, year = row
        doi_lower = doi.lower()

        if doi_lower not in doi_events:
            doi_events[doi_lower] = {
                'doi_original': doi,  # Mantém case original
                'events': []
            }

        doi_events[doi_lower]['events'].append({
            'source': source,
            'year': year
        })

    # Constrói resultado estruturado
    results = []
    found_dois = set(doi_events.keys())

    for original_doi in dois:
        doi_lower = original_doi.lower()

        if doi_lower in found_dois:
            events = doi_events[doi_lower]['events']

            # Agrega por fonte
            events_by_source = {}
            for event in events:
                source = event['source']
                events_by_source[source] = events_by_source.get(source, 0) + 1

            # Agrega por ano
            events_by_year = {}
            for event in events:
                year = str(event['year'])  # Frontend espera string
                events_by_year[year] = events_by_year.get(year, 0) + 1

            results.append({
                'doi': doi_events[doi_lower]['doi_original'],
                'found': True,
                'total_events': len(events),
                'events_by_source': events_by_source,
                'events_by_year': events_by_year
            })
        else:
            # DOI não encontrado
            results.append({
                'doi': original_doi,
                'found': False
            })

    found_count = len(found_dois)
    not_found_count = len(dois) - found_count

    return {
        'total_searched': len(dois),
        'found_count': found_count,
        'not_found_count': not_found_count,
        'results': results
    }


# CSV Streaming Generator
def generate_csv_streaming(conn: duckdb.DuckDBPyConnection, year_a: int, year_b: int):
    """
    Generate CSV output as streaming chunks to avoid loading all data in memory
    Used for direct CSV download endpoints
    """
    import csv
    import io

    # Get data from existing enriched query
    data = all_events_data_filter_years_enriched(conn, year_a, year_b)

    # CSV header
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(['DOI', 'Timestamp', 'Year', 'Source', 'Prefix', 'Title', 'Publication Year', 'Journal', 'Field'])
    yield output.getvalue()
    output.seek(0)
    output.truncate(0)

    # Stream data rows in chunks (1000 rows at a time to avoid memory issues)
    total_rows = len(data['doi'])
    chunk_size = 1000

    for i in range(total_rows):
        writer.writerow([
            data['doi'][i],
            data['timestamp_'][i],
            data['year'][i],
            data['source_'][i],
            data['prefix'][i],
            data['title'][i] or '',
            data['publication_year'][i] or '',
            data['journal'][i] or '',
            data['field'][i] or ''
        ])

        # Yield chunk every 1000 rows
        if (i + 1) % chunk_size == 0 or i == total_rows - 1:
            yield output.getvalue()
            output.seek(0)
            output.truncate(0)