"""Scraper Diário Oficial do Estado de SC (DOESC).

Portal: https://www.doe.sea.sc.gov.br
Estratégia: busca por termo via GET, filtra por escopo.
"""
import logging
import re
import time
from datetime import date, timedelta

import requests
from bs4 import BeautifulSoup
from tenacity import retry, stop_after_attempt, wait_exponential

from automacao.filters import matches_scope

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

BASE_URL = "https://www.doe.sea.sc.gov.br"
SEARCH_URL = BASE_URL + "/buscapublicacao"
HEADERS = {"User-Agent": "Mozilla/5.0 GarimpoGov/1.0"}

SEARCH_TERMS = [
    "concurso público tecnologia informação",
    "concurso público analista sistemas",
    "concurso público professor inglês",
    "edital concurso TI superior",
]


@retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=4, max=20))
def _fetch(url: str, params: dict) -> str:
    r = requests.get(url, params=params, headers=HEADERS, timeout=30)
    r.raise_for_status()
    return r.text


def _parse_results(html: str) -> list[dict]:
    soup = BeautifulSoup(html, "lxml")
    concursos = []

    items = (
        soup.select("div.publicacao") or
        soup.select("div.resultado") or
        soup.select("div.search-item") or
        soup.select("article") or
        soup.find_all("a", href=re.compile(r"/(publicacao|ato|edital|concurso)"))
    )

    for item in items:
        titulo = ""
        link = ""
        orgao = ""

        if item.name == "a":
            titulo = item.get_text(strip=True)
            href = item.get("href", "")
            link = href if href.startswith("http") else BASE_URL + href
        else:
            a_tag = item.find("a")
            if a_tag:
                titulo = a_tag.get_text(strip=True)
                href = a_tag.get("href", "")
                link = href if href.startswith("http") else BASE_URL + href
            else:
                titulo = item.get_text(separator=" ", strip=True)[:200]

            orgao_tag = item.find(class_=re.compile(r"orgao|organ|entidade"))
            if orgao_tag:
                orgao = orgao_tag.get_text(strip=True)

        if not titulo or not link:
            continue

        entry = {
            "instituicao": orgao or titulo,
            "orgao": orgao or "SC",
            "cargos": [titulo],
            "salario_maximo": None,
            "link_edital": link,
            "data_encerramento": None,
            "status": "aberto",
            "fonte": "DOESC",
        }

        if matches_scope(entry):
            concursos.append(entry)

    return concursos


def scrape_doesc() -> list[dict]:
    hoje = date.today()
    data_inicio = (hoje - timedelta(days=30)).strftime("%d/%m/%Y")
    data_fim = hoje.strftime("%d/%m/%Y")

    all_concursos = []
    seen = set()

    for term in SEARCH_TERMS:
        try:
            params = {
                "q": term,
                "dtInicio": data_inicio,
                "dtFim": data_fim,
            }
            html = _fetch(SEARCH_URL, params)
            results = _parse_results(html)
            for c in results:
                if c["link_edital"] not in seen:
                    seen.add(c["link_edital"])
                    all_concursos.append(c)
            logger.info(f"DOESC '{term}': {len(results)} no escopo")
            time.sleep(3)
        except Exception as e:
            logger.error(f"Erro DOESC '{term}': {e}")

    logger.info(f"DOESC total: {len(all_concursos)}")
    return all_concursos
