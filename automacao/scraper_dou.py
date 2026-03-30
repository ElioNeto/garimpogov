"""Scraper Diário Oficial da União (DOU) - API pública IN.gov.br."""
import logging
import time
from datetime import date, timedelta

import requests
from tenacity import retry, stop_after_attempt, wait_exponential

from automacao.config import DOU_SEARCH_TERMS
from automacao.filters import matches_scope

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# API pública do DOU
DOU_API = "https://www.in.gov.br/consulta/-/buscar/dou"
HEADERS = {
    "User-Agent": "Mozilla/5.0 GarimpoGov/1.0",
    "Accept": "application/json",
}


@retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=4, max=20))
def _search_dou(term: str, data_inicio: str, data_fim: str, page: int = 1) -> dict:
    params = {
        "q": term,
        "exactDate": "personalizado",
        "published": data_inicio,
        "endDate": data_fim,
        "s": "todos",
        "p": page,
        "paginaBaseUrl": DOUP_API,
    }
    r = requests.get(DOU_API, params=params, headers=HEADERS, timeout=30)
    r.raise_for_status()
    return r.json()


def scrape_dou(days_back: int = 7) -> list[dict]:
    """Busca concursos no DOU dos últimos N dias dentro do escopo."""
    hoje = date.today()
    data_fim = hoje.strftime("%d/%m/%Y")
    data_inicio = (hoje - timedelta(days=days_back)).strftime("%d/%m/%Y")

    all_concursos = []
    seen = set()

    for term in DOU_SEARCH_TERMS:
        logger.info(f"DOU buscando: '{term}'")
        try:
            data = _search_dou(term, data_inicio, data_fim)
            items = data.get("items", []) or data.get("results", [])

            for item in items:
                titulo = item.get("title", "") or item.get("titulo", "")
                link = item.get("urlTitle", "") or item.get("link", "")
                orgao = item.get("pubName", "") or item.get("orgao", "")
                data_pub = item.get("pubDate", "") or item.get("data", "")
                resumo = item.get("content", "") or item.get("resumo", "")

                if not link:
                    continue

                # Monta full URL se for relativo
                if link.startswith("/"):
                    link = "https://www.in.gov.br" + link

                entry = {
                    "instituicao": orgao or titulo,
                    "orgao": orgao,
                    "cargos": [titulo],
                    "salario_maximo": None,
                    "link_edital": link,
                    "data_encerramento": None,
                    "status": "aberto",
                    "fonte": "DOU",
                    "resumo": resumo[:500] if resumo else None,
                    "data_publicacao": data_pub,
                }

                if link not in seen and matches_scope(entry):
                    seen.add(link)
                    all_concursos.append(entry)

            time.sleep(3)  # respeita rate limit
        except Exception as e:
            logger.error(f"Erro DOU termo '{term}': {e}")

    logger.info(f"DOU total no escopo: {len(all_concursos)}")
    return all_concursos
