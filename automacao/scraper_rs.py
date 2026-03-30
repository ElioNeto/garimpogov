"""Scraper DOERS - navega por edicoes recentes e extrai via Gemini.

O DOERS nao tem API de busca publica. Estrategia:
1. Busca na pagina inicial (destaques + edicoes recentes)
2. Tenta pagina de pesquisa com termo relevante
"""
import logging
import time

import requests
from tenacity import retry, stop_after_attempt, wait_exponential

from automacao.ai_extractor import extract_concursos_from_html

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

BASE_URL = "https://www.diariooficial.rs.gov.br"
HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    )
}

# Paginas publicas do DOERS para varrer
PAGES = [
    BASE_URL + "/",
    BASE_URL + "/pesquisa?q=concurso+publico+tecnologia",
    BASE_URL + "/pesquisa?q=concurso+publico+informatica",
    BASE_URL + "/pesquisa?q=professor+ingles",
]


@retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=2, min=5, max=30))
def _fetch(url: str) -> str:
    r = requests.get(url, headers=HEADERS, timeout=30)
    r.raise_for_status()
    return r.text


def scrape_doers() -> list[dict]:
    all_concursos = []
    seen = set()

    for url in PAGES:
        try:
            html = _fetch(url)
            results = extract_concursos_from_html(html, base_url=BASE_URL, fonte="DOERS")
            for c in results:
                if c["link_edital"] not in seen:
                    seen.add(c["link_edital"])
                    all_concursos.append(c)
            logger.info(f"DOERS [{url}]: {len(results)} no escopo")
            time.sleep(4)
        except Exception as e:
            logger.error(f"Erro DOERS [{url}]: {e}")

    logger.info(f"DOERS total: {len(all_concursos)}")
    return all_concursos
