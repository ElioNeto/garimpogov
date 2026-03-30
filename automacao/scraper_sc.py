"""Scraper Diario Oficial do Estado de SC (DOESC) - extracao via Gemini."""
import logging
import time
from datetime import date, timedelta

import requests
from tenacity import retry, stop_after_attempt, wait_exponential

from automacao.ai_extractor import extract_concursos_from_html

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

BASE_URL = "https://www.doe.sea.sc.gov.br"
SEARCH_URL = BASE_URL + "/buscapublicacao"
HEADERS = {"User-Agent": "Mozilla/5.0 GarimpoGov/1.0"}

SEARCH_TERMS = [
    "concurso publico tecnologia informacao",
    "concurso publico professor ingles",
    "edital concurso TI superior",
]


@retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=4, max=20))
def _fetch(params: dict) -> str:
    r = requests.get(SEARCH_URL, params=params, headers=HEADERS, timeout=30)
    r.raise_for_status()
    return r.text


def scrape_doesc() -> list[dict]:
    hoje = date.today()
    data_inicio = (hoje - timedelta(days=30)).strftime("%d/%m/%Y")
    data_fim = hoje.strftime("%d/%m/%Y")

    all_concursos = []
    seen = set()

    for term in SEARCH_TERMS:
        try:
            html = _fetch({"q": term, "dtInicio": data_inicio, "dtFim": data_fim})
            results = extract_concursos_from_html(html, base_url=BASE_URL, fonte="DOESC")
            for c in results:
                if c["link_edital"] not in seen:
                    seen.add(c["link_edital"])
                    all_concursos.append(c)
            time.sleep(4)
        except Exception as e:
            logger.error(f"Erro DOESC '{term}': {e}")

    logger.info(f"DOESC total: {len(all_concursos)}")
    return all_concursos
