"""Classe base para scrapers municipais com extracao via Gemini.

Usa session com headers de browser real e retry com backoff.
"""
from abc import ABC
import logging
import time

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

from automacao.ai_extractor import extract_concursos_from_html

logger = logging.getLogger(__name__)

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "pt-BR,pt;q=0.9,en;q=0.8",
    "Accept-Encoding": "gzip, deflate, br",
    "Connection": "keep-alive",
}


def _make_session(verify_ssl: bool = True) -> requests.Session:
    session = requests.Session()
    session.headers.update(HEADERS)
    retry_cfg = Retry(
        total=3,
        backoff_factor=3,
        status_forcelist=[429, 500, 502, 503, 504],
        allowed_methods=["GET"],
    )
    adapter = HTTPAdapter(max_retries=retry_cfg)
    session.mount("https://", adapter)
    session.mount("http://", adapter)
    if not verify_ssl:
        session.verify = False
    return session


class DiarioMunicipal(ABC):
    nome: str = ""
    base_url: str = ""
    fonte: str = ""
    pages: list[str] = []
    verify_ssl: bool = True
    timeout: int = 30

    def scrape(self) -> list[dict]:
        logger.info(f"Scraping {self.fonte} ({self.nome})...")
        session = _make_session(self.verify_ssl)
        all_results = []
        seen = set()

        for url in self.pages:
            try:
                r = session.get(url, timeout=self.timeout)
                r.raise_for_status()
                results = extract_concursos_from_html(
                    r.text, base_url=self.base_url, fonte=self.fonte
                )
                for c in results:
                    if c["link_edital"] not in seen:
                        seen.add(c["link_edital"])
                        all_results.append(c)
                logger.info(f"{self.fonte} [{url}]: {len(results)} no escopo")
                time.sleep(5)  # espaco generoso entre chamadas ao Gemini
            except Exception as e:
                logger.error(f"Erro {self.fonte} [{url}]: {e}")

        logger.info(f"{self.fonte} total: {len(all_results)}")
        return all_results
