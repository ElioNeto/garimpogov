"""Base para scrapers de bancas - apenas coleta HTML, sem chamar Gemini.

O Gemini e chamado uma unica vez no run_ingestion.py via extract_batch().
"""
import logging
import time
import warnings

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
from requests.packages.urllib3.exceptions import InsecureRequestWarning

logger = logging.getLogger(__name__)

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/120 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml",
    "Accept-Language": "pt-BR,pt;q=0.9",
}


def _session(verify_ssl: bool = True) -> requests.Session:
    s = requests.Session()
    s.headers.update(HEADERS)
    retry = Retry(total=3, backoff_factor=2, status_forcelist=[429, 500, 502, 503, 504])
    s.mount("https://", HTTPAdapter(max_retries=retry))
    s.mount("http://", HTTPAdapter(max_retries=retry))
    if not verify_ssl:
        s.verify = False
        warnings.filterwarnings("ignore", category=InsecureRequestWarning)
    return s


def fetch_pages(nome: str, base_url: str, pages: list[str], verify_ssl: bool = True, timeout: int = 30) -> list[tuple[str, str, str]]:
    """Coleta HTML de todas as paginas de uma banca.

    Returns:
        lista de (html, base_url, nome) para passar ao extract_batch()
    """
    session = _session(verify_ssl)
    results = []

    for url in pages:
        try:
            r = session.get(url, timeout=timeout)
            r.raise_for_status()
            results.append((r.text, base_url, nome))
            logger.info(f"{nome} [{url}]: HTML coletado ({len(r.text)} chars)")
            time.sleep(1)  # delay entre requests HTTP (nao Gemini)
        except Exception as e:
            logger.warning(f"{nome} [{url}]: falha HTTP - {e}")

    return results


def scrape_banca(nome: str, base_url: str, pages: list[str], verify_ssl: bool = True, timeout: int = 30) -> list[tuple[str, str, str]]:
    """Alias de fetch_pages para compatibilidade."""
    return fetch_pages(nome, base_url, pages, verify_ssl, timeout)
