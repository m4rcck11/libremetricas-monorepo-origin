#!/usr/bin/env python3
"""
Script Interativo de Importação de Dados Bibliográficos OpenAlex LATAM
Versão monolítica com menu de opções para controle manual das etapas

Autor: Portal de Altmetria - Ibict
Versão: 1.0 Interactive
"""

import os
import sys
import logging
import shutil
from pathlib import Path
from typing import List, Dict, Optional
from collections import defaultdict
import time

import requests
import duckdb
from tqdm import tqdm
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type

try:
    from colorlog import ColoredFormatter
    HAS_COLORLOG = True
except ImportError:
    HAS_COLORLOG = False

# Importação condicional de pymysql (apenas se MySQL estiver habilitado)
try:
    import pymysql
    HAS_PYMYSQL = True
except ImportError:
    HAS_PYMYSQL = False

# Importação condicional para scripts Crossref
try:
    from collect_crossref_events import collect_all_events
    from process_crossref_events import process_raw_events
    HAS_CROSSREF_SCRIPTS = True
except ImportError:
    HAS_CROSSREF_SCRIPTS = False

try:
    from collect_bluesky_events import ScientificPostCollector
    from process_bluesky_events import process_bluesky_raw_files
    from process_all_events import process_all_events
    HAS_BLUESKY_SCRIPTS = True
except ImportError:
    HAS_BLUESKY_SCRIPTS = False

try:
    from process_bori_events import process_bori_raw_files
    HAS_BORI_SCRIPTS = True
except ImportError:
    HAS_BORI_SCRIPTS = False

from config import Config, EXPECTED_TABLES


# ========================================
# Configuração de Logging
# ========================================

def setup_logging():
    """Configura sistema de logging com arquivo e console"""
    logger = logging.getLogger(__name__)
    logger.setLevel(getattr(logging, Config.LOG_LEVEL.upper()))

    file_handler = logging.FileHandler(Config.LOG_FILE, encoding='utf-8')
    file_handler.setLevel(logging.DEBUG)
    file_formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    file_handler.setFormatter(file_formatter)

    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(getattr(logging, Config.LOG_LEVEL.upper()))

    if HAS_COLORLOG:
        console_formatter = ColoredFormatter(
            '%(log_color)s%(levelname)-8s%(reset)s %(message)s',
            log_colors={
                'DEBUG': 'cyan',
                'INFO': 'green',
                'WARNING': 'yellow',
                'ERROR': 'red',
                'CRITICAL': 'red,bg_white',
            }
        )
    else:
        console_formatter = logging.Formatter('%(levelname)-8s %(message)s')

    console_handler.setFormatter(console_formatter)

    logger.addHandler(file_handler)
    logger.addHandler(console_handler)

    return logger


logger = setup_logging()


# ========================================
# Utilitários de Interface
# ========================================

def print_header(title: str):
    """Imprime cabeçalho formatado"""
    print("\n" + "=" * 70)
    print(f"  {title}")
    print("=" * 70)


def print_menu():
    """Exibe menu principal"""
    print_header("MENU PRINCIPAL - Importação de Dados Bibliográficos")
    print("\n1. 📥 Baixar parquets do bucket GCS")
    print("2. 🔄 Listar parquets baixados")
    print("3. 🔗 Concatenar parquets por tabela (DuckDB)")

    # Opções MySQL (apenas se habilitado)
    if Config.ENABLE_MYSQL_IMPORT and HAS_PYMYSQL:
        print("4. 📤 Enviar parquets para MySQL (Alibaba Cloud)")
        print("5. 🚀 Executar tudo (download + concatenar + enviar)")
        print("7. 🔍 Verificar tabelas no MySQL")
        print("8. ⚙️  Testar conexão MySQL")
    else:
        print("4. [DESABILITADO] Enviar parquets para MySQL")
        print("5. 🚀 Executar tudo (download + concatenar)")

    print("6. 🗑️  Limpar arquivos temporários")
    print("9. 📊 Estatísticas dos dados")
    print("\n📡 Eventos:")
    print("10. 📡 Coletar eventos Crossref Event Data")
    print("11. 🔄 Processar eventos Crossref (raw → clean)")
    if HAS_BLUESKY_SCRIPTS:
        print("12. 🔵 Coletar eventos Bluesky (streaming)")
        print("13. 🔵 Processar eventos Bluesky (raw → clean)")
    if HAS_BORI_SCRIPTS:
        print("15. 📰 Processar eventos BORI (raw → clean)")
    print("14. 🔄 Consolidar todos os eventos (Crossref + Bluesky + BORI)")
    print("\n0. ❌ Sair")
    print("\n" + "-" * 70)

    if Config.ENABLE_MYSQL_IMPORT and not HAS_PYMYSQL:
        print("⚠️  MySQL habilitado mas pymysql não instalado. Execute: pip install pymysql")


def get_user_choice() -> str:
    """Obtém escolha do usuário"""
    try:
        choice = input("\nEscolha uma opção: ").strip()
        return choice
    except KeyboardInterrupt:
        print("\n\n⚠ Operação cancelada pelo usuário")
        sys.exit(0)


def confirm_action(message: str) -> bool:
    """Solicita confirmação do usuário"""
    while True:
        response = input(f"\n{message} (s/n): ").strip().lower()
        if response in ['s', 'sim', 'y', 'yes']:
            return True
        elif response in ['n', 'não', 'nao', 'no']:
            return False
        else:
            print("Resposta inválida. Digite 's' para sim ou 'n' para não.")


# ========================================
# Download de Arquivos do GCS
# ========================================

class GCSDownloader:
    """Classe para download de arquivos do Google Cloud Storage público"""

    def __init__(self):
        self.base_url = f"https://storage.googleapis.com/storage/v1/b/{Config.GCS_BUCKET_NAME}/o"
        self.download_path = Path(Config.LOCAL_DOWNLOAD_PATH)
        self.download_path.mkdir(parents=True, exist_ok=True)

    @retry(
        stop=stop_after_attempt(Config.MAX_RETRIES),
        wait=wait_exponential(multiplier=Config.RETRY_BACKOFF),
        retry=retry_if_exception_type(requests.exceptions.RequestException)
    )
    def list_parquet_files(self) -> List[Dict]:
        """Lista todos os arquivos .parquet no bucket"""
        logger.info(f"Listando arquivos em gs://{Config.GCS_BUCKET_NAME}/{Config.GCS_FOLDER_PREFIX}...")

        params = {}
        if Config.GCS_FOLDER_PREFIX:
            params['prefix'] = Config.GCS_FOLDER_PREFIX

        response = requests.get(self.base_url, params=params, timeout=Config.REQUEST_TIMEOUT)
        response.raise_for_status()

        data = response.json()
        items = data.get('items', [])

        parquet_files = [
            item for item in items
            if item['name'].lower().endswith('.parquet')
        ]

        logger.info(f"Encontrados {len(parquet_files)} arquivos .parquet")
        return parquet_files

    @retry(
        stop=stop_after_attempt(Config.MAX_RETRIES),
        wait=wait_exponential(multiplier=Config.RETRY_BACKOFF),
        retry=retry_if_exception_type(requests.exceptions.RequestException)
    )
    def download_file(self, file_name: str, show_progress: bool = True) -> Path:
        """Baixa um arquivo do GCS"""
        download_url = f"https://storage.googleapis.com/{Config.GCS_BUCKET_NAME}/{file_name}"
        destination = self.download_path / Path(file_name).name

        if destination.exists():
            logger.debug(f"Arquivo já existe: {destination.name}")
            return destination

        logger.debug(f"Baixando {file_name}...")

        response = requests.get(download_url, stream=True, timeout=Config.REQUEST_TIMEOUT)
        response.raise_for_status()

        total_size = int(response.headers.get('content-length', 0))

        with open(destination, 'wb') as f:
            if show_progress and total_size > 0:
                with tqdm(total=total_size, unit='B', unit_scale=True, desc=destination.name) as pbar:
                    for chunk in response.iter_content(chunk_size=Config.DOWNLOAD_CHUNK_SIZE):
                        f.write(chunk)
                        pbar.update(len(chunk))
            else:
                for chunk in response.iter_content(chunk_size=Config.DOWNLOAD_CHUNK_SIZE):
                    f.write(chunk)

        return destination

    def download_all(self, interactive: bool = True) -> Dict[str, List[Path]]:
        """Baixa todos os arquivos e organiza por tabela"""
        files = self.list_parquet_files()

        if not files:
            logger.warning("Nenhum arquivo .parquet encontrado no bucket")
            return {}

        print(f"\n📊 Total de arquivos encontrados: {len(files)}")

        # Mostrar preview dos arquivos
        print("\nPrimeiros 10 arquivos:")
        for i, f in enumerate(files[:10], 1):
            size_mb = int(f.get('size', 0)) / (1024 * 1024)
            print(f"  {i}. {f['name']} ({size_mb:.2f} MB)")

        if len(files) > 10:
            print(f"  ... e mais {len(files) - 10} arquivos")

        if interactive and not confirm_action(f"\nDeseja baixar {len(files)} arquivos?"):
            logger.info("Download cancelado pelo usuário")
            return {}

        logger.info(f"Iniciando download de {len(files)} arquivos...")

        files_by_table = defaultdict(list)

        for file_info in files:
            file_name = file_info['name']
            local_path = self.download_file(file_name)

            # Extrair nome da tabela
            table_name = Path(file_name).stem
            table_name = table_name.rsplit('_', 1)[0] if table_name[-1].isdigit() else table_name

            files_by_table[table_name].append(local_path)

        logger.info(f"✓ Download concluído. {len(files_by_table)} tabelas identificadas")
        return dict(files_by_table)


# ========================================
# Gerenciamento de Arquivos Locais
# ========================================

class LocalFileManager:
    """Gerencia arquivos parquet locais"""

    def __init__(self):
        self.download_path = Path(Config.LOCAL_DOWNLOAD_PATH)

    def list_local_files(self, include_merged: bool = True) -> Dict[str, List[Path]]:
        """Lista arquivos parquet locais organizados por tabela"""
        if not self.download_path.exists():
            return {}

        files_by_table = defaultdict(list)

        # Buscar parquets na pasta principal
        parquet_files = list(self.download_path.glob("*.parquet"))

        for file_path in parquet_files:
            table_name = file_path.stem
            # Remove sufixo numérico do particionamento (ex: works_latam_000000000000 -> works_latam)
            table_name = table_name.rsplit('_', 1)[0] if table_name[-1].isdigit() else table_name
            files_by_table[table_name].append(file_path)

        # Buscar parquets concatenados na pasta merged
        if include_merged:
            merged_path = self.download_path / "merged"
            if merged_path.exists():
                merged_files = list(merged_path.glob("*.parquet"))
                for file_path in merged_files:
                    table_name = file_path.stem
                    files_by_table[table_name].append(file_path)

        return dict(files_by_table)

    def show_local_files(self):
        """Exibe arquivos locais"""
        files_by_table = self.list_local_files()

        if not files_by_table:
            print("\n⚠ Nenhum arquivo parquet encontrado localmente")
            print(f"Diretório: {self.download_path}")
            return

        print(f"\n📁 Arquivos em: {self.download_path}")
        print(f"\n{'Tabela':<30} {'Arquivos':<10} {'Tamanho Total':<15} {'Status'}")
        print("-" * 70)

        total_size = 0
        total_files = 0

        for table_name, files in sorted(files_by_table.items()):
            size = sum(f.stat().st_size for f in files)
            total_size += size
            total_files += len(files)
            size_mb = size / (1024 * 1024)

            # Verificar se é arquivo concatenado
            is_merged = any('merged' in str(f) for f in files)
            status = "🔗 Concatenado" if is_merged else "📦 Particionado"

            print(f"{table_name:<30} {len(files):<10} {size_mb:>10.2f} MB    {status}")

        print("-" * 70)
        print(f"{'TOTAL':<30} {total_files:<10} {total_size / (1024 * 1024):>10.2f} MB")

    def cleanup(self, interactive: bool = True):
        """Remove arquivos temporários (apenas arquivos .parquet na raiz, preserva subdiretórios)"""
        if not self.download_path.exists():
            print("\n✓ Diretório já está limpo")
            return

        # Buscar apenas arquivos .parquet na raiz do diretório (não em subdiretórios)
        files = list(self.download_path.glob("*.parquet"))
        
        # Também limpar pasta merged se existir
        merged_dir = self.download_path / "merged"
        merged_files = []
        if merged_dir.exists():
            merged_files = list(merged_dir.glob("*.parquet"))

        total_files = len(files) + len(merged_files)

        if total_files == 0:
            print("\n✓ Nenhum arquivo para limpar")
            return

        print(f"\n🗑️  Encontrados {total_files} arquivos para remover:")
        if files:
            print(f"  - {len(files)} arquivo(s) na raiz")
        if merged_files:
            print(f"  - {len(merged_files)} arquivo(s) em merged/")

        if interactive and not confirm_action("Confirma a remoção? (Subdiretórios como 'events/' serão preservados)"):
            print("Limpeza cancelada")
            return

        # Remover apenas arquivos .parquet, preservando subdiretórios
        removed_count = 0
        for f in files:
            try:
                f.unlink()
                removed_count += 1
            except Exception as e:
                logger.warning(f"Erro ao remover {f}: {e}")

        # Remover arquivos em merged/ e depois o diretório se estiver vazio
        for f in merged_files:
            try:
                f.unlink()
                removed_count += 1
            except Exception as e:
                logger.warning(f"Erro ao remover {f}: {e}")
        
        # Remover diretório merged se estiver vazio
        if merged_dir.exists():
            try:
                merged_dir.rmdir()  # Só remove se estiver vazio
            except OSError:
                pass  # Diretório não está vazio, deixar como está

        logger.info(f"✓ {removed_count} arquivos removidos")
        print(f"✓ {removed_count} arquivo(s) removido(s)")
        print(f"  Diretório preservado: {self.download_path}")
        print(f"  Subdiretórios (como events/) foram preservados")


# ========================================
# Processamento com DuckDB
# ========================================

class DuckDBProcessor:
    """Processa e concatena parquets com DuckDB"""

    def __init__(self):
        self.file_manager = LocalFileManager()

    def analyze_table(self, table_name: str, parquet_files: List[Path]):
        """Analisa uma tabela usando DuckDB"""
        print(f"\n📊 Analisando tabela: {table_name}")
        print(f"  Arquivos: {len(parquet_files)}")

        duck_conn = duckdb.connect(':memory:')

        try:
            if len(parquet_files) == 1:
                file_pattern = f"'{parquet_files[0]}'"
            else:
                file_pattern = f"[{','.join(repr(str(f)) for f in parquet_files)}]"

            # Contar linhas
            count_query = f"SELECT COUNT(*) as total FROM read_parquet({file_pattern})"
            total_rows = duck_conn.execute(count_query).fetchone()[0]

            # Obter schema
            schema_query = f"DESCRIBE SELECT * FROM read_parquet({file_pattern})"
            schema = duck_conn.execute(schema_query).fetchall()

            print(f"  Total de linhas: {total_rows:,}")
            print(f"  Total de colunas: {len(schema)}")

            if confirm_action("Deseja ver o schema da tabela?"):
                print(f"\n  Schema de {table_name}:")
                for col_name, col_type, *_ in schema:
                    print(f"    - {col_name}: {col_type}")

            if confirm_action("Deseja ver uma amostra dos dados (5 linhas)?"):
                sample_query = f"SELECT * FROM read_parquet({file_pattern}) LIMIT 5"
                sample = duck_conn.execute(sample_query).df()
                print(f"\n{sample.to_string()}\n")

            # Opção de concatenar fisicamente se houver múltiplos arquivos
            if len(parquet_files) > 1:
                print(f"\n💡 Esta tabela tem {len(parquet_files)} arquivos particionados.")
                print(f"   Você pode concatená-los em um único arquivo para melhor performance.")
                if confirm_action(f"Concatenar {len(parquet_files)} arquivos em um único parquet?"):
                    self.merge_parquet_files(table_name, parquet_files, duck_conn)
                else:
                    print("  ⏭️  Concatenação cancelada. Arquivos permanecem particionados.")
            else:
                print(f"\n✓ Esta tabela já está em um único arquivo (não precisa concatenar)")

        except Exception as e:
            logger.error(f"Erro ao analisar tabela {table_name}: {e}")
        finally:
            duck_conn.close()

    def merge_parquet_files(self, table_name: str, parquet_files: List[Path], duck_conn):
        """Concatena múltiplos parquets em um único arquivo"""
        try:
            output_dir = Path(Config.LOCAL_DOWNLOAD_PATH) / "merged"
            output_dir.mkdir(exist_ok=True)
            output_file = output_dir / f"{table_name}.parquet"

            print(f"\n🔗 Concatenando {len(parquet_files)} arquivos...")
            print(f"  Destino: {output_file}")

            file_pattern = f"[{','.join(repr(str(f)) for f in parquet_files)}]"

            # Usar DuckDB para ler todos e salvar como um único parquet
            merge_query = f"""
                COPY (SELECT * FROM read_parquet({file_pattern}))
                TO '{output_file}' (FORMAT PARQUET)
            """

            with tqdm(desc="Concatenando", unit=" linhas") as pbar:
                duck_conn.execute(merge_query)

            file_size = output_file.stat().st_size / (1024 * 1024)
            print(f"  ✓ Arquivo concatenado criado: {output_file.name} ({file_size:.2f} MB)")

            if confirm_action("Remover arquivos particionados originais?"):
                for f in parquet_files:
                    f.unlink()
                    logger.info(f"Removido: {f.name}")
                print(f"  ✓ {len(parquet_files)} arquivos originais removidos")

        except Exception as e:
            logger.error(f"Erro ao concatenar {table_name}: {e}")
            print(f"  ✗ Erro ao concatenar: {e}")

    def concatenate_tables(self, interactive: bool = True):
        """Menu interativo para concatenar tabelas"""
        files_by_table = self.file_manager.list_local_files()

        if not files_by_table:
            print("\n⚠ Nenhum arquivo parquet encontrado para concatenar")
            return

        print("\n🔗 Tabelas disponíveis para análise/concatenação:")
        tables = list(files_by_table.keys())

        for i, table_name in enumerate(tables, 1):
            file_count = len(files_by_table[table_name])
            print(f"  {i}. {table_name} ({file_count} arquivo{'s' if file_count > 1 else ''})")

        print(f"\n  A. Analisar todas as tabelas")
        print(f"  0. Voltar ao menu principal")

        choice = input("\nEscolha uma tabela para analisar (número ou A): ").strip()

        if choice == '0':
            return
        elif choice.upper() == 'A':
            for table_name, files in files_by_table.items():
                self.analyze_table(table_name, files)
                if not confirm_action("\nContinuar para próxima tabela?"):
                    break
        elif choice.isdigit() and 1 <= int(choice) <= len(tables):
            table_name = tables[int(choice) - 1]
            self.analyze_table(table_name, files_by_table[table_name])


# ========================================
# Importação para MySQL
# ========================================

class MySQLImporter:
    """Importa dados para MySQL (FUNCIONALIDADE OPCIONAL)"""

    def __init__(self):
        if not HAS_PYMYSQL:
            raise ImportError(
                "pymysql não está instalado. "
                "Para habilitar MySQL: pip install pymysql"
            )
        if not Config.ENABLE_MYSQL_IMPORT:
            raise RuntimeError(
                "MySQL import está desabilitado. "
                "Para habilitar, defina ENABLE_MYSQL_IMPORT=true no .env"
            )
        self.file_manager = LocalFileManager()

    def test_connection(self):
        """Testa conexão com MySQL"""
        print("\n🔌 Testando conexão com MySQL...")
        print(f"  Host: {Config.MYSQL_HOST}:{Config.MYSQL_PORT}")
        print(f"  Database: {Config.MYSQL_DATABASE}")
        print(f"  User: {Config.MYSQL_USER}")

        try:
            conn = pymysql.connect(**Config.get_mysql_dict())

            # Verificar versão
            cursor = conn.cursor()
            cursor.execute("SELECT VERSION()")
            version = cursor.fetchone()[0]

            cursor.execute("SELECT DATABASE()")
            db = cursor.fetchone()[0]

            cursor.close()
            conn.close()

            print(f"  ✓ Conexão bem-sucedida!")
            print(f"  MySQL Version: {version}")
            print(f"  Current Database: {db}")

            logger.info("Conexão MySQL OK")
            return True

        except Exception as e:
            print(f"  ✗ Erro ao conectar: {e}")
            logger.error(f"Erro de conexão MySQL: {e}")
            return False

    def list_mysql_tables(self):
        """Lista tabelas existentes no MySQL"""
        print("\n📋 Tabelas no MySQL:")

        try:
            conn = pymysql.connect(**Config.get_mysql_dict())
            cursor = conn.cursor()

            # Listar tabelas
            cursor.execute("SHOW TABLES")
            tables = cursor.fetchall()

            if not tables:
                print("  ⚠ Nenhuma tabela encontrada")
                cursor.close()
                conn.close()
                return

            # Obter estatísticas de cada tabela
            print(f"\n{'Tabela':<30} {'Linhas':<15} {'Tamanho'}")
            print("-" * 60)

            for (table_name,) in tables:
                cursor.execute(f"""
                    SELECT
                        TABLE_ROWS,
                        ROUND((DATA_LENGTH + INDEX_LENGTH) / 1024 / 1024, 2) AS size_mb
                    FROM information_schema.TABLES
                    WHERE TABLE_SCHEMA = '{Config.MYSQL_DATABASE}'
                    AND TABLE_NAME = '{table_name}'
                """)

                result = cursor.fetchone()
                if result:
                    rows, size_mb = result
                    print(f"{table_name:<30} {rows or 0:<15,} {size_mb or 0:>10.2f} MB")

            cursor.close()
            conn.close()

        except Exception as e:
            print(f"  ✗ Erro ao listar tabelas: {e}")
            logger.error(f"Erro ao listar tabelas MySQL: {e}")

    @retry(
        stop=stop_after_attempt(Config.MAX_RETRIES),
        wait=wait_exponential(multiplier=Config.RETRY_BACKOFF)
    )
    def import_table(self, table_name: str, parquet_files: List[Path], interactive: bool = True):
        """Importa uma tabela do DuckDB para MySQL"""
        print(f"\n📤 Preparando importação: {table_name}")
        print(f"  Arquivos: {len(parquet_files)}")

        duck_conn = duckdb.connect(':memory:')

        try:
            # Preparar pattern
            if len(parquet_files) == 1:
                file_pattern = f"'{parquet_files[0]}'"
            else:
                file_pattern = f"[{','.join(repr(str(f)) for f in parquet_files)}]"

            # Contar linhas
            count_query = f"SELECT COUNT(*) as total FROM read_parquet({file_pattern})"
            total_rows = duck_conn.execute(count_query).fetchone()[0]
            print(f"  Total de linhas: {total_rows:,}")

            if interactive and not confirm_action(f"Confirma importação de {table_name}?"):
                print("  Importação cancelada")
                return

            # Conectar MySQL
            mysql_conn = pymysql.connect(**Config.get_mysql_dict())
            cursor = mysql_conn.cursor()

            # Verificar se tabela existe
            cursor.execute(f"SHOW TABLES LIKE '{table_name}'")
            table_exists = cursor.fetchone() is not None

            if table_exists:
                cursor.execute(f"SELECT COUNT(*) FROM {table_name}")
                existing_rows = cursor.fetchone()[0]
                print(f"  ⚠ Tabela já existe com {existing_rows:,} linhas")

                if interactive and not confirm_action("Substituir tabela existente?"):
                    cursor.close()
                    mysql_conn.close()
                    return

            # Obter schema
            sample_query = f"SELECT * FROM read_parquet({file_pattern}) LIMIT 1"
            sample_df = duck_conn.execute(sample_query).df()

            # Criar tabela
            print(f"  Criando tabela {table_name}...")
            cursor.execute(f"DROP TABLE IF EXISTS {table_name}")

            create_cols = []
            for col_name, dtype in sample_df.dtypes.items():
                mysql_type = self._map_dtype_to_mysql(dtype)
                create_cols.append(f"`{col_name}` {mysql_type}")

            create_table_sql = f"CREATE TABLE `{table_name}` ({', '.join(create_cols)})"
            cursor.execute(create_table_sql)

            # Inserir dados
            print(f"  Inserindo dados em batches de {Config.CHUNK_SIZE:,}...")

            offset = 0
            with tqdm(total=total_rows, desc=f"Importando {table_name}") as pbar:
                while offset < total_rows:
                    batch_query = f"""
                        SELECT * FROM read_parquet({file_pattern})
                        LIMIT {Config.CHUNK_SIZE} OFFSET {offset}
                    """
                    batch_df = duck_conn.execute(batch_query).df()

                    if batch_df.empty:
                        break

                    cols = ', '.join([f'`{col}`' for col in batch_df.columns])
                    placeholders = ', '.join(['%s'] * len(batch_df.columns))
                    insert_sql = f"INSERT INTO `{table_name}` ({cols}) VALUES ({placeholders})"

                    data = [tuple(row) for row in batch_df.values]
                    cursor.executemany(insert_sql, data)
                    mysql_conn.commit()

                    offset += len(batch_df)
                    pbar.update(len(batch_df))

            cursor.close()
            mysql_conn.close()

            print(f"  ✓ Tabela {table_name} importada com sucesso ({total_rows:,} linhas)")
            logger.info(f"Tabela {table_name} importada: {total_rows:,} linhas")

        except Exception as e:
            print(f"  ✗ Erro ao importar {table_name}: {e}")
            logger.error(f"Erro ao importar {table_name}: {e}")
            raise
        finally:
            duck_conn.close()

    def import_all_tables(self, interactive: bool = True):
        """Importa todas as tabelas"""
        files_by_table = self.file_manager.list_local_files()

        if not files_by_table:
            print("\n⚠ Nenhum arquivo parquet encontrado")
            return

        print(f"\n📤 Tabelas disponíveis para importação:")
        for i, (table_name, files) in enumerate(sorted(files_by_table.items()), 1):
            print(f"  {i}. {table_name} ({len(files)} arquivo{'s' if len(files) > 1 else ''})")

        if interactive and not confirm_action(f"\nImportar todas as {len(files_by_table)} tabelas?"):
            # Menu de seleção individual
            choice = input("\nEscolha uma tabela (número) ou 0 para cancelar: ").strip()

            if choice == '0':
                return

            if choice.isdigit():
                tables = list(sorted(files_by_table.keys()))
                idx = int(choice) - 1

                if 0 <= idx < len(tables):
                    table_name = tables[idx]
                    self.import_table(table_name, files_by_table[table_name], interactive=True)
                else:
                    print("Opção inválida")
            return

        # Importar todas
        for table_name, files in files_by_table.items():
            try:
                self.import_table(table_name, files, interactive=False)
            except Exception as e:
                logger.error(f"Falha em {table_name}: {e}")
                if not confirm_action("Continuar com as próximas tabelas?"):
                    break

    def _map_dtype_to_mysql(self, dtype) -> str:
        """Mapeia tipos do pandas/DuckDB para MySQL"""
        dtype_str = str(dtype).lower()

        if 'int' in dtype_str:
            return 'BIGINT'
        elif 'float' in dtype_str or 'double' in dtype_str:
            return 'DOUBLE'
        elif 'bool' in dtype_str:
            return 'BOOLEAN'
        elif 'datetime' in dtype_str or 'timestamp' in dtype_str:
            return 'DATETIME'
        elif 'date' in dtype_str:
            return 'DATE'
        else:
            return 'TEXT'


# ========================================
# Fluxo Automatizado
# ========================================

def run_full_pipeline():
    """Executa todo o pipeline automaticamente"""
    print_header("EXECUÇÃO COMPLETA DO PIPELINE")

    # Verificar se MySQL está habilitado
    include_mysql = Config.ENABLE_MYSQL_IMPORT and HAS_PYMYSQL

    if include_mysql:
        if not confirm_action("\nIsso irá: baixar → concatenar → importar para MySQL. Continuar?"):
            return
    else:
        if not confirm_action("\nIsso irá: baixar → concatenar parquets. Continuar?"):
            return

    start_time = time.time()

    try:
        # 1. Download
        print("\n" + "=" * 70)
        print("ETAPA 1: Download dos parquets")
        print("=" * 70)
        downloader = GCSDownloader()
        files_by_table = downloader.download_all(interactive=False)

        if not files_by_table:
            print("✗ Nenhum arquivo baixado")
            return

        # 2. Análise (opcional)
        print("\n" + "=" * 70)
        print("ETAPA 2: Análise dos dados (DuckDB)")
        print("=" * 70)
        print(f"✓ {len(files_by_table)} tabelas prontas")

        # 3. Import MySQL (opcional)
        if include_mysql:
            print("\n" + "=" * 70)
            print("ETAPA 3: Importação para MySQL")
            print("=" * 70)
            importer = MySQLImporter()
            importer.import_all_tables(interactive=False)
        else:
            print("\n⏭️  Importação MySQL desabilitada (ENABLE_MYSQL_IMPORT=false)")

        # Limpeza (apenas arquivos .parquet na raiz, preserva subdiretórios como events/)
        if Config.CLEANUP_AFTER_IMPORT:
            print("\n🗑️  Limpando arquivos temporários...")
            print("   (Subdiretórios como 'events/' serão preservados)")
            file_manager = LocalFileManager()
            file_manager.cleanup(interactive=False)

        elapsed = time.time() - start_time
        print_header(f"✓ PIPELINE CONCLUÍDO EM {elapsed:.2f} SEGUNDOS")

    except Exception as e:
        print(f"\n✗ Erro no pipeline: {e}")
        logger.critical(f"Erro no pipeline: {e}", exc_info=True)


# ========================================
# Menu Principal
# ========================================

def main():
    """Função principal com menu interativo"""

    print_header("Script Interativo - Importação OpenAlex LATAM")
    print("\nAutor: Portal de Altmetria - Ibict")
    print("Versão: 1.0 Interactive\n")

    # Validar configurações
    try:
        Config.validate()
        print("✓ Configurações validadas")
    except Exception as e:
        print(f"✗ Erro de configuração: {e}")
        sys.exit(1)

    downloader = GCSDownloader()
    file_manager = LocalFileManager()
    duckdb_processor = DuckDBProcessor()

    # Inicializar MySQL importer apenas se habilitado
    mysql_importer = None
    if Config.ENABLE_MYSQL_IMPORT and HAS_PYMYSQL:
        try:
            mysql_importer = MySQLImporter()
        except Exception as e:
            logger.warning(f"MySQL importer não disponível: {e}")

    while True:
        try:
            print_menu()
            choice = get_user_choice()

            if choice == '1':
                # Download
                files = downloader.download_all(interactive=True)
                if files:
                    print(f"\n✓ Download concluído: {len(files)} tabelas")

            elif choice == '2':
                # Listar locais
                file_manager.show_local_files()

            elif choice == '3':
                # Concatenar/Analisar
                duckdb_processor.concatenate_tables(interactive=True)

            elif choice == '4':
                # Enviar para MySQL
                if mysql_importer:
                    mysql_importer.import_all_tables(interactive=True)
                else:
                    print("\n⚠️  MySQL import está desabilitado")
                    print("   Para habilitar: ENABLE_MYSQL_IMPORT=true no .env")

            elif choice == '5':
                # Pipeline completo
                run_full_pipeline()

            elif choice == '6':
                # Limpar
                file_manager.cleanup(interactive=True)

            elif choice == '7':
                # Ver tabelas MySQL
                if mysql_importer:
                    mysql_importer.list_mysql_tables()
                else:
                    print("\n⚠️  MySQL import está desabilitado")

            elif choice == '8':
                # Testar conexão
                if mysql_importer:
                    mysql_importer.test_connection()
                else:
                    print("\n⚠️  MySQL import está desabilitado")

            elif choice == '9':
                # Estatísticas
                print_header("ESTATÍSTICAS")
                print("\n📁 Arquivos locais:")
                file_manager.show_local_files()
                if mysql_importer:
                    print("\n📊 Tabelas no MySQL:")
                    mysql_importer.list_mysql_tables()
                else:
                    print("\n⏭️  MySQL desabilitado")

            elif choice == '10':
                # Coletar Crossref
                if HAS_CROSSREF_SCRIPTS:
                    print_header("Coleta de Eventos Crossref")
                    # Verificar se prefixes foram baixados
                    prefixes_dir = Path(Config.LOCAL_DOWNLOAD_PATH)
                    prefix_files = list(prefixes_dir.glob('prefixes_latam*.parquet'))
                    
                    if not prefix_files:
                        print("\n⚠️ Arquivo de prefixes não encontrado!")
                        print("   Execute primeiro a opção 1 para baixar os arquivos do GCS.")
                        if confirm_action("Deseja baixar agora?"):
                            # Chamar download do GCS
                            files = downloader.download_all(interactive=False)
                            if not files:
                                print("✗ Falha ao baixar arquivos")
                                continue
                            # Recarregar lista de arquivos
                            prefix_files = list(prefixes_dir.glob('prefixes_latam*.parquet'))
                        else:
                            continue
                    
                    # Mostrar estatísticas antes de iniciar
                    try:
                        from collect_crossref_events import load_prefixes, read_last_collection
                        prefixes = load_prefixes()
                        last_collection = read_last_collection()
                        
                        print(f"\n📊 Estatísticas da Coleta:")
                        print(f"   Prefixes a processar: {len(prefixes):,}")
                        
                        if not last_collection.empty:
                            incremental_count = len(last_collection)
                            print(f"   Coleta incremental: Sim ({incremental_count} prefixes com histórico)")
                            print(f"   Prefixes novos: {len(prefixes) - incremental_count:,}")
                        else:
                            print(f"   Coleta incremental: Não (primeira coleta)")
                        
                        # Estimar tempo (aproximado: ~2 segundos por prefix)
                        estimated_minutes = (len(prefixes) * 2) / 60
                        print(f"   Tempo estimado: ~{estimated_minutes:.1f} minutos")
                        print(f"   Diretório de saída: {Config.CROSSREF_RAW_DIR}")
                        
                        if not confirm_action("\nDeseja iniciar a coleta?"):
                            continue
                            
                    except Exception as e:
                        logger.error(f"Erro ao carregar informações: {e}", exc_info=True)
                        print(f"\n✗ Erro ao carregar informações: {e}")
                        if not confirm_action("Deseja continuar mesmo assim?"):
                            continue
                    
                    try:
                        collect_all_events()
                        print("\n✓ Coleta concluída com sucesso!")
                    except Exception as e:
                        logger.error(f"Erro na coleta: {e}", exc_info=True)
                        print(f"\n✗ Erro: {e}")
                else:
                    print("\n⚠️ Scripts Crossref não disponíveis")

            elif choice == '11':
                # Processar Crossref
                if HAS_CROSSREF_SCRIPTS:
                    print_header("Processamento de Eventos Crossref")
                    try:
                        success = process_raw_events()
                        if success:
                            print("\n✓ Processamento concluído")
                        else:
                            print("\n✗ Processamento falhou. Verifique os logs.")
                    except Exception as e:
                        logger.error(f"Erro no processamento: {e}", exc_info=True)
                        print(f"\n✗ Erro: {e}")
                else:
                    print("\n⚠️ Scripts Crossref não disponíveis")

            elif choice == '12':
                # Coletar Bluesky
                if HAS_BLUESKY_SCRIPTS:
                    print_header("Coleta de Eventos Bluesky")
                    print("\n⚠️ ATENÇÃO: Esta coleta é em tempo real (streaming)")
                    print("   O processo continuará rodando até ser interrompido (Ctrl+C)")
                    print(f"   Arquivos serão salvos em: {Config.BLUESKY_RAW_DIR}")
                    
                    if not confirm_action("\nDeseja iniciar a coleta agora?"):
                        continue
                    
                    try:
                        collector = ScientificPostCollector()
                        collector.run()
                    except KeyboardInterrupt:
                        print("\n\n✓ Coleta interrompida pelo usuário")
                    except Exception as e:
                        logger.error(f"Erro na coleta: {e}", exc_info=True)
                        print(f"\n✗ Erro: {e}")
                else:
                    print("\n⚠️ Scripts Bluesky não disponíveis")
                    print("   Instale as dependências: pip install atproto pyarrow")

            elif choice == '13':
                # Processar Bluesky
                if HAS_BLUESKY_SCRIPTS:
                    print_header("Processamento de Eventos Bluesky")
                    try:
                        success = process_bluesky_raw_files()
                        if success:
                            print("\n✓ Processamento concluído")
                        else:
                            print("\n✗ Processamento falhou. Verifique os logs.")
                    except Exception as e:
                        logger.error(f"Erro no processamento: {e}", exc_info=True)
                        print(f"\n✗ Erro: {e}")
                else:
                    print("\n⚠️ Scripts Bluesky não disponíveis")

            elif choice == '14':
                # Consolidar todos os eventos
                if HAS_CROSSREF_SCRIPTS or HAS_BLUESKY_SCRIPTS or HAS_BORI_SCRIPTS:
                    print_header("Consolidação de Eventos")
                    print("\nEste processo irá:")
                    print("  1. Processar eventos brutos de todas as fontes disponíveis")
                    print("  2. Consolidar em um único arquivo")
                    print("  3. Criar link simbólico para compatibilidade com backend")
                    
                    sources_available = []
                    if HAS_CROSSREF_SCRIPTS:
                        sources_available.append("Crossref")
                    if HAS_BLUESKY_SCRIPTS:
                        sources_available.append("Bluesky")
                    if HAS_BORI_SCRIPTS:
                        sources_available.append("BORI")
                    
                    print(f"\nFontes disponíveis: {', '.join(sources_available)}")
                    
                    if not confirm_action("\nDeseja continuar?"):
                        continue
                    
                    try:
                        success = process_all_events()
                        if success:
                            print("\n✓ Consolidação concluída")
                        else:
                            print("\n✗ Consolidação falhou. Verifique os logs.")
                    except Exception as e:
                        logger.error(f"Erro na consolidação: {e}", exc_info=True)
                        print(f"\n✗ Erro: {e}")
                else:
                    print("\n⚠️ Nenhum script de eventos disponível")

            elif choice == '15':
                # Processar BORI
                if HAS_BORI_SCRIPTS:
                    print_header("Processamento de Eventos BORI")
                    print(f"\nArquivos brutos devem estar em: {Config.BORI_RAW_DIR}")
                    print("Este processo irá:")
                    print("  1. Carregar arquivos .parquet do diretório BORI")
                    print("  2. Extrair DOIs do campo 'labelDOI'")
                    print("  3. Gerar arquivo processado no formato padrão")
                    
                    if not confirm_action("\nDeseja continuar?"):
                        continue
                    
                    try:
                        success = process_bori_raw_files()
                        if success:
                            print("\n✓ Processamento concluído")
                        else:
                            print("\n✗ Processamento falhou. Verifique os logs.")
                    except Exception as e:
                        logger.error(f"Erro no processamento: {e}", exc_info=True)
                        print(f"\n✗ Erro: {e}")
                else:
                    print("\n⚠️ Scripts BORI não disponíveis")

            elif choice == '0':
                # Sair
                if confirm_action("\nTem certeza que deseja sair?"):
                    print("\n👋 Até logo!\n")
                    sys.exit(0)

            else:
                print("\n⚠ Opção inválida. Tente novamente.")

            input("\n[Pressione ENTER para continuar]")

        except KeyboardInterrupt:
            print("\n\n⚠ Operação interrompida")
            if confirm_action("Deseja sair do programa?"):
                print("\n👋 Até logo!\n")
                sys.exit(0)

        except Exception as e:
            logger.error(f"Erro: {e}", exc_info=True)
            print(f"\n✗ Erro: {e}")
            input("\n[Pressione ENTER para continuar]")


if __name__ == "__main__":
    main()
