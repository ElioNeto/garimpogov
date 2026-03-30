"""Classe base para scrapers municipais com extracao via Gemini."""
from abc import ABC, abstractmethod
import logging
import time
from datetime import date, timedelta

import requests
from tenacity import retry, stop_after_attempt, wait_exponential

from automacao.ai_extractor import extract_concursos_from_html

logger = logging.getLogger(__name__)

HEADERS = {"User-Agent": "Mozilla/5.0 GarimpoGov/1.0"}

# Termos de busca genericos (usados por portais com campo de busca)
SEARCH_TERMS = [
    "concurso publico tecnologia informacao",
    "concurso publico analista TI",
    "concurso publico professor ingles",
    "edital concurso superior",
]


class DiarioMunicipal(ABC):
    nome: str = ""
    base_url: str = ""
    fonte: str = ""

    # URLs a serem visitadas (pode ser lista de paginas estaticas ou busca)
    # Subclasses definem isso
    pages: list[str] = []

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=4, max=20))
    def _fetch(self, url: str, params: dict = None) -> str:
        r = requests.get(url, params=params or {}, headers=HEADERS, timeout=30)
        r.raise_for_status()
        return r.text

    def scrape(self) -> list[dict]:
        logger.info(f"Scraping {self.fonte} ({self.nome})...")
        all_results = []
        seen = set()

        for url in self.pages:
            try:
                html = self._fetch(url)
                results = extract_concursos_from_html(
                    html, base_url=self.base_url, fonte=self.fonte
                )
                for c in results:
                    if c["link_edital"] not in seen:
                        seen.add(c["link_edital"])
                        all_results.append(c)
                logger.info(f"{self.fonte} [{url}]: {len(results)} no escopo")
                time.sleep(4)  # respeita rate limit
            except Exception as e:
                logger.error(f"Erro {self.fonte} [{url}]: {e}")

        logger.info(f"{self.fonte} total: {len(all_results)}")
        return all_results
