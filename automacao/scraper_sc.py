"""Scraper DOESC.

Portal oficial: https://www.doe.sea.sc.gov.br
Alternativa: portal de licitacoes/concursos do estado SC.

Nota (B31): O certificado SSL do servidor SC costumava ser invalido,
portanto usamos verify=False como fallback.
"""
import logging
import os

import requests
from tenacity import retry, stop_after_attempt, wait_exponential

from automacao.ai_extractor import extract_concursos_from_html
from automacao.scraper_base import BaseScraper

logger = logging.getLogger(__name__)

BASE_URL = "https://www.doe.sea.sc.gov.br"


class DOEScScraper(BaseScraper):
    nome = "DOESC"
    base_url = BASE_URL
    pages = [
        BASE_URL + "/",
        BASE_URL + "/buscapublicacao?q=concurso+publico+tecnologia",
        BASE_URL + "/buscapublicacao?q=concurso+publico+professor+ingles",
        # Portal de RH do estado SC como alternativa
        "https://www.sc.gov.br/index.php/noticias/temas/concursos-e-selecoes",
    ]
    # SSL: tenta com True, fallback False (certificado conhecido como problematico)
    verify_override = None  # setado durante scrape

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=2, min=5, max=30))
    def _fetch_page(self, url: str) -> str:
        ca_bundle = os.environ.get("REQUESTS_CA_BUNDLE")
        verify = ca_bundle if (ca_bundle and os.path.exists(ca_bundle)) else True
        try:
            r = requests.get(
                url, headers=self._make_session().headers,
                timeout=self.timeout, verify=verify,
            )
            r.raise_for_status()
            return r.text
        except requests.exceptions.SSLError:
            logger.warning(f"SSL Error para {url}, tentando sem verificacao...")
            r = requests.get(
                url, headers=self._make_session().headers,
                timeout=self.timeout, verify=False,
            )
            r.raise_for_status()
            return r.text

    def scrape(self) -> list[dict]:
        logger.info(f"Scraping {self.nome} ({len(self.pages)} paginas)...")
        all_concursos = []
        seen: set[str] = set()

        for url in self.pages:
            try:
                html = self._fetch_page(url)
                results = extract_concursos_from_html(
                    html, base_url=self.base_url, fonte=self.nome
                )
                for c in results:
                    key = c.get("link_edital", "") or c.get("instituicao", "")
                    if key not in seen:
                        seen.add(key)
                        all_concursos.append(c)
                logger.info(f"{self.nome} [{url}]: {len(results)} extraidos")
            except Exception as e:
                logger.error(f"Erro {self.nome} [{url}]: {e}")

        logger.info(f"{self.nome} total: {len(all_concursos)}")
        return all_concursos


def scrape_doesc() -> list[dict]:
    return DOEScScraper().scrape()
