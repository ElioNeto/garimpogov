"""Scraper DOESC - SSL verify=False (certificado invalido do servidor SC).

Portal oficial: https://www.doe.sea.sc.gov.br
Alternativa: portal de licitacoes/concursos do estado SC.
"""
import logging
import time
import warnings

import requests
from requests.packages.urllib3.exceptions import InsecureRequestWarning
from tenacity import retry, stop_after_attempt, wait_exponential

from automacao.ai_extractor import extract_concursos_from_html

warnings.filterwarnings("ignore", category=InsecureRequestWarning)
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

BASE_URL = "https://www.doe.sea.sc.gov.br"
HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    )
}

PAGES = [
    BASE_URL + "/",
    BASE_URL + "/buscapublicacao?q=concurso+publico+tecnologia",
    BASE_URL + "/buscapublicacao?q=concurso+publico+professor+ingles",
    # Portal de RH do estado SC como alternativa
    "https://www.sc.gov.br/index.php/noticias/temas/concursos-e-selecoes",
]


@retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=2, min=5, max=30))
def _fetch(url: str) -> str:
    r = requests.get(url, headers=HEADERS, timeout=30, verify=False)
    r.raise_for_status()
    return r.text


def scrape_doesc() -> list[dict]:
    all_concursos = []
    seen = set()

    for url in PAGES:
        try:
            html = _fetch(url)
            results = extract_concursos_from_html(html, base_url=BASE_URL, fonte="DOESC")
            for c in results:
                if c["link_edital"] not in seen:
                    seen.add(c["link_edital"])
                    all_concursos.append(c)
            logger.info(f"DOESC [{url}]: {len(results)} no escopo")
            time.sleep(4)
        except Exception as e:
            logger.error(f"Erro DOESC [{url}]: {e}")

    logger.info(f"DOESC total: {len(all_concursos)}")
    return all_concursos
