"""Scraper module for GarimpoGov.

Currently targets PCI Concursos (https://www.pciconcursos.com.br) as a starting point.
Extends by adding more sources in the SOURCES list.

Uses Gemini with structured output to extract relevant data from HTML.
"""
import json
import logging
import os
import time
from typing import Optional

import google.generativeai as genai
import requests
from bs4 import BeautifulSoup
from tenacity import retry, stop_after_attempt, wait_exponential

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

genai.configure(api_key=os.environ["GEMINI_API_KEY"])

SOURCES = [
    {
        "name": "PCI Concursos",
        "url": "https://www.pciconcursos.com.br/concursos/",
        "selector": "div.cc",
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
    """Fetch HTML content from URL with retries."""
    logger.info(f"Fetching {url}")
    response = requests.get(url, headers=HEADERS, timeout=30)
    response.raise_for_status()
    return response.text


def extract_concursos_with_gemini(html_snippet: str, source_name: str) -> list[dict]:
    """Use Gemini to extract structured concurso data from HTML."""
    prompt = f"""Analise o seguinte HTML de um site de concursos publicos brasileiros ({source_name})
e extraia informacoes sobre os concursos listados.

Retorne um JSON array com objetos no formato:
{{
  "instituicao": "nome do orgao/instituicao",
  "cargos": ["cargo1", "cargo2"],
  "salario_maximo": "valor em R$ ou null",
  "link_edital": "URL completa do edital ou pagina do concurso",
  "data_encerramento": "DD/MM/YYYY ou null",
  "status": "aberto"
}}

Se nao encontrar informacao, use null.
Retorne APENAS o JSON array, sem markdown, sem texto adicional.

HTML:
{html_snippet[:8000]}
"""

    model = genai.GenerativeModel("gemini-2.0-flash")
    response = model.generate_content(prompt)
    text = response.text.strip()

    # Clean possible markdown code fences
    if text.startswith("```"):
        text = text.split("```")[1]
        if text.startswith("json"):
            text = text[4:]

    try:
        data = json.loads(text)
        return data if isinstance(data, list) else []
    except json.JSONDecodeError as e:
        logger.error(f"JSON parse error: {e}\nRaw response: {text[:500]}")
        return []


def scrape_all_sources() -> list[dict]:
    """Scrape all configured sources and return list of concurso dicts."""
    all_concursos = []

    for source in SOURCES:
        try:
            html = fetch_page(source["url"])
            soup = BeautifulSoup(html, "lxml")

            elements = soup.select(source["selector"])
            if elements:
                snippet = "\n".join(str(el) for el in elements[:50])
            else:
                snippet = soup.get_text(separator="\n", strip=True)[:8000]

            concursos = extract_concursos_with_gemini(snippet, source["name"])
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
