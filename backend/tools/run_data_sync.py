#!/usr/bin/env python3
"""
Script Não-Interativo para Sincronização Incremental de Dados OpenAlex LATAM
Baixa apenas arquivos novos do GCS (sincronização incremental)

Autor: Portal de Altmetria - Ibict
Versão: 1.1 Incremental Sync
"""

import sys
import logging
import time
from pathlib import Path
from typing import Dict, List, Set, Tuple

# Importações locais
try:
    from collect_data_gcp import GCSDownloader, LocalFileManager
    from config import Config, EXPECTED_TABLES
except ImportError as e:
    print(f"Erro ao importar módulos: {e}")
    print("Execute este script a partir do diretório tools/")
    sys.exit(1)


# ========================================
# Configuração de Logging para ECS
# ========================================

def setup_logging():
    """Configura logging estruturado para CloudWatch"""
    logging.basicConfig(
        level=getattr(logging, Config.LOG_LEVEL.upper()),
        format='%(asctime)s - %(levelname)s - %(name)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S',
        handlers=[
            logging.StreamHandler(sys.stdout),  # CloudWatch captura stdout
            logging.FileHandler(Config.LOG_FILE, encoding='utf-8')
        ]
    )
    return logging.getLogger(__name__)


logger = setup_logging()


# ========================================
# Sincronização Incremental
# ========================================

def get_local_files_set(download_path: Path) -> Set[str]:
    """
    Retorna set com nomes de arquivos .parquet existentes localmente

    Args:
        download_path: Caminho do diretório de dados

    Returns:
        Set com nomes de arquivos (ex: {'works_latam_0.parquet', ...})
    """
    if not download_path.exists():
        logger.info(f"Diretório {download_path} não existe. Será criado.")
        download_path.mkdir(parents=True, exist_ok=True)
        return set()

    local_files = set()
    for file_path in download_path.glob("*.parquet"):
        local_files.add(file_path.name)

    logger.info(f"Arquivos locais encontrados: {len(local_files)}")
    return local_files


def calculate_sync_stats(gcs_files: List[str], local_files: Set[str]) -> Tuple[Set[str], int, int]:
    """
    Calcula estatísticas de sincronização

    Args:
        gcs_files: Lista de arquivos no GCS
        local_files: Set de arquivos locais

    Returns:
        Tupla (files_to_download, total_gcs, total_local)
    """
    gcs_files_set = {Path(f['name']).name for f in gcs_files}
    files_to_download = gcs_files_set - local_files

    logger.info("=" * 70)
    logger.info("ESTATÍSTICAS DE SINCRONIZAÇÃO")
    logger.info("=" * 70)
    logger.info(f"Total de arquivos no GCS: {len(gcs_files_set)}")
    logger.info(f"Total de arquivos locais: {len(local_files)}")
    logger.info(f"Arquivos novos a baixar: {len(files_to_download)}")

    if len(local_files) > len(gcs_files_set):
        extra_local = len(local_files) - len(gcs_files_set)
        logger.warning(f"⚠️  {extra_local} arquivos locais a mais que no GCS (não serão deletados)")

    if len(files_to_download) == 0:
        logger.info("✓ Todos os arquivos já estão atualizados. Nada a baixar.")

    return files_to_download, len(gcs_files_set), len(local_files)


# ========================================
# Validação de Dados
# ========================================

def validate_downloaded_files(files_by_table: Dict[str, List[Path]]) -> bool:
    """
    Valida arquivos baixados contra tabelas esperadas

    Returns:
        bool: True se validação passou, False caso contrário
    """
    logger.info("Validando arquivos baixados...")

    downloaded_tables = set(files_by_table.keys())
    expected_tables = set(EXPECTED_TABLES)

    # Verificar tabelas faltantes
    missing_tables = expected_tables - downloaded_tables
    if missing_tables:
        logger.warning(f"Tabelas faltantes: {', '.join(missing_tables)}")

    # Verificar tabelas extras (não esperadas)
    extra_tables = downloaded_tables - expected_tables
    if extra_tables:
        logger.info(f"Tabelas extras encontradas: {', '.join(extra_tables)}")

    # Verificar se todas as tabelas críticas estão presentes
    critical_tables = {'works_latam', 'authors_latam', 'institutions_latam', 'sources_latam'}
    missing_critical = critical_tables - downloaded_tables

    if missing_critical:
        logger.error(f"Tabelas críticas faltando: {', '.join(missing_critical)}")
        return False

    # Verificar integridade dos arquivos (tamanho > 0)
    for table_name, files in files_by_table.items():
        for file_path in files:
            if file_path.stat().st_size == 0:
                logger.error(f"Arquivo vazio detectado: {file_path}")
                return False
            logger.debug(f"{table_name}: {file_path.name} ({file_path.stat().st_size / 1024 / 1024:.2f} MB)")

    total_files = sum(len(files) for files in files_by_table.values())
    total_size_mb = sum(
        f.stat().st_size for files in files_by_table.values() for f in files
    ) / 1024 / 1024

    logger.info(f"✓ Validação concluída: {len(files_by_table)} tabelas, {total_files} arquivos, {total_size_mb:.2f} MB")
    return True


# ========================================
# Função Principal
# ========================================

def main():
    """
    Execução principal não-interativa

    Exit codes:
        0: Sucesso
        1: Erro de configuração
        2: Erro no download
        3: Erro na validação
        4: Outros erros
    """
    start_time = time.time()

    logger.info("=" * 70)
    logger.info("Iniciando sincronização de dados OpenAlex LATAM")
    logger.info("=" * 70)

    try:
        # 1. Validar configurações
        logger.info("Validando configurações...")
        Config.validate()
        logger.info(f"✓ GCS Bucket: {Config.GCS_BUCKET_NAME}")
        logger.info(f"✓ Download path: {Config.LOCAL_DOWNLOAD_PATH}")

        # 2. Listar arquivos locais existentes
        download_path = Path(Config.LOCAL_DOWNLOAD_PATH)
        logger.info("\n" + "=" * 70)
        logger.info("ETAPA 1: Verificação de Arquivos Locais")
        logger.info("=" * 70)

        local_files = get_local_files_set(download_path)

        # 3. Listar arquivos no GCS
        logger.info("\n" + "=" * 70)
        logger.info("ETAPA 2: Listagem de Arquivos no GCS")
        logger.info("=" * 70)

        downloader = GCSDownloader()
        gcs_files = downloader.list_parquet_files()

        if not gcs_files:
            logger.error("Nenhum arquivo .parquet encontrado no GCS")
            return 2

        # 4. Calcular diferença (sincronização incremental)
        logger.info("\n" + "=" * 70)
        logger.info("ETAPA 3: Cálculo de Sincronização")
        logger.info("=" * 70)

        files_to_download, total_gcs, total_local = calculate_sync_stats(gcs_files, local_files)

        # 5. Baixar apenas arquivos novos
        if len(files_to_download) > 0:
            logger.info("\n" + "=" * 70)
            logger.info("ETAPA 4: Download de Arquivos Novos")
            logger.info("=" * 70)

            # Filtrar apenas arquivos que precisam ser baixados
            files_to_download_list = [f for f in gcs_files if Path(f['name']).name in files_to_download]

            downloaded_count = 0
            for file_info in files_to_download_list:
                try:
                    downloader.download_file(file_info['name'], show_progress=True)
                    downloaded_count += 1
                except Exception as e:
                    logger.error(f"Erro ao baixar {file_info['name']}: {e}")

            logger.info(f"✓ Download concluído: {downloaded_count} arquivo(s) baixado(s)")
        else:
            logger.info("\n⏭️  Nenhum arquivo novo para baixar. Sistema já está sincronizado.")

        # 6. Validação dos dados locais
        logger.info("\n" + "=" * 70)
        logger.info("ETAPA 5: Validação de Dados")
        logger.info("=" * 70)

        file_manager = LocalFileManager()
        files_by_table = file_manager.list_local_files()

        if not validate_downloaded_files(files_by_table):
            logger.error("Validação de dados falhou")
            return 3

        # 7. Resumo final
        logger.info("\n" + "=" * 70)
        logger.info("ETAPA 6: Resumo Final")
        logger.info("=" * 70)

        logger.info("Arquivos locais prontos para uso:")
        for table_name, files in sorted(files_by_table.items()):
            size_mb = sum(f.stat().st_size for f in files) / 1024 / 1024
            logger.info(f"  {table_name}: {len(files)} arquivo(s), {size_mb:.2f} MB")

        # 8. Sucesso
        elapsed = time.time() - start_time
        logger.info("\n" + "=" * 70)
        logger.info(f"✓ SINCRONIZAÇÃO CONCLUÍDA COM SUCESSO")
        logger.info(f"✓ Tempo decorrido: {elapsed:.2f} segundos")
        logger.info(f"✓ Total GCS: {total_gcs} | Local: {len(files_by_table)} tabelas | Novos: {len(files_to_download)}")
        logger.info("=" * 70)

        return 0

    except ValueError as e:
        logger.error(f"Erro de configuração: {e}")
        return 1

    except Exception as e:
        logger.critical(f"Erro inesperado: {e}", exc_info=True)
        return 4


if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)
