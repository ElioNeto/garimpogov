"""Scraper DOE-MG (Diário Oficial do Estado de Minas Gerais).

URL: https://www.diariomg.com.br
Busca por concursos públicos no diário oficial.
"""
import logging
from urllib.parse import quote

import requests
from tenacity import retry, stop_after_attempt, wait_exponential

from automacao.ai_extractor import extract_concursos_from_html
from automacao.scraper_base import BaseScraper
from automacao.config import DEFAULT_HEADERS

logger = logging.getLogger(__name__)

BASE_URL = "https://www.diariomg.com.br"


class DOEScraperMG(BaseScraper):
    nome = "DOE-MG"
    base_url = BASE_URL
    pages = [
        BASE_URL + "/",
        BASE_URL + "/edicoes",
        BASE_URL + "/busca?q=" + quote("concurso público"),
        BASE_URL + "/busca?q=" + quote("edital de concurso"),
        BASE_URL + "/busca?q=" + quote("tecnologia informação concurso"),
    ]

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=2, min=5, max=30))
    def _fetch_page(self, url: str) -> str:
        r = requests.get(url, headers=DEFAULT_HEADERS, timeout=30)
        r.raise_for_status()
        return r.text


def scrape_doemg() -> list[dict]:
    return DOEScraperMG().scrape()
