"""Scraper DOU - usa endpoint de pesquisa correto do IN.gov.br.

O endpoint real usado pelo portal eh via POST no SOLR interno.
Fallback: scraping da pagina de busca HTML + Gemini para extrair.
"""
import logging
import time
from datetime import date, timedelta

import requests
from bs4 import BeautifulSoup
from tenacity import retry, stop_after_attempt, wait_exponential

from automacao.ai_extractor import extract_concursos_from_html
from automacao.config import DOU_SEARCH_TERMS

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# URL correta da pesquisa do DOU (retorna HTML, nao JSON)
DOU_SEARCH_URL = "https://www.in.gov.br/consulta/-/buscar/dou"
BASE_URL = "https://www.in.gov.br"

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml",
    "Accept-Language": "pt-BR,pt;q=0.9",
}


@retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=2, min=5, max=30))
def _fetch_dou(term: str, data_inicio: str, data_fim: str) -> str:
    params = {
        "q": term,
        "exactDate": "personalizado",
        "published": data_inicio,
        "endDate": data_fim,
        "s": "todos",
        "p": 1,
    }
    r = requests.get(DOU_SEARCH_URL, params=params, headers=HEADERS, timeout=30)
    r.raise_for_status()
    return r.text


def scrape_dou(days_back: int = 30) -> list[dict]:
    hoje = date.today()
    data_fim = hoje.strftime("%d/%m/%Y")
    data_inicio = (hoje - timedelta(days=days_back)).strftime("%d/%m/%Y")

    all_concursos = []
    seen = set()

    for term in DOU_SEARCH_TERMS:
        logger.info(f"DOU buscando: '{term}'")
        try:
            html = _fetch_dou(term, data_inicio, data_fim)
            results = extract_concursos_from_html(html, base_url=BASE_URL, fonte="DOU")
            for c in results:
                if c["link_edital"] not in seen:
                    seen.add(c["link_edital"])
                    all_concursos.append(c)
            logger.info(f"DOU '{term}': {len(results)} no escopo")
            time.sleep(5)
        except Exception as e:
            logger.error(f"Erro DOU '{term}': {e}")

    logger.info(f"DOU total no escopo: {len(all_concursos)}")
    return all_concursos
