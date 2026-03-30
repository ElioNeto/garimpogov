"""Base para scrapers de bancas organizadoras."""
import logging
import time
import warnings

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
from requests.packages.urllib3.exceptions import InsecureRequestWarning

from automacao.ai_extractor import extract_concursos_from_html

logger = logging.getLogger(__name__)

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/120 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml",
    "Accept-Language": "pt-BR,pt;q=0.9",
}


def _session(verify_ssl: bool = True) -> requests.Session:
    s = requests.Session()
    s.headers.update(HEADERS)
    retry = Retry(total=3, backoff_factor=3, status_forcelist=[429, 500, 502, 503, 504])
    s.mount("https://", HTTPAdapter(max_retries=retry))
    s.mount("http://", HTTPAdapter(max_retries=retry))
    if not verify_ssl:
        s.verify = False
        warnings.filterwarnings("ignore", category=InsecureRequestWarning)
    return s


def scrape_banca(nome: str, base_url: str, pages: list[str], verify_ssl: bool = True, timeout: int = 30) -> list[dict]:
    session = _session(verify_ssl)
    all_concursos = []
    seen = set()

    for url in pages:
        try:
            r = session.get(url, timeout=timeout)
            r.raise_for_status()
            results = extract_concursos_from_html(r.text, base_url=base_url, fonte=nome)
            for c in results:
                key = c.get("link_edital", "") or c.get("instituicao", "")
                if key not in seen:
                    seen.add(key)
                    all_concursos.append(c)
            logger.info(f"{nome} [{url}]: {len(results)} no escopo")
            time.sleep(5)
        except Exception as e:
            logger.error(f"Erro {nome} [{url}]: {e}")

    logger.info(f"{nome} total: {len(all_concursos)}")
    return all_concursos
