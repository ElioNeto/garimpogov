"""Scraper QConcursos - pagina de concursos abertos.

URL: https://www.qconcursos.com/concursos/abertos
O site lista concursos com titulo, banca e link - bom para Gemini extrair.
"""
import logging
import time

import requests

from automacao.ai_extractor import extract_concursos_from_html

logger = logging.getLogger(__name__)

BASE_URL = "https://www.qconcursos.com"
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/120 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml",
    "Accept-Language": "pt-BR,pt;q=0.9",
    "Referer": "https://www.qconcursos.com/",
}

PAGES = [
    BASE_URL + "/concursos/abertos",
    BASE_URL + "/concursos/abertos?area=tecnologia-da-informacao",
    BASE_URL + "/concursos/abertos?area=professor",
]


def scrape_qconcursos() -> list[dict]:
    session = requests.Session()
    session.headers.update(HEADERS)
    all_concursos = []
    seen = set()

    for url in PAGES:
        try:
            r = session.get(url, timeout=30)
            r.raise_for_status()
            results = extract_concursos_from_html(r.text, base_url=BASE_URL, fonte="QConcursos")
            for c in results:
                key = c.get("link_edital", "") or c.get("instituicao", "")
                if key not in seen:
                    seen.add(key)
                    all_concursos.append(c)
            logger.info(f"QConcursos [{url}]: {len(results)} no escopo")
            time.sleep(4)
        except Exception as e:
            logger.error(f"Erro QConcursos [{url}]: {e}")

    logger.info(f"QConcursos total: {len(all_concursos)}")
    return all_concursos
