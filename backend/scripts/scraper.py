"""Scraper module for GarimpoGov.

Currently targets PCI Concursos (https://www.pciconcursos.com.br) as a starting point.
Extends by adding more sources in the SOURCES list.

Extracts links directly from HTML, then uses Gemini only to parse structured data.
"""
import json
import logging
import os
import re
import time

import google.generativeai as genai
import requests
from bs4 import BeautifulSoup
from tenacity import retry, stop_after_attempt, wait_exponential

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

genai.configure(api_key=os.environ["GEMINI_API_KEY"])

GEMINI_MODEL = "gemini-2.5-flash-lite"
BASE_URL = "https://www.pciconcursos.com.br"

SOURCES = [
    {
        "name": "PCI Concursos",
        "url": "https://www.pciconcursos.com.br/concursos/",
    },
]

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    )
}


@retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=2, max=10))
def fetch_page(url: str) -> str:
    logger.info(f"Fetching {url}")
    response = requests.get(url, headers=HEADERS, timeout=30)
    response.raise_for_status()
    return response.text


def parse_pci_concursos(html: str) -> list[dict]:
    """
    Parse PCI Concursos HTML directly.
    Each concurso entry is a <a> tag linking to /concurso/<slug>/
    with surrounding text containing institution, cargo, salary, deadline.
    """
    soup = BeautifulSoup(html, "lxml")
    concursos = []

    # PCI Concursos: each entry is a table row or div containing an anchor
    # to /concurso/ paths. We find all anchors pointing to concurso pages.
    links = soup.find_all("a", href=re.compile(r"/concurso/"))
    logger.info(f"Found {len(links)} anchor links to concurso pages")

    for a_tag in links:
        href = a_tag.get("href", "")
        if not href:
            continue

        # Build full URL
        if href.startswith("http"):
            full_url = href
        else:
            full_url = BASE_URL + href

        # The institution name is usually the anchor text
        instituicao = a_tag.get_text(separator=" ", strip=True)
        if not instituicao:
            continue

        # Walk up to find the parent container with more details
        parent = a_tag.find_parent(["tr", "li", "div", "p", "td"])
        context_text = parent.get_text(separator=" ", strip=True) if parent else instituicao

        # Extract deadline (DD/MM/YYYY pattern)
        date_match = re.search(r"(\d{2}/\d{2}/\d{4})", context_text)
        data_encerramento = date_match.group(1) if date_match else None

        # Extract salary (R$ pattern)
        salary_match = re.search(r"R\$\s?[\d\.]+(?:,\d{2})?", context_text)
        salario_maximo = salary_match.group(0) if salary_match else None

        # Extract state (2-letter abbreviation)
        state_match = re.search(
            r"\b(AC|AL|AP|AM|BA|CE|DF|ES|GO|MA|MT|MS|MG|PA|PB|PR|PE|PI|RJ|RN|RS|RO|RR|SC|SP|SE|TO)\b",
            context_text
        )
        orgao = state_match.group(1) if state_match else None

        concursos.append({
            "instituicao": instituicao,
            "orgao": orgao,
            "cargos": [],
            "salario_maximo": salario_maximo,
            "link_edital": full_url,
            "data_encerramento": data_encerramento,
            "status": "aberto",
        })

    return concursos


def scrape_all_sources() -> list[dict]:
    """Scrape all configured sources and return list of concurso dicts."""
    all_concursos = []

    for source in SOURCES:
        try:
            html = fetch_page(source["url"])
            concursos = parse_pci_concursos(html)
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
