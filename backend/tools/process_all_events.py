#!/usr/bin/env python3
"""
Processa eventos de TODAS as fontes (Crossref + Bluesky + BORI) e gera arquivo consolidado
"""
import duckdb
import logging
from pathlib import Path
from config import Config

logger = logging.getLogger(__name__)


def process_all_events():
    """Processa eventos de todas as fontes e consolida"""
    
    print(f"\n{'='*70}")
    print(f"🔄 PROCESSAMENTO UNIFICADO DE EVENTOS")
    print(f"{'='*70}\n")
    
    conn = duckdb.connect(':memory:')
    
    try:
        sources_loaded = []
        
        # 1. Processar Crossref (se houver arquivos brutos)
        crossref_files = list(Config.CROSSREF_RAW_DIR.glob('p*_*.parquet'))
        if crossref_files:
            print(f"📊 Processando Crossref: {len(crossref_files)} arquivos brutos")
            
            if len(crossref_files) == 1:
                crossref_load = f"CREATE TABLE crossref_raw AS SELECT * FROM read_parquet('{crossref_files[0].absolute()}');"
            else:
                file_list = ','.join([f"'{f.absolute()}'" for f in crossref_files])
                crossref_load = f"CREATE TABLE crossref_raw AS SELECT * FROM read_parquet([{file_list}], union_by_name=true);"
            
            conn.execute(f"""
                {crossref_load}
                
                -- Transformar para formato limpo
                -- Estrutura real: source_id contém nome da fonte, obj_id contém URL completa do DOI
                CREATE TABLE crossref_events AS
                SELECT 
                    TRIM(obj_id, '"') AS id,
                    TRIM(occurred_at, '"') AS timestamp_,
                    CAST(SUBSTR(TRIM(occurred_at, '"'), 1, 4) AS INTEGER) AS year,
                    source_id AS source_,
                    SPLIT_PART(
                        SUBSTR(TRIM(obj_id, '"'), 17),
                        '/',
                        1
                    ) AS prefix
                FROM crossref_raw
                WHERE obj_id IS NOT NULL
                  AND occurred_at IS NOT NULL
                  AND source_id IS NOT NULL;
            """)
            
            crossref_count = conn.execute("SELECT COUNT(*) FROM crossref_events").fetchone()[0]
            print(f"   ✓ {crossref_count:,} eventos processados")
            sources_loaded.append('crossref')
        else:
            # Tentar carregar arquivo processado se existir
            if Config.CROSSREF_PROCESSED_FILE.exists():
                print(f"📊 Carregando Crossref processado")
                conn.execute(f"""
                    CREATE TABLE crossref_events AS
                    SELECT * FROM read_parquet('{Config.CROSSREF_PROCESSED_FILE.absolute()}');
                """)
                crossref_count = conn.execute("SELECT COUNT(*) FROM crossref_events").fetchone()[0]
                print(f"   ✓ {crossref_count:,} eventos carregados")
                sources_loaded.append('crossref')
        
        # 2. Processar Bluesky (se houver arquivos brutos)
        bluesky_files = list(Config.BLUESKY_RAW_DIR.glob('scientific_posts_*.parquet'))
        if bluesky_files:
            print(f"📊 Processando Bluesky: {len(bluesky_files)} arquivos brutos")
            
            try:
                # Limpar qualquer tabela anterior que possa existir
                try:
                    conn.execute("DROP TABLE IF EXISTS bluesky_raw;")
                    conn.execute("DROP TABLE IF EXISTS bluesky_events_from_doi;")
                    conn.execute("DROP TABLE IF EXISTS bluesky_with_dois;")
                    conn.execute("DROP TABLE IF EXISTS bluesky_events_from_urls;")
                    conn.execute("DROP TABLE IF EXISTS bluesky_events;")
                except:
                    pass  # Ignorar erros de limpeza
                
                # Carregar arquivo bruto (executar separadamente)
                if len(bluesky_files) == 1:
                    conn.execute(f"CREATE TABLE bluesky_raw AS SELECT * FROM read_parquet('{bluesky_files[0].absolute()}');")
                else:
                    file_list = ','.join([f"'{f.absolute()}'" for f in bluesky_files])
                    conn.execute(f"CREATE TABLE bluesky_raw AS SELECT * FROM read_parquet([{file_list}], union_by_name=true);")
                
                # Verificar se há dados
                raw_count = conn.execute("SELECT COUNT(*) FROM bluesky_raw").fetchone()[0]
                
                if raw_count == 0:
                    print("   ⚠️ Arquivo Bluesky vazio, pulando processamento")
                    conn.execute("DROP TABLE IF EXISTS bluesky_raw;")
                else:
                    # Executar cada CREATE TABLE separadamente (sem usar IF NOT EXISTS para evitar conflitos)
                    conn.execute("DROP TABLE IF EXISTS bluesky_events_from_doi;")
                    conn.execute("""
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
                    """)
                    
                    conn.execute("DROP TABLE IF EXISTS bluesky_with_dois;")
                    conn.execute("""
                        CREATE TABLE bluesky_with_dois AS
                        SELECT 
                            timestamp,
                            UNNEST(SPLIT(urls, '|')) AS url
                        FROM bluesky_raw
                        WHERE urls IS NOT NULL 
                          AND urls != ''
                          AND timestamp IS NOT NULL;
                    """)
                    
                    conn.execute("DROP TABLE IF EXISTS bluesky_events_from_urls;")
                    conn.execute("""
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
                    """)
                    
                    conn.execute("DROP TABLE IF EXISTS bluesky_events;")
                    conn.execute("""
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
                    """)
                    
                    bluesky_count = conn.execute("SELECT COUNT(*) FROM bluesky_events").fetchone()[0]
                    print(f"   ✓ {bluesky_count:,} eventos processados")
                    sources_loaded.append('bluesky')
                    
                    # Limpar tabelas temporárias
                    conn.execute("DROP TABLE IF EXISTS bluesky_raw;")
                    conn.execute("DROP TABLE IF EXISTS bluesky_events_from_doi;")
                    conn.execute("DROP TABLE IF EXISTS bluesky_with_dois;")
                    conn.execute("DROP TABLE IF EXISTS bluesky_events_from_urls;")
                    
            except Exception as e:
                print(f"   ⚠️ Erro ao processar Bluesky: {e}")
                print(f"   Pulando Bluesky e continuando apenas com Crossref")
                logger.warning(f"Erro ao processar Bluesky: {e}", exc_info=True)
                # Limpar qualquer tabela parcial
                try:
                    conn.execute("DROP TABLE IF EXISTS bluesky_raw;")
                    conn.execute("DROP TABLE IF EXISTS bluesky_events_from_doi;")
                    conn.execute("DROP TABLE IF EXISTS bluesky_with_dois;")
                    conn.execute("DROP TABLE IF EXISTS bluesky_events_from_urls;")
                    conn.execute("DROP TABLE IF EXISTS bluesky_events;")
                except:
                    pass
        else:
            # Tentar carregar arquivo processado se existir
            if Config.BLUESKY_PROCESSED_FILE.exists():
                print(f"📊 Carregando Bluesky processado")
                conn.execute(f"""
                    CREATE TABLE bluesky_events AS
                    SELECT * FROM read_parquet('{Config.BLUESKY_PROCESSED_FILE.absolute()}');
                """)
                bluesky_count = conn.execute("SELECT COUNT(*) FROM bluesky_events").fetchone()[0]
                print(f"   ✓ {bluesky_count:,} eventos carregados")
                sources_loaded.append('bluesky')
        
        # 3. Processar BORI (se houver arquivos brutos)
        bori_files = list(Config.BORI_RAW_DIR.glob('*.parquet'))
        if bori_files:
            print(f"📊 Processando BORI: {len(bori_files)} arquivos brutos")
            
            try:
                # Carregar arquivo bruto
                if len(bori_files) == 1:
                    conn.execute(f"CREATE TABLE bori_raw AS SELECT * FROM read_parquet('{bori_files[0].absolute()}');")
                else:
                    file_list = ','.join([f"'{f.absolute()}'" for f in bori_files])
                    conn.execute(f"CREATE TABLE bori_raw AS SELECT * FROM read_parquet([{file_list}], union_by_name=true);")
                
                # Verificar se há dados
                raw_count = conn.execute("SELECT COUNT(*) FROM bori_raw").fetchone()[0]
                
                if raw_count == 0:
                    print("   ⚠️ Arquivo BORI vazio, pulando processamento")
                    conn.execute("DROP TABLE IF EXISTS bori_raw;")
                else:
                    # Criar eventos a partir da coluna 'labelDOI'
                    conn.execute("""
                        CREATE TABLE bori_events AS
                        SELECT 
                            'https://doi.org/' || TRIM("labelDOI") AS id,
                            "datePublished" AS timestamp_,
                            CAST(SUBSTR("datePublished", 1, 4) AS INTEGER) AS year,
                            'bori' AS source_,
                            SPLIT_PART(TRIM("labelDOI"), '/', 1) AS prefix
                        FROM bori_raw
                        WHERE "labelDOI" IS NOT NULL 
                          AND "labelDOI" != ''
                          AND "datePublished" IS NOT NULL
                          AND "labelDOI" LIKE '10.%'
                          AND LENGTH(TRIM("labelDOI")) > 5;
                    """)
                    
                    bori_count = conn.execute("SELECT COUNT(*) FROM bori_events").fetchone()[0]
                    print(f"   ✓ {bori_count:,} eventos processados")
                    sources_loaded.append('bori')
                    
                    # Limpar tabela temporária
                    conn.execute("DROP TABLE IF EXISTS bori_raw;")
                    
            except Exception as e:
                print(f"   ⚠️ Erro ao processar BORI: {e}")
                logger.warning(f"Erro ao processar BORI: {e}", exc_info=True)
                # Limpar qualquer tabela parcial
                try:
                    conn.execute("DROP TABLE IF EXISTS bori_raw;")
                    conn.execute("DROP TABLE IF EXISTS bori_events;")
                except:
                    pass
        else:
            # Tentar carregar arquivo processado se existir
            if Config.BORI_PROCESSED_FILE.exists():
                print(f"📊 Carregando BORI processado")
                conn.execute(f"""
                    CREATE TABLE bori_events AS
                    SELECT * FROM read_parquet('{Config.BORI_PROCESSED_FILE.absolute()}');
                """)
                bori_count = conn.execute("SELECT COUNT(*) FROM bori_events").fetchone()[0]
                print(f"   ✓ {bori_count:,} eventos carregados")
                sources_loaded.append('bori')
        
        if not sources_loaded:
            print("⚠️ Nenhuma fonte de eventos encontrada")
            return False
        
        # 4. Consolidar tudo
        print(f"\n🔄 Consolidando eventos de {len(sources_loaded)} fonte(s)...")
        
        # UNION de todas as fontes disponíveis
        union_parts = []
        if 'crossref' in sources_loaded:
            union_parts.append("SELECT * FROM crossref_events")
        if 'bluesky' in sources_loaded:
            union_parts.append("SELECT * FROM bluesky_events")
        if 'bori' in sources_loaded:
            union_parts.append("SELECT * FROM bori_events")
        
        union_query = " UNION ALL ".join(union_parts)
        
        conn.execute(f"""
            CREATE TABLE all_events AS
            {union_query};
        """)
        
        # Estatísticas por fonte
        stats = conn.execute("""
            SELECT 
                source_,
                COUNT(*) as total,
                COUNT(DISTINCT prefix) as prefixes,
                MIN(year) as min_year,
                MAX(year) as max_year
            FROM all_events
            GROUP BY source_
            ORDER BY total DESC
        """).df()
        
        print("\n📊 Estatísticas por fonte:")
        print(stats.to_string(index=False))
        
        # Salvar arquivo consolidado
        output_file = Config.ALL_EVENTS_FILE
        output_file.parent.mkdir(parents=True, exist_ok=True)
        
        print("\n💾 Salvando arquivo consolidado...")
        
        conn.execute(f"""
            COPY all_events 
            TO '{output_file.absolute()}' 
            (FORMAT PARQUET, COMPRESSION 'SNAPPY')
        """)
        
        total = conn.execute("SELECT COUNT(*) FROM all_events").fetchone()[0]
        file_size_mb = output_file.stat().st_size / (1024 * 1024)
        
        # Criar link simbólico para compatibilidade com backend
        compat_file = Path(Config.LOCAL_DOWNLOAD_PATH) / "crossref_clean_events.parquet"
        try:
            if compat_file.exists() or compat_file.is_symlink():
                compat_file.unlink()
            compat_file.symlink_to(output_file.relative_to(Config.LOCAL_DOWNLOAD_PATH))
            print(f"✓ Link de compatibilidade criado: {compat_file.name}")
        except Exception as e:
            logger.warning(f"Erro ao criar link simbólico: {e}")
        
        print(f"\n{'='*70}")
        print(f"✓ CONSOLIDAÇÃO CONCLUÍDA")
        print(f"{'='*70}")
        print(f"Arquivo gerado: {output_file.name}")
        print(f"Tamanho: {file_size_mb:.2f} MB")
        print(f"Total de eventos: {total:,}")
        print(f"Fontes: {', '.join(sources_loaded)}")
        print(f"{'='*70}\n")
        
        logger.info(f"Arquivo consolidado gerado: {output_file}")
        logger.info(f"Total de eventos: {total:,}")
        
        return True
        
    except Exception as e:
        print(f"\n✗ Erro: {e}")
        logger.error(f"Erro ao processar eventos: {e}", exc_info=True)
        return False
    finally:
        conn.close()


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    process_all_events()

