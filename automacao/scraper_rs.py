"""Scraper Diário Oficial do Estado do RS (DOERS).

Portal: https://www.diariooficial.rs.gov.br
Estratégia: busca por termo via formulário GET, filtra por escopo.
"""
import logging
import re
import time
from datetime import date, timedelta

import requests
from bs4 import BeautifulSoup
from tenacity import retry, stop_after_attempt, wait_exponential

from automacao.filters import matches_scope
from automacao.config import TARGET_PROFILES

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

BASE_URL = "https://www.diariooficial.rs.gov.br"
SEARCH_URL = BASE_URL + "/busca"
HEADERS = {"User-Agent": "Mozilla/5.0 GarimpoGov/1.0"}

# Termos de busca no DOERS
SEARCH_TERMS = [
    "concurso público tecnologia informação",
    "concurso público analista sistemas",
    "concurso público professor inglês",
    "edital concurso TI",
]


@retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=4, max=20))
def _fetch(url: str, params: dict) -> str:
    r = requests.get(url, params=params, headers=HEADERS, timeout=30)
    r.raise_for_status()
    return r.text


def _parse_results(html: str, fonte: str) -> list[dict]:
    soup = BeautifulSoup(html, "lxml")
    concursos = []

    # Tenta múltiplos seletores comuns em portais de diários estaduais
    items = (
        soup.select("div.resultado-busca") or
        soup.select("div.search-result") or
        soup.select("li.resultado") or
        soup.select("article") or
        soup.select("tr.resultado")
    )

    if not items:
        # Fallback: extrai todos os links que parecem atos
        items = soup.find_all("a", href=re.compile(r"/(ato|atos|publicacao|edital|concurso)"))

    for item in items:
        titulo = ""
        link = ""
        orgao = ""
        data_pub = ""

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

            orgao_tag = item.find(class_=re.compile(r"orgao|organ|fonte"))
            if orgao_tag:
                orgao = orgao_tag.get_text(strip=True)

            data_tag = item.find(class_=re.compile(r"data|date"))
            if data_tag:
                data_pub = data_tag.get_text(strip=True)

        if not titulo or not link:
            continue

        entry = {
            "instituicao": orgao or titulo,
            "orgao": orgao or fonte,
            "cargos": [titulo],
            "salario_maximo": None,
            "link_edital": link,
            "data_encerramento": None,
            "data_publicacao": data_pub,
            "status": "aberto",
            "fonte": fonte,
        }

        if matches_scope(entry):
            concursos.append(entry)

    return concursos


def scrape_doers() -> list[dict]:
    hoje = date.today()
    data_inicio = (hoje - timedelta(days=30)).strftime("%d/%m/%Y")
    data_fim = hoje.strftime("%d/%m/%Y")

    all_concursos = []
    seen = set()

    for term in SEARCH_TERMS:
        try:
            params = {
                "q": term,
                "dataInicio": data_inicio,
                "dataFim": data_fim,
            }
            html = _fetch(SEARCH_URL, params)
            results = _parse_results(html, "DOERS")
            for c in results:
                if c["link_edital"] not in seen:
                    seen.add(c["link_edital"])
                    all_concursos.append(c)
            logger.info(f"DOERS '{term}': {len(results)} no escopo")
            time.sleep(3)
        except Exception as e:
            logger.error(f"Erro DOERS '{term}': {e}")

    logger.info(f"DOERS total: {len(all_concursos)}")
    return all_concursos
