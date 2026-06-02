"""BaseScraper: classe base unificada para todos os scrapers.

Elimina a duplicação de HEADERS, loop de páginas, dedup e sleep
que antes estava replicada em cada scraper individual.
"""
import logging
import random
import socket
import time
import warnings
from abc import ABC
from typing import Optional
from urllib.parse import urlparse

import cloudscraper
import requests
from requests.adapters import HTTPAdapter
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type
from requests.exceptions import HTTPError, ConnectionError, Timeout

from automacao.ai_extractor import extract_concursos_from_html
from automacao.config import DEFAULT_HEADERS, USER_AGENTS, random_delay

logger = logging.getLogger(__name__)


def _hostname_resolves(hostname: str, timeout: float = 2.0, retries: int = 2) -> bool:
    """Verifica se um hostname resolve via DNS. Sem cache — cada chamada refaz a consulta."""
    if not hostname:
        return False
    for attempt in range(retries):
        try:
            socket.setdefaulttimeout(timeout)
            socket.getaddrinfo(hostname, 443)
            return True
        except (socket.gaierror, OSError):
            if attempt == retries - 1:
                return False
            time.sleep(0.5)
        finally:
            socket.setdefaulttimeout(None)
    return False

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
        # cloudscraper bypassa Cloudflare; fallback para requests puro
        try:
            session = cloudscraper.create_scraper()
        except Exception:
            session = requests.Session()
        headers = dict(DEFAULT_HEADERS)  # copia para não modificar o original
        headers["User-Agent"] = random.choice(USER_AGENTS)
        session.headers.update(headers)
        # NÃO usar urllib3.Retry aqui — o tenacity já cuida das retentativas
        # e o Retry duplicado causa timeout excessivo em domínios mortos
        adapter = HTTPAdapter(max_retries=0)
        session.mount("https://", adapter)
        session.mount("http://", adapter)
        if not self.verify_ssl:
            session.verify = False
        return session

    @retry(
        stop=stop_after_attempt(2),
        wait=wait_exponential(multiplier=1, min=1, max=10),
        retry=retry_if_exception_type((HTTPError, ConnectionError, Timeout)),
    )
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
            # DNS pre-check rápido: pula imediatamente se o domínio não resolver.
            # Sem cache — cada URL verifica de novo (o DNS pode ficar bom entre tentativas).
            hostname = urlparse(url).hostname
            if hostname and not _hostname_resolves(hostname):
                logger.warning(f"{self.nome} DNS não resolve para {hostname}, pulando {url}")
                continue

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
