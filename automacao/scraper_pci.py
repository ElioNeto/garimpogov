"""Scraper PCI Concursos - parse direto do HTML via Gemini.

URLs de busca por area:
  https://www.pciconcursos.com.br/concursos/
  (filtrar por nivel=superior e area na pagina)
"""
import logging
import re
import time
from datetime import date

import requests
from bs4 import BeautifulSoup

from automacao.ai_extractor import extract_concursos_from_html

logger = logging.getLogger(__name__)

BASE_URL = "https://www.pciconcursos.com.br"
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/120 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml",
    "Accept-Language": "pt-BR,pt;q=0.9",
}

# Paginas de busca com escopo relevante
PAGES = [
    BASE_URL + "/concursos/",
    BASE_URL + "/concursos/nacional/0/0/0/0/0/0/0/1/ti/",
    BASE_URL + "/concursos/nacional/0/0/0/0/0/0/0/1/tecnologia/",
    BASE_URL + "/concursos/nacional/0/0/0/0/0/0/0/1/informatica/",
    BASE_URL + "/concursos/nacional/0/0/0/0/0/0/0/1/ingles/",
    BASE_URL + "/concursos/regiao-sul/0/0/0/0/0/0/0/1/ti/",
    BASE_URL + "/concursos/regiao-sul/0/0/0/0/0/0/0/1/informatica/",
    BASE_URL + "/concursos/regiao-sul/0/0/0/0/0/0/0/1/ingles/",
]


def scrape_pci() -> list[dict]:
    session = requests.Session()
    session.headers.update(HEADERS)
    all_concursos = []
    seen = set()

    for url in PAGES:
        try:
            r = session.get(url, timeout=30)
            r.raise_for_status()
            results = extract_concursos_from_html(r.text, base_url=BASE_URL, fonte="PCI")
            for c in results:
                key = c.get("link_edital", "") or c.get("instituicao", "")
                if key not in seen:
                    seen.add(key)
                    all_concursos.append(c)
            logger.info(f"PCI [{url}]: {len(results)} concursos no escopo")
            time.sleep(4)
        except Exception as e:
            logger.error(f"Erro PCI [{url}]: {e}")

    logger.info(f"PCI total no escopo: {len(all_concursos)}")
    return all_concursos
