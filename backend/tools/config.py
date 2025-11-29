
import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

# Diretório raiz do script
SCRIPT_DIR = Path(__file__).parent.resolve()
# Diretório raiz do projeto (um nível acima de tools/)
PROJECT_ROOT = SCRIPT_DIR.parent.resolve()


class Config:
    """Configurações do sistema"""

    # Google Cloud Storage - Bucket Público
    GCS_BUCKET_NAME = os.getenv("GCS_BUCKET_NAME", "altmetria_latam_ibict_tables")
    GCS_FOLDER_PREFIX = os.getenv("GCS_FOLDER_PREFIX", "")

    # Local de salvamento dos parquets.
    # Prioridade:
    # 1. Variável de ambiente LOCAL_DOWNLOAD_PATH
    # 2. /app/data (Docker/VM - diretório padrão do backend)
    # 3. data/ (na raiz do projeto - desenvolvimento local)
    @staticmethod
    def get_download_path():
        env_path = os.getenv("LOCAL_DOWNLOAD_PATH")
        if env_path:
            return env_path

        # Verificar se estamos em ambiente Docker/VM de produção
        app_data = Path("/app/data")
        if app_data.exists():
            return str(app_data)

        # Fallback para desenvolvimento local: data/ na raiz do projeto
        return str(PROJECT_ROOT / "data")

    LOCAL_DOWNLOAD_PATH = get_download_path()

    # ========================================
    # Estrutura de Diretórios para Eventos
    # ========================================
    # Base directory para eventos (raw, processed, consolidated)
    EVENTS_BASE_DIR = Path(LOCAL_DOWNLOAD_PATH) / "events"

    # Configurações de performance
    CHUNK_SIZE = int(os.getenv("CHUNK_SIZE", "50000"))  # Linhas por batch no insert
    DOWNLOAD_CHUNK_SIZE = int(os.getenv("DOWNLOAD_CHUNK_SIZE", "8192"))  # Bytes por chunk no download

    # Retry e timeout
    MAX_RETRIES = int(os.getenv("MAX_RETRIES", "3"))
    RETRY_BACKOFF = int(os.getenv("RETRY_BACKOFF", "2"))  # Segundos (exponencial)
    REQUEST_TIMEOUT = int(os.getenv("REQUEST_TIMEOUT", "300"))  # 5 minutos

    # Logging
    LOG_FILE = os.getenv("LOG_FILE", "import_biblio.log")
    LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")

    # Notificações (opcional)
    WEBHOOK_URL = os.getenv("WEBHOOK_URL", "")  # URL para webhook de notificação
    NOTIFICATION_EMAIL = os.getenv("NOTIFICATION_EMAIL", "")

    # Limpeza automática
    CLEANUP_AFTER_IMPORT = os.getenv("CLEANUP_AFTER_IMPORT", "true").lower() == "true"

    # ========================================
    # Crossref Event Data API
    # ========================================

    # API Configuration
    CROSSREF_API_BASE_URL = "https://api.eventdata.crossref.org/v1/events"
    CROSSREF_MAILTO = os.getenv("CROSSREF_MAILTO", "marcelo@markdev.dev")  # Email para API (recomendado)
    CROSSREF_ROWS_PER_REQUEST = int(os.getenv("CROSSREF_ROWS_PER_REQUEST", "200"))
    CROSSREF_REQUEST_DELAY = float(os.getenv("CROSSREF_REQUEST_DELAY", "1.0"))  # Segundos entre requests

    # Crossref Event Data - Diretórios
    CROSSREF_RAW_DIR = EVENTS_BASE_DIR / "raw" / "crossref"
    CROSSREF_PROCESSED_FILE = EVENTS_BASE_DIR / "processed" / "crossref_clean_events.parquet"
    CROSSREF_COLLECTION_LOG = EVENTS_BASE_DIR / "logs" / "crossref_collection_log.csv"
    
    # Manter compatibilidade: arquivo consolidado (usado pelo backend)
    # Pode conter eventos de múltiplas fontes após consolidação
    ALL_EVENTS_FILE = EVENTS_BASE_DIR / "consolidated" / "all_events.parquet"
    
    # Compatibilidade: manter referência ao nome antigo para backend
    CROSSREF_CLEAN_FILE = ALL_EVENTS_FILE  # Aponta para arquivo consolidado

    # ========================================
    # Bluesky Event Data
    # ========================================
    
    # Bluesky - Diretórios
    BLUESKY_RAW_DIR = EVENTS_BASE_DIR / "raw" / "bluesky"
    BLUESKY_PROCESSED_FILE = EVENTS_BASE_DIR / "processed" / "bluesky_clean_events.parquet"
    BLUESKY_COLLECTION_LOG = EVENTS_BASE_DIR / "logs" / "bluesky_collection_log.csv"
    
    # Configurações do Bluesky (se necessário)
    BLUESKY_OUTPUT_DIR = os.getenv("BLUESKY_OUTPUT_DIR", "")  # Diretório onde código Bluesky salva (se diferente)

    # ========================================
    # BORI Event Data
    # ========================================
    
    # BORI - Diretórios
    BORI_RAW_DIR = EVENTS_BASE_DIR / "raw" / "BORI"
    BORI_PROCESSED_FILE = EVENTS_BASE_DIR / "processed" / "bori_clean_events.parquet"
    BORI_COLLECTION_LOG = EVENTS_BASE_DIR / "logs" / "bori_collection_log.csv"

    # ========================================
    # Funcionalidades Opcionais
    # ========================================

    # MySQL/MariaDB - Importação para banco relacional (DESABILITADO POR PADRÃO)
    # Para habilitar: defina ENABLE_MYSQL_IMPORT=true no .env
    ENABLE_MYSQL_IMPORT = os.getenv("ENABLE_MYSQL_IMPORT", "false").lower() == "true"

    # Configurações MySQL (apenas se ENABLE_MYSQL_IMPORT=true)
    MYSQL_HOST = os.getenv("MYSQL_HOST", "localhost")
    MYSQL_PORT = int(os.getenv("MYSQL_PORT", "3306"))
    MYSQL_DATABASE = os.getenv("MYSQL_DATABASE", "openalex_latam")
    MYSQL_USER = os.getenv("MYSQL_USER", "root")
    MYSQL_PASSWORD = os.getenv("MYSQL_PASSWORD", "")

    @staticmethod
    def get_mysql_dict():
        """Retorna dict de configuração MySQL para pymysql.connect()"""
        return {
            "host": Config.MYSQL_HOST,
            "port": Config.MYSQL_PORT,
            "user": Config.MYSQL_USER,
            "password": Config.MYSQL_PASSWORD,
            "database": Config.MYSQL_DATABASE,
            "charset": "utf8mb4"
        }

    @staticmethod
    def validate():
        """Valida configurações essenciais"""
        if not Config.GCS_BUCKET_NAME:
            raise ValueError("GCS_BUCKET_NAME não pode estar vazio")

        # Criar diretório de download se não existir
        download_path = Path(Config.LOCAL_DOWNLOAD_PATH)
        download_path.mkdir(parents=True, exist_ok=True)
        
        # Criar estrutura de diretórios para eventos
        Config.EVENTS_BASE_DIR.mkdir(parents=True, exist_ok=True)
        (Config.EVENTS_BASE_DIR / "raw" / "crossref").mkdir(parents=True, exist_ok=True)
        (Config.EVENTS_BASE_DIR / "raw" / "bluesky").mkdir(parents=True, exist_ok=True)
        (Config.EVENTS_BASE_DIR / "raw" / "BORI").mkdir(parents=True, exist_ok=True)
        (Config.EVENTS_BASE_DIR / "processed").mkdir(parents=True, exist_ok=True)
        (Config.EVENTS_BASE_DIR / "consolidated").mkdir(parents=True, exist_ok=True)
        (Config.EVENTS_BASE_DIR / "logs").mkdir(parents=True, exist_ok=True)

        # Validar MySQL apenas se habilitado
        if Config.ENABLE_MYSQL_IMPORT:
            if not Config.MYSQL_PASSWORD:
                raise ValueError("MYSQL_PASSWORD é obrigatório quando ENABLE_MYSQL_IMPORT=true")


# Tabelas esperadas do OpenAlex (baseado nos exports do BigQuery)
EXPECTED_TABLES = [
    "authors_latam",
    "domains",
    "fields",
    "subfields",
    "topics",
    "institutions_latam",
    "sources_latam",
    "works_authorships_latam",
    "works_latam",
    "works_locations_latam",
    "works_topics_latam",
    "prefixes_latam",
    "prefixes_sources_latam"
]
