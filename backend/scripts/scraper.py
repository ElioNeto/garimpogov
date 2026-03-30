"""Scraper module for GarimpoGov.

PCI Concursos retorna texto puro (sem links HTML) via requests.
Estrategia: parsear o texto estruturado diretamente com regex.
Link do edital: URL de busca no PCI baseada no nome da instituicao.
"""
import json
import logging
import os
import re
import time
from urllib.parse import quote_plus

import requests
from bs4 import BeautifulSoup
from tenacity import retry, stop_after_attempt, wait_exponential

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

BASE_URL = "https://www.pciconcursos.com.br"
SEARCH_URL = BASE_URL + "/concursos/?q="

SOURCES = [
    {
        "name": "PCI Concursos",
        "url": BASE_URL + "/concursos/",
    },
]

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    )
}

STATES = (
    "AC|AL|AP|AM|BA|CE|DF|ES|GO|MA|MT|MS|MG"
    "|PA|PB|PR|PE|PI|RJ|RN|RS|RO|RR|SC|SP|SE|TO"
)


@retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=2, max=10))
def fetch_page(url: str) -> str:
    logger.info(f"Fetching {url}")
    response = requests.get(url, headers=HEADERS, timeout=30)
    response.raise_for_status()
    return response.text


def parse_pci_text(html: str) -> list[dict]:
    """
    Parseia o texto da pagina PCI Concursos.
    Cada bloco de concurso tem o padrao:
      Nome da Instituicao
      [UF]  (opcional, para concursos estaduais)
      [X vagas] [ate R$ Y,YY]
      Cargos
      Nivel
      DD/MM/YYYY  (data encerramento)
    """
    soup = BeautifulSoup(html, "lxml")
    # Remove scripts e estilos
    for tag in soup(["script", "style", "nav", "footer", "header"]):
        tag.decompose()

    text = soup.get_text(separator="\n", strip=True)
    lines = [l.strip() for l in text.splitlines() if l.strip()]

    concursos = []
    i = 0
    date_pattern = re.compile(r"^\d{2}/\d{2}/\d{4}")
    salary_pattern = re.compile(r"R\$\s?[\d\.]+,\d{2}")
    vagas_pattern = re.compile(r"(\d+)\s+vaga")
    state_pattern = re.compile(rf"^({STATES})$")

    while i < len(lines):
        line = lines[i]

        # Linha de data indica fim de um bloco de concurso
        # Tentamos capturar o bloco das linhas anteriores
        if date_pattern.match(line):
            # Retroage para montar o bloco: pega ate 6 linhas anteriores
            start = max(0, i - 6)
            block = lines[start:i + 1]

            # Instituicao: primeira linha do bloco que nao seja UF, vaga, salario ou nivel
            instituicao = None
            orgao = None
            cargos = []
            salario = None
            vagas_count = None

            nivel_keywords = {"Fundamental", "Médio", "Técnico", "Superior", "Ensino"}

            for b_line in block:
                # Estado
                if state_pattern.match(b_line):
                    orgao = b_line
                    continue
                # Data de encerramento
                if date_pattern.match(b_line):
                    data_enc = re.search(r"\d{2}/\d{2}/\d{4}", b_line)
                    data_encerramento = data_enc.group(0) if data_enc else None
                    continue
                # Salario
                sal = salary_pattern.search(b_line)
                if sal:
                    salario = sal.group(0)
                # Vagas
                vag = vagas_pattern.search(b_line)
                if vag:
                    vagas_count = int(vag.group(1))
                # Nivel de escolaridade -> nao e instituicao nem cargo util
                if any(k in b_line for k in nivel_keywords):
                    continue
                # Linha com cargo (geralmente apos instituicao)
                if instituicao and not orgao and len(b_line) > 3 and not sal and not vag:
                    cargos.append(b_line)
                # Primeira linha relevante = instituicao
                if not instituicao and len(b_line) > 5 and not sal and not vag:
                    instituicao = b_line

            if not instituicao:
                i += 1
                continue

            # Monta URL de busca no PCI para este concurso
            search_term = instituicao.split(" - ")[0].strip()
            link_edital = SEARCH_URL + quote_plus(search_term)

            concursos.append({
                "instituicao": instituicao,
                "orgao": orgao,
                "cargos": cargos[:3],  # limita a 3 cargos
                "salario_maximo": salario,
                "link_edital": link_edital,
                "data_encerramento": data_encerramento if 'data_encerramento' in dir() else None,
                "status": "aberto",
            })

        i += 1

    # Remove duplicatas por instituicao+data
    seen = set()
    unique = []
    for c in concursos:
        key = (c["instituicao"], c.get("data_encerramento"))
        if key not in seen:
            seen.add(key)
            unique.append(c)

    logger.info(f"Parsed {len(unique)} unique concursos")
    return unique


def scrape_all_sources() -> list[dict]:
    all_concursos = []
    for source in SOURCES:
        try:
            html = fetch_page(source["url"])
            concursos = parse_pci_text(html)
            logger.info(f"Found {len(concursos)} concursos from {source['name']}")
            all_concursos.extend(concursos)
            time.sleep(2)
        except Exception as e:
            logger.error(f"Error scraping {source['name']}: {e}")
            continue
    return all_concursos


if __name__ == "__main__":
    results = scrape_all_sources()
    logger.info(f"Total concursos found: {len(results)}")
    print(json.dumps(results, ensure_ascii=False, indent=2))
