#!/usr/bin/env python3
"""
Coleta eventos científicos do Bluesky via Firehose
Adaptado para integrar com estrutura de eventos do projeto
"""
import re
import json
import logging
import time
import os
import threading
import hashlib
from datetime import datetime
from logging.handlers import RotatingFileHandler
from pathlib import Path
from queue import Queue
from dotenv import load_dotenv
from atproto import FirehoseSubscribeReposClient, parse_subscribe_repos_message, CAR
import pyarrow as pa
import pyarrow.parquet as pq

# Importar Config do projeto
import sys
SCRIPT_DIR = Path(__file__).parent.resolve()
sys.path.insert(0, str(SCRIPT_DIR))
from config import Config

# Carregar variáveis de ambiente
load_dotenv()

DOI_PATTERN = re.compile(r'10\.\d{4,9}/[-._;()/:A-Za-z0-9]+')
URL_PATTERN = re.compile(r'https?://[^\s]+')


class OSSUploader:
    """Gerencia upload assíncrono de arquivos para Alibaba Cloud OSS (opcional)"""

    def __init__(self, config, logger):
        self.config = config
        self.logger = logger
        self.upload_queue = Queue()
        self.enabled = config.get('enabled', False)

        if not self.enabled:
            self.logger.info('OSS upload desabilitado')
            return

        try:
            import oss2
        except ImportError:
            self.logger.warning('oss2 não instalado. Upload OSS desabilitado.')
            self.enabled = False
            return

        # Carregar credenciais do .env
        access_key_id = os.getenv('OSS_ACCESS_KEY_ID')
        access_key_secret = os.getenv('OSS_ACCESS_KEY_SECRET')

        if not access_key_id or not access_key_secret:
            self.logger.error('Credenciais OSS não encontradas no .env!')
            self.enabled = False
            return

        # Configurar cliente OSS
        endpoint = config.get('endpoint', 'https://oss-eu-central-1.aliyuncs.com')
        bucket_name = config.get('bucket_name', 'bluesky-atproto')

        try:
            auth = oss2.Auth(access_key_id, access_key_secret)
            self.bucket = oss2.Bucket(auth, endpoint, bucket_name)
            self.logger.info(f'OSS configurado: {bucket_name} @ {endpoint}')
        except Exception as e:
            self.logger.error(f'Erro ao configurar OSS: {e}')
            self.enabled = False
            return

        self.retry_attempts = config.get('retry_attempts', 3)
        self.delete_after_upload = config.get('delete_after_upload', False)

        # Iniciar worker thread
        self.worker_thread = threading.Thread(target=self._upload_worker, daemon=True)
        self.worker_thread.start()
        self.logger.info('Upload worker iniciado')

    def _calculate_md5(self, file_path):
        """Calcula MD5 do arquivo para validação"""
        hash_md5 = hashlib.md5()
        with open(file_path, 'rb') as f:
            for chunk in iter(lambda: f.read(4096), b''):
                hash_md5.update(chunk)
        return hash_md5.hexdigest()

    def _upload_file(self, file_path):
        """Upload de arquivo com retry"""
        if not self.enabled:
            return False

        import oss2
        file_name = os.path.basename(file_path)

        for attempt in range(1, self.retry_attempts + 1):
            try:
                # Calcular MD5
                local_md5 = self._calculate_md5(file_path)

                # Upload
                self.logger.info(f'Upload {file_name} (tentativa {attempt}/{self.retry_attempts})')
                result = self.bucket.put_object_from_file(file_name, file_path)

                # Validar
                if result.status == 200:
                    self.logger.info(f'✓ Upload bem-sucedido: {file_name} (MD5: {local_md5[:8]}...)')

                    # Deletar arquivo local se configurado
                    if self.delete_after_upload:
                        try:
                            os.remove(file_path)
                            self.logger.info(f'Arquivo local deletado: {file_name}')
                        except Exception as e:
                            self.logger.warning(f'Erro ao deletar arquivo local: {e}')

                    return True
                else:
                    self.logger.warning(f'Upload falhou com status {result.status}')

            except Exception as e:
                self.logger.error(f'Erro no upload (tentativa {attempt}): {e}')
                if attempt < self.retry_attempts:
                    time.sleep(2 ** attempt)  # Backoff exponencial

        self.logger.error(f'✗ Upload falhou após {self.retry_attempts} tentativas: {file_name}')
        return False

    def _upload_worker(self):
        """Worker thread que processa fila de upload"""
        while True:
            try:
                file_path = self.upload_queue.get()
                if file_path is None:  # Sinal de parada
                    break

                self._upload_file(file_path)
                self.upload_queue.task_done()

            except Exception as e:
                self.logger.error(f'Erro no upload worker: {e}')

    def enqueue_upload(self, file_path):
        """Adiciona arquivo à fila de upload"""
        if self.enabled and os.path.exists(file_path):
            self.upload_queue.put(file_path)
            self.logger.info(f'Arquivo enfileirado para upload: {os.path.basename(file_path)}')

    def shutdown(self):
        """Aguarda uploads pendentes e finaliza worker"""
        if self.enabled:
            self.logger.info('Aguardando uploads pendentes...')
            self.upload_queue.join()
            self.upload_queue.put(None)  # Sinal de parada
            self.worker_thread.join(timeout=30)


class ScientificPostCollector:
    def __init__(self, output_dir=None, config_file='config.json'):
        self.load_config(config_file)
        
        # Usar diretório da nova estrutura se não especificado
        if output_dir is None:
            self.output_dir = Config.BLUESKY_RAW_DIR
        else:
            self.output_dir = Path(output_dir)
        
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.state_file = self.output_dir / 'state.json'
        self.log_file = self.output_dir / 'collector.log'
        self.posts_buffer = []
        self.count = 0
        self.checked_count = 0
        self.session_start = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

        # Arquivo com timestamp único
        self.current_file_index = 0
        self.output_file = self._generate_new_filename()

        self.setup_logging()
        self.load_state()

        # Inicializar OSS uploader (opcional)
        oss_config = self.config.get('oss_config', {})
        self.oss_uploader = OSSUploader(oss_config, self.logger)
        self.upload_threshold_bytes = oss_config.get('upload_threshold_mb', 50) * 1024 * 1024
        self.max_local_storage_bytes = oss_config.get('max_local_storage_gb', 5) * 1024 * 1024 * 1024

    def load_config(self, config_file):
        try:
            config_path = Path(config_file)
            if not config_path.is_absolute():
                config_path = SCRIPT_DIR / config_file
            
            if config_path.exists():
                with open(config_path, 'r') as f:
                    self.config = json.load(f)
            else:
                self.config = {}
            
            self.scientific_domains = self.config.get('scientific_domains', [])
            self.output_columns = self.config.get('output_columns', ['urls', 'text', 'author_did', 'timestamp', 'doi'])
            self.buffer_size = self.config.get('buffer_size', 50)
        except Exception as e:
            print(f'Aviso: Erro ao carregar {config_file}: {e}. Usando configurações padrão.')
            self.config = {}
            self.scientific_domains = []
            self.output_columns = ['urls', 'text', 'author_did', 'timestamp', 'doi']
            self.buffer_size = 50

    def setup_logging(self):
        """Configura sistema de logging com rotação de arquivos"""
        self.logger = logging.getLogger('ScientificPostCollector')
        self.logger.setLevel(logging.INFO)

        # Limpar handlers existentes
        self.logger.handlers.clear()

        # Handler para arquivo com rotação (max 10MB, 5 backups)
        file_handler = RotatingFileHandler(
            self.log_file,
            maxBytes=10*1024*1024,
            backupCount=5,
            encoding='utf-8'
        )
        file_handler.setLevel(logging.INFO)

        # Handler para console
        console_handler = logging.StreamHandler()
        console_handler.setLevel(logging.INFO)

        # Formato
        formatter = logging.Formatter('[%(asctime)s] [%(levelname)s] %(message)s', datefmt='%Y-%m-%d %H:%M:%S')
        file_handler.setFormatter(formatter)
        console_handler.setFormatter(formatter)

        self.logger.addHandler(file_handler)
        self.logger.addHandler(console_handler)

    def load_state(self):
        """Carrega estado da sessão anterior se existir"""
        if self.state_file.exists():
            try:
                with open(self.state_file, 'r') as f:
                    state = json.load(f)
                self.count = state.get('total_posts_saved', 0)
                self.checked_count = state.get('total_posts_checked', 0)
                last_save = state.get('last_save_time', 'desconhecido')

                self.logger.info('='*60)
                self.logger.info('RETOMANDO SESSÃO ANTERIOR')
                self.logger.info(f'Último salvamento: {last_save}')
                self.logger.info(f'Posts salvos: {self.count}')
                self.logger.info(f'Posts checados: {self.checked_count}')
                self.logger.info('='*60)
            except Exception as e:
                self.logger.warning(f'Não foi possível carregar state.json: {e}. Começando do zero.')
        else:
            self.logger.info('Iniciando nova sessão de coleta')

    def save_state(self):
        """Salva estado atual para recuperação futura"""
        state = {
            'total_posts_saved': self.count,
            'total_posts_checked': self.checked_count,
            'last_save_time': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            'session_start': self.session_start
        }
        try:
            with open(self.state_file, 'w') as f:
                json.dump(state, f, indent=2)
        except Exception as e:
            self.logger.error(f'Erro ao salvar state.json: {e}')

    def has_scientific_content(self, text):
        if DOI_PATTERN.search(text):
            return 'DOI'
        urls = URL_PATTERN.findall(text)
        for url in urls:
            for domain in self.scientific_domains:
                if domain in url.lower():
                    return domain
        return None

    def extract_dois_from_urls(self, urls_string):
        if not urls_string:
            return ''
        urls = urls_string.split('|')
        dois = []
        for url in urls:
            match = re.search(r'doi\.org/(10\.\d{4,9}/[^\s|]+)', url)
            if match:
                dois.append(match.group(1))
        return '|'.join(dois) if dois else ''

    def extract_urls(self, text, record):
        urls_from_facets = []
        facets = record.get('facets', [])
        for facet in facets:
            features = facet.get('features', [])
            for feature in features:
                if feature.get('$type') == 'app.bsky.richtext.facet#link':
                    uri = feature.get('uri')
                    if uri:
                        urls_from_facets.append(uri)

        return list(set(urls_from_facets))

    def _generate_new_filename(self):
        """Gera nome de arquivo único com timestamp"""
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        self.current_file_index += 1
        filename = f'scientific_posts_{timestamp}_{self.current_file_index:03d}.parquet'
        return self.output_dir / filename

    def _get_file_size(self, file_path):
        """Retorna tamanho do arquivo em bytes"""
        try:
            return os.path.getsize(file_path) if os.path.exists(file_path) else 0
        except Exception:
            return 0

    def _get_total_local_storage(self):
        """Calcula tamanho total de arquivos .parquet na pasta"""
        total = 0
        try:
            for file in self.output_dir.glob('*.parquet'):
                total += os.path.getsize(file)
        except Exception as e:
            self.logger.warning(f'Erro ao calcular storage local: {e}')
        return total

    def _cleanup_old_files(self):
        """Remove arquivos antigos se exceder limite de storage"""
        total_storage = self._get_total_local_storage()

        if total_storage > self.max_local_storage_bytes:
            # Listar arquivos por data de modificação
            files = sorted(
                self.output_dir.glob('*.parquet'),
                key=lambda f: os.path.getmtime(f)
            )

            # Remover os mais antigos até ficar abaixo do limite
            for file in files:
                if file == self.output_file:  # Nunca deletar arquivo atual
                    continue

                try:
                    file_size = os.path.getsize(file)
                    os.remove(file)
                    total_storage -= file_size
                    self.logger.info(f'Arquivo antigo removido: {file.name} (liberou {file_size / 1024 / 1024:.1f} MB)')

                    if total_storage <= self.max_local_storage_bytes * 0.8:  # 80% do limite
                        break
                except Exception as e:
                    self.logger.error(f'Erro ao remover arquivo {file.name}: {e}')

    def _rotate_file_if_needed(self):
        """Rotaciona arquivo se exceder threshold"""
        current_size = self._get_file_size(self.output_file)

        if current_size >= self.upload_threshold_bytes:
            self.logger.info(f'Rotacionando arquivo: {current_size / 1024 / 1024:.1f} MB')

            # Enfileirar upload do arquivo atual
            self.oss_uploader.enqueue_upload(str(self.output_file))

            # Criar novo arquivo
            self.output_file = self._generate_new_filename()
            self.logger.info(f'Novo arquivo: {self.output_file.name}')

            # Limpar arquivos antigos se necessário
            self._cleanup_old_files()

    def save_buffer(self):
        if not self.posts_buffer:
            return

        all_data = {
            'urls': [p['urls'] for p in self.posts_buffer],
            'text': [p['text'] for p in self.posts_buffer],
            'author_did': [p['author_did'] for p in self.posts_buffer],
            'timestamp': [p['timestamp'] for p in self.posts_buffer],
            'doi': [self.extract_dois_from_urls(p['urls']) for p in self.posts_buffer]
        }

        df_data = {col: all_data[col] for col in self.output_columns if col in all_data}

        # Contar quantos posts têm DOI
        posts_with_doi = sum(1 for doi in all_data['doi'] if doi)

        table = pa.table(df_data)

        # Append usando dataset API (mais eficiente em memória)
        try:
            # Criar arquivo temporário para evitar corrupção
            temp_file = self.output_file.with_suffix('.tmp')

            if Path(self.output_file).exists():
                # Ler arquivo existente em chunks e escrever com novos dados
                existing_table = pq.read_table(self.output_file)
                combined = pa.concat_tables([existing_table, table])
                pq.write_table(combined, temp_file, compression='snappy')

                # Substituir arquivo original
                os.replace(temp_file, self.output_file)
            else:
                # Primeiro arquivo - criar novo
                pq.write_table(table, self.output_file, compression='snappy')

        except Exception as e:
            self.logger.error(f'Erro ao salvar arquivo: {e}')
            # Tentar salvar em arquivo de backup
            backup_file = self.output_file.with_suffix('.backup.parquet')
            pq.write_table(table, backup_file, compression='snappy')
            self.logger.warning(f'Dados salvos em backup: {backup_file}')

        self.count += len(self.posts_buffer)

        # Logging mais informativo com tamanho do arquivo
        file_size_mb = self._get_file_size(self.output_file) / 1024 / 1024
        total_storage_mb = self._get_total_local_storage() / 1024 / 1024
        self.logger.info(
            f'Salvos {len(self.posts_buffer)} posts ({posts_with_doi} com DOI). '
            f'Total: {self.count} | Arquivo: {file_size_mb:.1f} MB | Storage: {total_storage_mb:.1f} MB'
        )

        # Registrar coleta no log padronizado
        try:
            log_file = Config.BLUESKY_COLLECTION_LOG
            log_file.parent.mkdir(parents=True, exist_ok=True)
            
            current_date = datetime.today().strftime('%Y-%m-%d')
            with open(log_file, 'a') as f:
                f.write(f"{current_date},{len(self.posts_buffer)},{self.count}\n")
        except Exception as e:
            self.logger.warning(f'Erro ao registrar no log padronizado: {e}')

        self.posts_buffer = []

        # Salvar checkpoint após salvar dados
        self.save_state()

        # Verificar se precisa rotacionar arquivo
        self._rotate_file_if_needed()

    def format_timestamp(self, iso_timestamp):
        try:
            dt = datetime.fromisoformat(iso_timestamp.replace('Z', '+00:00'))
            return dt.strftime('%d-%m-%Y %H:%M:%S')
        except:
            return iso_timestamp

    def handle_message(self, message):
        try:
            commit = parse_subscribe_repos_message(message)
        except (KeyError, AttributeError, ValueError) as e:
            # Ignorar tipos de mensagem desconhecidos (ex: #account, #handle, etc)
            # Esses tipos não são posts, então podemos ignorar silenciosamente
            return
        
        if not hasattr(commit, 'ops') or not commit.ops:
            return

        found_scientific = False
        for op in commit.ops:
            if op.action != 'create' or not op.path.startswith('app.bsky.feed.post/'):
                continue

            self.checked_count += 1

            # Checkpoint periódico a cada 500 posts checados
            if self.checked_count % 500 == 0:
                self.save_state()
                self.logger.info(f'Checkpoint: {self.checked_count} posts checados, {self.count} salvos')

            try:
                car = CAR.from_bytes(commit.blocks)
                record = car.blocks.get(op.cid)
                if not record:
                    continue

                text = record.get('text', '')
                tip = self.has_scientific_content(text)
                if not tip:
                    continue

                urls = self.extract_urls(text, record)
                if not urls:
                    continue

                timestamp = record.get('createdAt', '')
                formatted_date = self.format_timestamp(timestamp)

                text_preview = text[:80] if len(text) > 80 else text
                text_preview = text_preview.replace('\n', ' ')

                self.logger.info(f'Post coletado: {commit.repo}, data: {formatted_date}, {text_preview}, tip: {tip}')

                self.posts_buffer.append({
                    'urls': '|'.join(urls),
                    'text': text,
                    'author_did': commit.repo,
                    'timestamp': timestamp
                })

                found_scientific = True

                if len(self.posts_buffer) >= self.buffer_size:
                    self.save_buffer()

            except Exception as e:
                self.logger.debug(f'Erro ao processar mensagem: {e}')
                continue

        if not found_scientific and self.checked_count % 1000 == 0:
            self.logger.info(f'Progresso: {self.checked_count} posts checados, {self.count} salvos')

    def connect_with_retry(self):
        """Conecta ao Firehose com retry automático em caso de falha"""
        retry_delays = [5, 10, 30, 60, 300]  # 5s, 10s, 30s, 1min, 5min
        retry_count = 0

        while True:
            try:
                self.logger.info('Conectando ao Firehose do Bluesky...')
                client = FirehoseSubscribeReposClient()
                client.start(self.handle_message)

            except KeyboardInterrupt:
                self.logger.info('Interrupção manual detectada (Ctrl+C)')
                raise

            except Exception as e:
                # Salvar estado antes de tentar reconectar
                self.save_buffer()
                self.save_state()

                # Determinar delay para próxima tentativa
                delay_index = min(retry_count, len(retry_delays) - 1)
                delay = retry_delays[delay_index]

                self.logger.warning(f'Conexão perdida: {e}')
                self.logger.warning(f'Tentando reconectar em {delay} segundos... (tentativa {retry_count + 1})')

                time.sleep(delay)
                retry_count += 1

    def run(self):
        self.logger.info('='*60)
        self.logger.info('INICIANDO COLETA DE POSTS CIENTÍFICOS')
        self.logger.info(f'Diretório de saída: {self.output_dir}')
        self.logger.info(f'Arquivo atual: {self.output_file.name}')
        self.logger.info(f'Buffer size: {self.buffer_size}')
        self.logger.info(f'Upload threshold: {self.upload_threshold_bytes / 1024 / 1024:.0f} MB')
        self.logger.info(f'Max local storage: {self.max_local_storage_bytes / 1024 / 1024 / 1024:.1f} GB')
        self.logger.info(f'Domínios científicos: {", ".join(self.scientific_domains) if self.scientific_domains else "Nenhum"}')
        self.logger.info('='*60)

        try:
            self.connect_with_retry()
        except KeyboardInterrupt:
            self.logger.info('\n\nParando... Salvando dados finais...')
            self.save_buffer()

            # Aguardar uploads pendentes
            self.logger.info('Finalizando uploads...')
            self.oss_uploader.shutdown()

            self.logger.info(f'Finalizado! Total: {self.count} posts científicos salvos')
            self.logger.info(f'Total de posts checados: {self.checked_count}')
            if self.checked_count > 0:
                taxa = (self.count / self.checked_count) * 100
                self.logger.info(f'Taxa de posts científicos: {taxa:.2f}%')


if __name__ == '__main__':
    collector = ScientificPostCollector()
    collector.run()

