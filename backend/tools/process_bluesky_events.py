#!/usr/bin/env python3
"""
Processa arquivos Parquet do Bluesky e gera eventos no schema padrão
Um post pode ter múltiplos DOIs, então cria um evento por DOI
"""
import duckdb
import logging
from pathlib import Path
from config import Config

logger = logging.getLogger(__name__)


def process_bluesky_raw_files():
    """Processa todos os arquivos Parquet do Bluesky"""
    
    # Diretório onde o código do Bluesky salva os arquivos
    bluesky_raw_dir = Config.BLUESKY_RAW_DIR
    
    raw_files = list(bluesky_raw_dir.glob('scientific_posts_*.parquet'))
    
    if not raw_files:
        print(f"\n⚠️ Nenhum arquivo do Bluesky encontrado em {bluesky_raw_dir}")
        logger.warning(f"Nenhum arquivo do Bluesky encontrado em {bluesky_raw_dir}")
        return False
    
    print(f"\n{'='*70}")
    print(f"🔄 PROCESSAMENTO DE EVENTOS BLUESKY")
    print(f"{'='*70}")
    print(f"Arquivos encontrados: {len(raw_files)}")
    print(f"Diretório: {bluesky_raw_dir}")
    print(f"Arquivo de saída: {Config.BLUESKY_PROCESSED_FILE}")
    print(f"{'='*70}\n")
    
    logger.info(f"Processando {len(raw_files)} arquivos brutos do Bluesky...")
    
    conn = duckdb.connect(':memory:')
    
    try:
        # Carregar todos os arquivos do Bluesky
        if len(raw_files) == 1:
            file_pattern = f"'{raw_files[0].absolute()}'"
        else:
            file_list = ','.join([f"'{f.absolute()}'" for f in raw_files])
            file_pattern = f"[{file_list}]"
        
        query = f"""
            -- Carregar arquivos brutos do Bluesky
            CREATE TABLE bluesky_raw AS
            SELECT * FROM read_parquet({file_pattern}, union_by_name=true);
            
            -- Criar eventos a partir da coluna 'doi' (se existir e estiver preenchida)
            CREATE TABLE bluesky_events_from_doi AS
            SELECT 
                'https://doi.org/' || TRIM(doi) AS id,
                timestamp AS timestamp_,
                CAST(SUBSTR(timestamp, 1, 4) AS INTEGER) AS year,
                'bluesky' AS source_,
                SPLIT_PART(TRIM(doi), '/', 1) AS prefix
            FROM bluesky_raw
            WHERE doi IS NOT NULL 
              AND doi != ''
              AND timestamp IS NOT NULL
              AND doi LIKE '10.%';
            
            -- Extrair DOIs das URLs (pode ter múltiplos DOIs por post)
            -- URLs estão separadas por '|' e podem conter doi.org/10.xxxx/xxxx
            CREATE TABLE bluesky_with_dois AS
            SELECT 
                timestamp,
                UNNEST(SPLIT(urls, '|')) AS url
            FROM bluesky_raw
            WHERE urls IS NOT NULL 
              AND urls != ''
              AND timestamp IS NOT NULL;
            
            -- Criar eventos a partir das URLs (apenas se não tiver coluna doi ou se doi estiver vazio)
            CREATE TABLE bluesky_events_from_urls AS
            SELECT 
                'https://doi.org/' || TRIM(doi_part) AS id,
                timestamp AS timestamp_,
                CAST(SUBSTR(timestamp, 1, 4) AS INTEGER) AS year,
                'bluesky' AS source_,
                SPLIT_PART(TRIM(doi_part), '/', 1) AS prefix
            FROM (
                SELECT 
                    timestamp,
                    CASE 
                        WHEN url LIKE '%doi.org/10.%' THEN
                            SUBSTR(url, POSITION('doi.org/' IN url) + 8)
                        WHEN url LIKE '%/10.%' THEN
                            SUBSTR(
                                url,
                                POSITION('/10.' IN url) + 1,
                                CASE 
                                    WHEN POSITION('?' IN SUBSTR(url, POSITION('/10.' IN url))) > 0 THEN
                                        POSITION('?' IN SUBSTR(url, POSITION('/10.' IN url))) - 1
                                    WHEN POSITION('#' IN SUBSTR(url, POSITION('/10.' IN url))) > 0 THEN
                                        POSITION('#' IN SUBSTR(url, POSITION('/10.' IN url))) - 1
                                    WHEN POSITION(' ' IN SUBSTR(url, POSITION('/10.' IN url))) > 0 THEN
                                        POSITION(' ' IN SUBSTR(url, POSITION('/10.' IN url))) - 1
                                    ELSE LENGTH(url) - POSITION('/10.' IN url)
                                END
                            )
                        ELSE NULL
                    END AS doi_part
                FROM bluesky_with_dois
                WHERE url LIKE '%/10.%'
            )
            WHERE doi_part IS NOT NULL
              AND doi_part LIKE '10.%'
              AND LENGTH(doi_part) > 5;
            
            -- Consolidar eventos: priorizar coluna doi, depois URLs
            -- Remover duplicatas mantendo apenas eventos únicos por (id, timestamp_)
            CREATE TABLE bluesky_events AS
            SELECT DISTINCT
                id,
                timestamp_,
                year,
                source_,
                prefix
            FROM (
                SELECT * FROM bluesky_events_from_doi
                UNION ALL
                SELECT * FROM bluesky_events_from_urls
            );
        """
        
        conn.execute(query)
        
        # Verificar resultado
        stats = conn.execute("SELECT COUNT(*) as total FROM bluesky_events").fetchone()
        total_events = stats[0]
        
        print(f"✓ Eventos processados: {total_events:,}")
        logger.info(f"Eventos processados: {total_events:,}")
        
        if total_events == 0:
            print("⚠️ Nenhum evento válido encontrado")
            logger.warning("Nenhum evento válido encontrado após processamento")
            return False
        
        # Estatísticas
        prefixes_stats = conn.execute("SELECT COUNT(DISTINCT prefix) FROM bluesky_events").fetchone()[0]
        years_stats = conn.execute("SELECT MIN(year), MAX(year) FROM bluesky_events").fetchone()
        
        print(f"✓ Prefixes únicos: {prefixes_stats}")
        if years_stats[0]:
            print(f"✓ Período: {years_stats[0]} - {years_stats[1]}")
        
        print("\n💾 Salvando arquivo processado...")
        
        # Salvar arquivo processado
        output_file = Config.BLUESKY_PROCESSED_FILE
        output_file.parent.mkdir(parents=True, exist_ok=True)
        
        conn.execute(f"""
            COPY bluesky_events 
            TO '{output_file.absolute()}' 
            (FORMAT PARQUET, COMPRESSION 'SNAPPY')
        """)
        
        file_size_mb = output_file.stat().st_size / (1024 * 1024)
        
        print(f"\n{'='*70}")
        print(f"✓ PROCESSAMENTO CONCLUÍDO")
        print(f"{'='*70}")
        print(f"Arquivo gerado: {output_file.name}")
        print(f"Tamanho: {file_size_mb:.2f} MB")
        print(f"Total de eventos: {total_events:,}")
        print(f"Prefixes únicos: {prefixes_stats}")
        if years_stats[0]:
            print(f"Período: {years_stats[0]} - {years_stats[1]}")
        print(f"{'='*70}\n")
        
        logger.info(f"Arquivo processado gerado: {output_file}")
        logger.info(f"Total de eventos: {total_events:,}")
        
        return True
        
    except Exception as e:
        print(f"\n✗ Erro ao processar eventos: {e}")
        logger.error(f"Erro ao processar eventos: {e}", exc_info=True)
        return False
    finally:
        conn.close()


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    process_bluesky_raw_files()

