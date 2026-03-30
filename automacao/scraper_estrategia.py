"""Scraper Estrategia Concursos - concursos com inscricoes abertas.

URL: https://www.estrategiaconcursos.com.br/concursos/abertos/
Lista concursos com titulo, orgao, banca, inscricoes e link do edital.
"""
import logging
import time

import requests

from automacao.ai_extractor import extract_concursos_from_html

logger = logging.getLogger(__name__)

BASE_URL = "https://www.estrategiaconcursos.com.br"
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/120 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml",
    "Accept-Language": "pt-BR,pt;q=0.9",
    "Referer": "https://www.estrategiaconcursos.com.br/",
}

PAGES = [
    BASE_URL + "/concursos/abertos/",
    BASE_URL + "/concursos/abertos/?area=ti",
    BASE_URL + "/concursos/abertos/?area=professor",
]


def scrape_estrategia() -> list[dict]:
    session = requests.Session()
    session.headers.update(HEADERS)
    all_concursos = []
    seen = set()

    for url in PAGES:
        try:
            r = session.get(url, timeout=30)
            r.raise_for_status()
            results = extract_concursos_from_html(r.text, base_url=BASE_URL, fonte="Estrategia")
            for c in results:
                key = c.get("link_edital", "") or c.get("instituicao", "")
                if key not in seen:
                    seen.add(key)
                    all_concursos.append(c)
            logger.info(f"Estrategia [{url}]: {len(results)} no escopo")
            time.sleep(4)
        except Exception as e:
            logger.error(f"Erro Estrategia [{url}]: {e}")

    logger.info(f"Estrategia total: {len(all_concursos)}")
    return all_concursos
