#!/usr/bin/env python3
"""
Processa arquivos Parquet do BORI e gera eventos no schema padrão
Extrai DOIs do campo labelDOI e cria eventos no formato esperado
"""
import duckdb
import logging
from pathlib import Path
from config import Config

logger = logging.getLogger(__name__)


def process_bori_raw_files():
    """Processa arquivos Parquet do BORI"""
    
    # Diretório onde os arquivos BORI estão salvos
    bori_raw_dir = Config.BORI_RAW_DIR
    
    raw_files = list(bori_raw_dir.glob('*.parquet'))
    
    if not raw_files:
        print(f"\n⚠️ Nenhum arquivo do BORI encontrado em {bori_raw_dir}")
        logger.warning(f"Nenhum arquivo do BORI encontrado em {bori_raw_dir}")
        return False
    
    print(f"\n{'='*70}")
    print(f"🔄 PROCESSAMENTO DE EVENTOS BORI")
    print(f"{'='*70}")
    print(f"Arquivos encontrados: {len(raw_files)}")
    print(f"Diretório: {bori_raw_dir}")
    print(f"Arquivo de saída: {Config.BORI_PROCESSED_FILE}")
    print(f"{'='*70}\n")
    
    logger.info(f"Processando {len(raw_files)} arquivos brutos do BORI...")
    
    conn = duckdb.connect(':memory:')
    
    try:
        # Carregar todos os arquivos do BORI
        if len(raw_files) == 1:
            file_pattern = f"'{raw_files[0].absolute()}'"
        else:
            file_list = ','.join([f"'{f.absolute()}'" for f in raw_files])
            file_pattern = f"[{file_list}]"
        
        query = f"""
            -- Carregar arquivos brutos do BORI
            CREATE TABLE bori_raw AS
            SELECT * FROM read_parquet({file_pattern}, union_by_name=true);
            
            -- Criar eventos a partir da coluna 'labelDOI'
            -- labelDOI contém DOI no formato "10.xxxx/xxxx" (sem https://doi.org/)
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
        """
        
        conn.execute(query)
        
        # Verificar resultado
        stats = conn.execute("SELECT COUNT(*) as total FROM bori_events").fetchone()
        total_events = stats[0]
        
        print(f"✓ Eventos processados: {total_events:,}")
        logger.info(f"Eventos processados: {total_events:,}")
        
        if total_events == 0:
            print("⚠️ Nenhum evento válido encontrado")
            logger.warning("Nenhum evento válido encontrado após processamento")
            return False
        
        # Estatísticas adicionais
        prefixes_stats = conn.execute("SELECT COUNT(DISTINCT prefix) FROM bori_events").fetchone()[0]
        years_stats = conn.execute("SELECT MIN(year), MAX(year) FROM bori_events").fetchone()
        
        print(f"✓ Prefixes únicos: {prefixes_stats}")
        if years_stats[0]:
            print(f"✓ Período: {years_stats[0]} - {years_stats[1]}")
        
        # Mostrar amostra
        sample = conn.execute("SELECT * FROM bori_events LIMIT 5").df()
        print("\n📋 Amostra dos eventos processados:")
        print(sample.to_string(index=False))
        
        print("\n💾 Salvando arquivo processado...")
        
        # Salvar arquivo processado
        output_file = Config.BORI_PROCESSED_FILE
        output_file.parent.mkdir(parents=True, exist_ok=True)
        
        conn.execute(f"""
            COPY bori_events 
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
    process_bori_raw_files()


