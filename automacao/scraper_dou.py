"""Scraper Diario Oficial da Uniao (DOU) - API publica + Gemini para filtragem.

A API do DOU retorna JSON estruturado; usamos Gemini apenas para validar
se o ato e realmente um edital de concurso no escopo, evitando falsos positivos.
"""
import json
import logging
import os
import time
from datetime import date, timedelta

import requests
from tenacity import retry, stop_after_attempt, wait_exponential

from automacao.ai_extractor import extract_concursos_from_text
from automacao.config import DOU_SEARCH_TERMS

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

DOU_API = "https://www.in.gov.br/consulta/-/buscar/dou"
HEADERS = {"User-Agent": "Mozilla/5.0 GarimpoGov/1.0", "Accept": "application/json"}


@retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=2, min=5, max=30))
def _search_dou(term: str, data_inicio: str, data_fim: str) -> list:
    params = {
        "q": term,
        "exactDate": "personalizado",
        "published": data_inicio,
        "endDate": data_fim,
        "s": "todos",
        "p": 1,
    }
    r = requests.get(DOU_API, params=params, headers=HEADERS, timeout=30)
    r.raise_for_status()
    data = r.json()
    return data.get("items", []) or data.get("results", [])


def scrape_dou(days_back: int = 7) -> list[dict]:
    hoje = date.today()
    data_fim = hoje.strftime("%d/%m/%Y")
    data_inicio = (hoje - timedelta(days=days_back)).strftime("%d/%m/%Y")

    all_items = []
    seen_links = set()

    for term in DOU_SEARCH_TERMS:
        logger.info(f"DOU buscando: '{term}'")
        try:
            items = _search_dou(term, data_inicio, data_fim)
            # Monta texto estruturado para o Gemini analisar
            text_block = "\n\n".join(
                f"Titulo: {i.get('title','')}\n"
                f"Orgao: {i.get('pubName','')}\n"
                f"Data: {i.get('pubDate','')}\n"
                f"URL: {i.get('urlTitle','') or i.get('link','')}\n"
                f"Resumo: {str(i.get('content',''))[:400]}"
                for i in items
                if i.get("title")
            )
            if not text_block:
                continue

            results = extract_concursos_from_text(
                text_block, base_url="https://www.in.gov.br", fonte="DOU"
            )
            for c in results:
                if c["link_edital"] not in seen_links:
                    seen_links.add(c["link_edital"])
                    all_items.append(c)

            time.sleep(3)
        except Exception as e:
            logger.error(f"Erro DOU '{term}': {e}")

    logger.info(f"DOU total no escopo: {len(all_items)}")
    return all_items
