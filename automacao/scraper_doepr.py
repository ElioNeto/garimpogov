"""Scraper DOE-PR (Diário Oficial do Estado do Paraná).

URL: https://www.doe.pr.gov.br
Busca por concursos públicos e editais.
"""
import logging
from urllib.parse import quote

import requests
from tenacity import retry, stop_after_attempt, wait_exponential

from automacao.ai_extractor import extract_concursos_from_html
from automacao.scraper_base import BaseScraper
from automacao.config import DEFAULT_HEADERS

logger = logging.getLogger(__name__)

BASE_URL = "https://www.doe.pr.gov.br"


class DOEScraperPR(BaseScraper):
    nome = "DOE-PR"
    base_url = BASE_URL
    pages = [
        BASE_URL + "/",
        BASE_URL + "/consulta",
        BASE_URL + "/consulta?q=" + quote("concurso público"),
        BASE_URL + "/consulta?q=" + quote("edital tecnologia informação"),
        BASE_URL + "/consulta?q=" + quote("professor inglês concurso"),
    ]

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=2, min=5, max=30))
    def _fetch_page(self, url: str) -> str:
        r = requests.get(url, headers=DEFAULT_HEADERS, timeout=30)
        r.raise_for_status()
        return r.text


def scrape_doepr() -> list[dict]:
    return DOEScraperPR().scrape()
