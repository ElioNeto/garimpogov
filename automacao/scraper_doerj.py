"""Scraper DOE-RJ (Diário Oficial do Estado do Rio de Janeiro).

URL: https://www.ioerj.com.br
Busca por editais de concursos públicos.
"""
import logging
from urllib.parse import quote

import requests
from tenacity import retry, stop_after_attempt, wait_exponential

from automacao.ai_extractor import extract_concursos_from_html
from automacao.scraper_base import BaseScraper
from automacao.config import DEFAULT_HEADERS

logger = logging.getLogger(__name__)

BASE_URL = "https://www.ioerj.com.br"


class DOEScraperRJ(BaseScraper):
    nome = "DOE-RJ"
    base_url = BASE_URL
    pages = [
        BASE_URL + "/",
        BASE_URL + "/portal/faces/pages_publicas/consultar_edicoes",
        BASE_URL + "/portal/faces/pages_publicas/consultar_edicoes?q=" + quote("concurso público"),
        BASE_URL + "/portal/faces/pages_publicas/consultar_edicoes?q=" + quote("edital tecnologia"),
    ]

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=2, min=5, max=30))
    def _fetch_page(self, url: str) -> str:
        r = requests.get(url, headers=DEFAULT_HEADERS, timeout=30)
        r.raise_for_status()
        return r.text


def scrape_doerj() -> list[dict]:
    return DOEScraperRJ().scrape()
