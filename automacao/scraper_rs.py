"""Scraper DOERS - navega por edicoes recentes e extrai via Gemini.

O DOERS nao tem API de busca publica. Estrategia:
1. Busca na pagina inicial (destaques + edicoes recentes)
2. Tenta pagina de pesquisa com termo relevante
"""
import logging

from tenacity import retry, stop_after_attempt, wait_exponential

from automacao.ai_extractor import extract_concursos_from_html
from automacao.scraper_base import BaseScraper

logger = logging.getLogger(__name__)

BASE_URL = "https://www.diariooficial.rs.gov.br"


class DOERSScraper(BaseScraper):
    nome = "DOERS"
    base_url = BASE_URL
    pages = [
        BASE_URL + "/",
        BASE_URL + "/pesquisa?q=concurso+publico+tecnologia",
        BASE_URL + "/pesquisa?q=concurso+publico+informatica",
        BASE_URL + "/pesquisa?q=professor+ingles",
    ]

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=2, min=5, max=30))
    def _fetch_page(self, url: str) -> str:
        return super()._fetch_page(url)


def scrape_doers() -> list[dict]:
    return DOERSScraper().scrape()
