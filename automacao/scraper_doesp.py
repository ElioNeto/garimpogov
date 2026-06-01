"""Scraper DOE-SP (Diário Oficial do Estado de São Paulo).

URL: https://www.imprensaoficial.com.br
Busca por concursos públicos no caderno de concursos.
"""
import logging
from urllib.parse import quote

import requests
from tenacity import retry, stop_after_attempt, wait_exponential

from automacao.ai_extractor import extract_concursos_from_html
from automacao.scraper_base import BaseScraper
from automacao.config import DEFAULT_HEADERS

logger = logging.getLogger(__name__)

BASE_URL = "https://www.imprensaoficial.com.br"


class DOESc(BaseScraper):
    nome = "DOE-SP"
    base_url = BASE_URL
    pages = [
        BASE_URL + "/",
        BASE_URL + "/DO?categoria=concursos",
        BASE_URL + "/DO?categoria=concursos&q=" + quote("concurso público tecnologia"),
        BASE_URL + "/DO?categoria=concursos&q=" + quote("concurso público professor inglês"),
    ]

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=2, min=5, max=30))
    def _fetch_page(self, url: str) -> str:
        r = requests.get(url, headers=DEFAULT_HEADERS, timeout=30)
        r.raise_for_status()
        return r.text


def scrape_doesp() -> list[dict]:
    return DOESc().scrape()
