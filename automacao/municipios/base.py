"""Classe base para scrapers municipais com extracao via LLM.

Usa session com headers de browser real, User-Agent rotativo e retry.
"""
from abc import ABC
import logging
import random
import socket
import time
import warnings
from urllib.parse import urlparse

import cloudscraper
import requests
from requests.adapters import HTTPAdapter

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


def _make_session(verify_ssl: bool = True) -> requests.Session:
    # cloudscraper bypassa Cloudflare; fallback para requests puro
    try:
        session = cloudscraper.create_scraper()
    except Exception:
        session = requests.Session()
    headers = dict(DEFAULT_HEADERS)  # copia para não modificar o original
    headers["User-Agent"] = random.choice(USER_AGENTS)
    headers["Connection"] = "keep-alive"
    session.headers.update(headers)
    # Sem urllib3.Retry — evita timeout excessivo em domínios mortos
    adapter = HTTPAdapter(max_retries=0)
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
            # DNS pre-check rápido: pula imediatamente se o domínio não resolver
            hostname = urlparse(url).hostname
            if hostname and not _hostname_resolves(hostname):
                logger.warning(f"{self.fonte} DNS não resolve para {hostname}, pulando {url}")
                continue

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
                logger.info(f"{self.fonte} [{url}]: {len(results)} extraidos")

                # Pausa aleatória entre requisições (anti-bot)
                delay = random_delay()
                logger.debug(f"{self.fonte} aguardando {delay:.1f}s...")
                time.sleep(delay)
            except Exception as e:
                logger.error(f"Erro {self.fonte} [{url}]: {e}")

        logger.info(f"{self.fonte} total: {len(all_results)}")
        return all_results
