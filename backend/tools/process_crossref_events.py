#!/usr/bin/env python3
"""
Processa eventos brutos do Crossref e gera crossref_clean_events.parquet
Replica a lógica SQL do BigQuery usando DuckDB
"""
import duckdb
import logging
from pathlib import Path
from config import Config

logger = logging.getLogger(__name__)


def process_raw_events():
    """Processa todos os arquivos brutos e gera tabela limpa"""
    
    raw_files = list(Config.CROSSREF_RAW_DIR.glob('p*_*.parquet'))
    
    if not raw_files:
        print(f"\n⚠️ Nenhum arquivo bruto encontrado em {Config.CROSSREF_RAW_DIR}")
        logger.error(f"Nenhum arquivo bruto encontrado em {Config.CROSSREF_RAW_DIR}")
        return False
    
    print(f"\n{'='*70}")
    print(f"🔄 PROCESSAMENTO DE EVENTOS CROSSREF")
    print(f"{'='*70}")
    print(f"Arquivos brutos encontrados: {len(raw_files)}")
    print(f"Diretório: {Config.CROSSREF_RAW_DIR}")
    print(f"Arquivo processado: {Config.CROSSREF_PROCESSED_FILE}")
    print(f"Arquivo consolidado: {Config.ALL_EVENTS_FILE}")
    print(f"{'='*70}\n")
    
    logger.info(f"Processando {len(raw_files)} arquivos brutos...")
    
    conn = duckdb.connect(':memory:')
    
    try:
        print("📊 Carregando arquivos brutos...")
        # Ler todos os arquivos brutos
        # pd.json_normalize cria colunas como "obj.@id", "source.@id", etc
        if len(raw_files) == 1:
            file_pattern = f"'{raw_files[0].absolute()}'"
        else:
            file_list = ','.join([f"'{f.absolute()}'" for f in raw_files])
            file_pattern = f"[{file_list}]"
        
        # SQL que replica a lógica do BigQuery
        # Adaptado para estrutura normalizada do pandas
        # Usa union_by_name para lidar com schemas diferentes entre arquivos
        if len(raw_files) == 1:
            # Arquivo único - sem necessidade de union
            load_query = f"CREATE TABLE raw_events AS SELECT * FROM read_parquet('{raw_files[0].absolute()}');"
        else:
            # Múltiplos arquivos - usar union_by_name para schemas diferentes
            file_list = ','.join([f"'{f.absolute()}'" for f in raw_files])
            load_query = f"CREATE TABLE raw_events AS SELECT * FROM read_parquet([{file_list}], union_by_name=true);"
        
        query = f"""
            {load_query}
            
            -- Transformar para formato limpo
            -- Estrutura real: source_id contém nome da fonte, obj_id contém URL completa do DOI
            CREATE TABLE crossref_clean_events AS
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
            FROM raw_events
            WHERE obj_id IS NOT NULL
              AND occurred_at IS NOT NULL
              AND source_id IS NOT NULL;
        """
        
        conn.execute(query)
        
        # Verificar resultado
        stats = conn.execute("SELECT COUNT(*) as total FROM crossref_clean_events").fetchone()
        total_events = stats[0]
        
        print(f"✓ Eventos processados: {total_events:,}")
        logger.info(f"Eventos processados: {total_events:,}")
        
        if total_events == 0:
            print("⚠️ Nenhum evento válido encontrado após processamento")
            logger.warning("Nenhum evento válido encontrado após processamento")
            return False
        
        # Estatísticas adicionais
        sources_stats = conn.execute("SELECT COUNT(DISTINCT source_) FROM crossref_clean_events").fetchone()[0]
        years_stats = conn.execute("SELECT MIN(year), MAX(year) FROM crossref_clean_events").fetchone()
        prefixes_stats = conn.execute("SELECT COUNT(DISTINCT prefix) FROM crossref_clean_events").fetchone()[0]
        
        print(f"✓ Sources únicos: {sources_stats}")
        print(f"✓ Prefixes únicos: {prefixes_stats}")
        if years_stats[0]:
            print(f"✓ Período: {years_stats[0]} - {years_stats[1]}")
        
        print("\n💾 Salvando arquivos...")
        
        # 1. Salvar arquivo processado (por fonte)
        processed_file = Config.CROSSREF_PROCESSED_FILE
        processed_file.parent.mkdir(parents=True, exist_ok=True)
        
        conn.execute(f"""
            COPY crossref_clean_events 
            TO '{processed_file.absolute()}' 
            (FORMAT PARQUET, COMPRESSION 'SNAPPY')
        """)
        
        file_size_mb = processed_file.stat().st_size / (1024 * 1024)
        print(f"✓ Arquivo processado: {processed_file.name} ({file_size_mb:.2f} MB)")
        
        # 2. Salvar também no arquivo consolidado (para backend)
        consolidated_file = Config.ALL_EVENTS_FILE
        consolidated_file.parent.mkdir(parents=True, exist_ok=True)
        
        conn.execute(f"""
            COPY crossref_clean_events 
            TO '{consolidated_file.absolute()}' 
            (FORMAT PARQUET, COMPRESSION 'SNAPPY')
        """)
        
        consolidated_size_mb = consolidated_file.stat().st_size / (1024 * 1024)
        print(f"✓ Arquivo consolidado: {consolidated_file.name} ({consolidated_size_mb:.2f} MB)")
        
        print(f"\n{'='*70}")
        print(f"✓ PROCESSAMENTO CONCLUÍDO")
        print(f"{'='*70}")
        print(f"Total de eventos: {total_events:,}")
        print(f"Sources únicos: {sources_stats}")
        print(f"Prefixes únicos: {prefixes_stats}")
        if years_stats[0]:
            print(f"Período: {years_stats[0]} - {years_stats[1]}")
        print(f"{'='*70}\n")
        
        logger.info(f"Tabela limpa gerada: {processed_file}")
        logger.info(f"Arquivo consolidado: {consolidated_file}")
        logger.info(f"Total de eventos: {total_events:,}")
        
        # Mostrar amostra
        sample = conn.execute("SELECT * FROM crossref_clean_events LIMIT 5").df()
        logger.info(f"\nAmostra dos dados:\n{sample.to_string()}")
        
        return True
        
    except Exception as e:
        print(f"\n✗ Erro ao processar eventos: {e}")
        logger.error(f"Erro ao processar eventos: {e}", exc_info=True)
        return False
    finally:
        conn.close()


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    process_raw_events()

