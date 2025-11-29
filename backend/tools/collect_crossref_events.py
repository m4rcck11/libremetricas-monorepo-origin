#!/usr/bin/env python3
"""
Coleta eventos da API Crossref Event Data
Adaptado do código legado para integração com sistema atual
Suporta coleta incremental baseada em datas anteriores
"""
import requests
import time
from datetime import datetime
import pandas as pd
from pathlib import Path
from typing import List, Optional
import glob
import logging
from tqdm import tqdm
from config import Config

logger = logging.getLogger(__name__)


def read_last_collection() -> pd.DataFrame:
    """Lê datas da última coleta para cada prefix"""
    if not Config.CROSSREF_COLLECTION_LOG.exists():
        logger.info("Nenhuma coleta anterior encontrada. Iniciando do zero.")
        return pd.DataFrame(columns=['prefix', 'date'], dtype=str)
    
    try:
        df = pd.read_csv(Config.CROSSREF_COLLECTION_LOG, names=['prefix', 'date'], header=None)
        # Pegar última data por prefix
        latest = df.groupby('prefix')['date'].max().reset_index()
        latest.columns = ['prefix', 'last_date']
        return latest
    except Exception as e:
        logger.error(f"Erro ao ler log de coleta: {e}")
        return pd.DataFrame(columns=['prefix', 'last_date'], dtype=str)


def collect_events_for_prefix(prefix: str, since: Optional[str] = None, show_progress: bool = False) -> List[dict]:
    """Coleta eventos para um prefix específico com tratamento de rate limits"""
    events = []
    cursor = None
    max_retries = 5
    retry_count = 0
    
    params_names = ["mailto", "rows", "obj-id.prefix"]
    params_values = [
        Config.CROSSREF_MAILTO or "marcelo@markdev.dev",
        str(Config.CROSSREF_ROWS_PER_REQUEST),
        prefix
    ]
    
    if since:
        params_names.append("from-collected-date")
        params_values.append(since)
    
    iteration = 0
    
    while True:
        params = "?" + '&'.join([f"{name}={value}" for name, value in zip(params_names, params_values)])
        
        if cursor:
            params += f"&cursor={cursor}"
        
        try:
            url = Config.CROSSREF_API_BASE_URL + params
            logger.debug(f"Request: {url}")
            
            response = requests.get(url, timeout=Config.REQUEST_TIMEOUT)
            
            # Tratamento de erro 429 (Rate Limit Exceeded)
            if response.status_code == 429:
                retry_after = int(response.headers.get('Retry-After', 60))
                logger.warning(f"Rate limit excedido para {prefix}. Aguardando {retry_after}s...")
                
                if retry_count < max_retries:
                    retry_count += 1
                    time.sleep(retry_after)
                    continue  # Tentar novamente a mesma requisição
                else:
                    logger.error(f"Limite de retries atingido para {prefix} após {max_retries} tentativas")
                    break
            
            # Outros erros HTTP
            if response.status_code != 200:
                logger.error(f"Erro ao coletar eventos para {prefix}: {response.status_code}")
                if response.status_code >= 500:
                    # Erro do servidor - tentar novamente após delay
                    if retry_count < max_retries:
                        retry_count += 1
                        wait_time = min(60, 2 ** retry_count)  # Backoff exponencial até 60s
                        logger.warning(f"Erro do servidor. Aguardando {wait_time}s antes de tentar novamente...")
                        time.sleep(wait_time)
                        continue
                break
            
            # Sucesso - resetar contador de retries
            retry_count = 0
            
            # Ler headers de rate limit para monitoramento
            rate_limit = response.headers.get('x-rate-limit-limit')
            rate_interval = response.headers.get('x-rate-limit-interval')
            rate_remaining = response.headers.get('x-rate-limit-remaining')
            
            if rate_limit and rate_interval:
                logger.debug(f"Rate limit: {rate_limit} req/{rate_interval}s")
                if rate_remaining:
                    remaining = int(rate_remaining)
                    if remaining < 10:
                        logger.warning(f"Atenção: Apenas {remaining} requisições restantes no intervalo atual")
            
            data = response.json()
            batch = data.get("message", {}).get("events", [])
            
            if not batch:
                break
            
            events.extend(batch)
            cursor = data.get("message", {}).get("next-cursor")
            
            iteration += 1
            logger.info(f"Prefix {prefix}: coletados {len(batch)} eventos (iteração {iteration})")
            
            if show_progress:
                print(f"    [{iteration}] {len(batch)} eventos", end='', flush=True)
            
            if not cursor:
                break
            
            # Delay entre requisições (respeitando rate limits)
            time.sleep(Config.CROSSREF_REQUEST_DELAY)
            
        except requests.exceptions.Timeout:
            logger.error(f"Timeout ao coletar eventos para {prefix}")
            if retry_count < max_retries:
                retry_count += 1
                wait_time = min(60, 2 ** retry_count)
                logger.warning(f"Aguardando {wait_time}s antes de tentar novamente...")
                time.sleep(wait_time)
                continue
            break
        except Exception as e:
            logger.error(f"Erro ao coletar eventos para {prefix}: {e}")
            if retry_count < max_retries:
                retry_count += 1
                wait_time = min(60, 2 ** retry_count)
                logger.warning(f"Erro inesperado. Aguardando {wait_time}s antes de tentar novamente...")
                time.sleep(wait_time)
                continue
            break
    
    if show_progress and events:
        print(f" → Total: {len(events):,} eventos ✓")
    elif show_progress:
        print(" → Nenhum evento encontrado")
    
    return events


def save_raw_events(events: List[dict], prefix: str):
    """Salva eventos brutos em Parquet usando json_normalize"""
    Config.CROSSREF_RAW_DIR.mkdir(parents=True, exist_ok=True)
    
    if not events:
        logger.warning(f"Nenhum evento para salvar para prefix {prefix}")
        return
    
    # Normalizar JSON (como no código legado)
    events_table = pd.json_normalize(events)
    
    current_date = datetime.today().strftime('%Y-%m-%d')
    filename = f"p{prefix.replace('.', '_')}_{current_date}.parquet"
    filepath = Config.CROSSREF_RAW_DIR / filename
    
    events_table.to_parquet(filepath, index=False)
    
    # Registrar coleta no log
    with open(Config.CROSSREF_COLLECTION_LOG, 'a') as f:
        f.write(f"{prefix},{current_date}\n")
    
    logger.info(f"Salvos {len(events)} eventos em {filepath}")


def load_prefixes() -> List[str]:
    """Carrega lista de prefixes do arquivo parquet baixado do GCS"""
    prefixes_dir = Path(Config.LOCAL_DOWNLOAD_PATH)
    prefix_files = list(prefixes_dir.glob('prefixes_latam*.parquet'))
    
    if not prefix_files:
        raise FileNotFoundError(
            f"Arquivo de prefixes não encontrado em {prefixes_dir}. "
            "Execute primeiro a opção 1 do menu para baixar os arquivos do GCS."
        )
    
    prefixes_file = prefix_files[-1]  # Usar o mais recente
    logger.info(f"Usando arquivo de prefixes: {prefixes_file}")
    
    df = pd.read_parquet(prefixes_file)
    
    if 'prefix' not in df.columns:
        raise ValueError(f"Arquivo {prefixes_file} não contém coluna 'prefix'")
    
    prefixes = list(df['prefix'].unique())
    logger.info(f"Carregados {len(prefixes)} prefixes únicos")
    return prefixes


def collect_all_events(prefixes: Optional[List[str]] = None):
    """Coleta eventos para todos os prefixes"""
    if prefixes is None:
        prefixes = load_prefixes()
    
    last_collection = read_last_collection()
    
    total_prefixes = len(prefixes)
    total_events = 0
    successful_prefixes = 0
    failed_prefixes = 0
    empty_prefixes = 0
    
    print(f"\n{'='*70}")
    print(f"📡 COLETA DE EVENTOS CROSSREF")
    print(f"{'='*70}")
    print(f"Total de prefixes: {total_prefixes:,}")
    print(f"Diretório de saída: {Config.CROSSREF_RAW_DIR}")
    
    if not last_collection.empty:
        incremental_count = len(last_collection)
        print(f"Coleta incremental: Sim ({incremental_count} prefixes com histórico)")
    else:
        print(f"Coleta incremental: Não (primeira coleta)")
    
    print(f"{'='*70}\n")
    
    # Barra de progresso geral
    with tqdm(total=total_prefixes, desc="Progresso", unit="prefix", ncols=100) as pbar:
        for prefix in prefixes:
            pbar.set_description(f"Processando {prefix}")
            
            logger.info(f"Iniciando coleta para prefix: {prefix}")
            
            # Verificar se há coleta anterior
            since = None
            if not last_collection.empty and prefix in last_collection['prefix'].values:
                since = last_collection[last_collection['prefix'] == prefix]['last_date'].iloc[0]
                logger.info(f"Coleta incremental desde: {since}")
            
            try:
                events = collect_events_for_prefix(prefix, since, show_progress=True)
                
                if events:
                    save_raw_events(events, prefix)
                    total_events += len(events)
                    successful_prefixes += 1
                    pbar.set_postfix({
                        'eventos': f"{total_events:,}",
                        'sucesso': successful_prefixes
                    })
                else:
                    logger.warning(f"Nenhum evento coletado para {prefix}")
                    empty_prefixes += 1
                    pbar.set_postfix({
                        'eventos': f"{total_events:,}",
                        'vazios': empty_prefixes
                    })
            except Exception as e:
                logger.error(f"Erro ao coletar {prefix}: {e}", exc_info=True)
                failed_prefixes += 1
                pbar.set_postfix({
                    'eventos': f"{total_events:,}",
                    'erros': failed_prefixes
                })
            
            pbar.update(1)
    
    # Resumo final
    print(f"\n{'='*70}")
    print(f"✓ COLETA CONCLUÍDA")
    print(f"{'='*70}")
    print(f"Prefixes processados: {total_prefixes:,}")
    print(f"  ✓ Com eventos: {successful_prefixes:,}")
    print(f"  ⚠ Sem eventos: {empty_prefixes:,}")
    print(f"  ✗ Com erros: {failed_prefixes:,}")
    print(f"\nTotal de eventos coletados: {total_events:,}")
    print(f"Arquivos salvos em: {Config.CROSSREF_RAW_DIR}")
    print(f"{'='*70}\n")


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    collect_all_events()

