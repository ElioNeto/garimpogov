"""BaseScraper: classe base unificada para todos os scrapers.

Elimina a duplicação de HEADERS, loop de páginas, dedup e sleep
que antes estava replicada em cada scraper individual.
"""
import logging
import random
import time
import warnings
from abc import ABC
from typing import Optional

import requests
from requests.adapters import HTTPAdapter
from tenacity import retry, stop_after_attempt, wait_exponential
from urllib3.util.retry import Retry

from automacao.ai_extractor import extract_concursos_from_html
from automacao.config import DEFAULT_HEADERS, USER_AGENTS, random_delay

logger = logging.getLogger(__name__)

# Suprime warnings de SSL para sites com certificado problemático
warnings.filterwarnings("ignore", message="Unverified HTTPS request")


class BaseScraper(ABC):
    """
    Classe base para scrapers de concursos.

    Subclasses devem definir:
    - nome: identificador da fonte (ex: "PCI")
    - base_url: URL base do site
    - pages: lista de URLs a visitar
    Opcional:
    - timeout: timeout da requisição (default 30)
    - verify_ssl: verificar SSL (default True)
    """

    nome: str = ""
    base_url: str = ""
    pages: list[str] = []
    timeout: int = 30
    verify_ssl: bool = True

    def _make_session(self) -> requests.Session:
        session = requests.Session()
        headers = dict(DEFAULT_HEADERS)  # copia para não modificar o original
        headers["User-Agent"] = random.choice(USER_AGENTS)
        session.headers.update(headers)
        retry_cfg = Retry(
            total=3,
            backoff_factor=2,
            status_forcelist=[429, 500, 502, 503, 504],
            allowed_methods=["GET"],
        )
        adapter = HTTPAdapter(max_retries=retry_cfg)
        session.mount("https://", adapter)
        session.mount("http://", adapter)
        if not self.verify_ssl:
            session.verify = False
        return session

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=2, min=5, max=30))
    def _fetch_page(self, url: str) -> str:
        session = self._make_session()
        r = session.get(url, timeout=self.timeout)
        r.raise_for_status()
        return r.text

    def scrape(self) -> list[dict]:
        """Executa o scraping de todas as páginas definidas.

        Returns:
            Lista de concursos encontrados (TODOS, sem filtro de escopo).
        """
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
                    # Chave composta: fonte + link_edital + instituicao
                    # Evita colapsar 20 concursos diferentes que tenham mesmo link generico
                    link = c.get("link_edital", "") or ""
                    inst = c.get("instituicao", "") or ""
                    key = f"{self.nome}|{link}|{inst}"
                    if key not in seen:
                        seen.add(key)
                        all_concursos.append(c)
                logger.info(f"{self.nome} [{url}]: {len(results)} extraidos")
            except Exception as e:
                logger.error(f"Erro {self.nome} [{url}]: {e}")

            # Pausa aleatória entre requisições (anti-bot)
            delay = random_delay()
            logger.debug(f"{self.nome} aguardando {delay:.1f}s...")
            time.sleep(delay)

        logger.info(f"{self.nome} total: {len(all_concursos)}")
        return all_concursos
