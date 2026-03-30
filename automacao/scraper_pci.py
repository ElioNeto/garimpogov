"""Scraper PCI Concursos - filtra por escopo (TI superior + prof inglês)."""
import logging
import re
import time
from urllib.parse import quote_plus

import requests
from bs4 import BeautifulSoup
from tenacity import retry, stop_after_attempt, wait_exponential

from automacao.config import TARGET_PROFILES
from automacao.filters import matches_scope

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

BASE_URL = "https://www.pciconcursos.com.br"
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

# URLs de busca segmentada por perfil para maximizar resultados
SEARCH_URLS = [
    f"{BASE_URL}/concursos/nacional/0/0/0/0/0/0/0/1/ti/",
    f"{BASE_URL}/concursos/nacional/0/0/0/0/0/0/0/1/tecnologia/",
    f"{BASE_URL}/concursos/nacional/0/0/0/0/0/0/0/1/informatica/",
    f"{BASE_URL}/concursos/nacional/0/0/0/0/0/0/0/1/ingles/",
    f"{BASE_URL}/concursos/nacional/0/0/0/0/0/0/0/1/professor-ingles/",
    f"{BASE_URL}/concursos/",  # fallback geral
]


@retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=2, max=10))
def fetch_page(url: str) -> str:
    logger.info(f"Fetching {url}")
    r = requests.get(url, headers=HEADERS, timeout=30)
    r.raise_for_status()
    return r.text


def parse_page(html: str, source_url: str) -> list[dict]:
    """Extrai concursos de uma página PCI e aplica filtro de escopo."""
    soup = BeautifulSoup(html, "lxml")
    for tag in soup(["script", "style", "nav", "footer", "header"]):
        tag.decompose()

    text = soup.get_text(separator="\n", strip=True)
    lines = [l.strip() for l in text.splitlines() if l.strip()]

    date_pat = re.compile(r"^\d{2}/\d{2}/\d{4}")
    salary_pat = re.compile(r"R\$\s?[\d\.]+,\d{2}")
    state_pat = re.compile(rf"^({STATES})$")

    concursos = []
    for i, line in enumerate(lines):
        if not date_pat.match(line):
            continue

        start = max(0, i - 6)
        block = lines[start:i + 1]

        instituicao = None
        orgao = None
        cargos = []
        salario = None
        data_encerramento = None
        nivel_keywords = {"Fundamental", "Médio", "Técnico", "Superior", "Ensino"}

        for b in block:
            if state_pat.match(b):
                orgao = b
                continue
            if date_pat.match(b):
                m = re.search(r"\d{2}/\d{2}/\d{4}", b)
                data_encerramento = m.group(0) if m else None
                continue
            sal = salary_pat.search(b)
            if sal:
                salario = sal.group(0)
            if any(k in b for k in nivel_keywords):
                continue
            if instituicao and len(b) > 3 and not sal:
                cargos.append(b)
            if not instituicao and len(b) > 5 and not sal:
                instituicao = b

        if not instituicao:
            continue

        search_term = instituicao.split(" - ")[0].strip()
        link_edital = f"{BASE_URL}/concursos/?q={quote_plus(search_term)}"

        entry = {
            "instituicao": instituicao,
            "orgao": orgao,
            "cargos": cargos[:3],
            "salario_maximo": salario,
            "link_edital": link_edital,
            "data_encerramento": data_encerramento,
            "status": "aberto",
        }

        if matches_scope(entry):
            concursos.append(entry)

    # Deduplicação
    seen = set()
    unique = []
    for c in concursos:
        key = (c["instituicao"], c.get("data_encerramento"))
        if key not in seen:
            seen.add(key)
            unique.append(c)

    return unique


def scrape_pci() -> list[dict]:
    all_concursos = []
    seen_keys = set()

    for url in SEARCH_URLS:
        try:
            html = fetch_page(url)
            results = parse_page(html, url)
            for c in results:
                key = (c["instituicao"], c.get("data_encerramento"))
                if key not in seen_keys:
                    seen_keys.add(key)
                    all_concursos.append(c)
            logger.info(f"PCI [{url}]: {len(results)} concursos no escopo")
            time.sleep(2)
        except Exception as e:
            logger.error(f"Erro ao scraper PCI {url}: {e}")

    logger.info(f"PCI total no escopo: {len(all_concursos)}")
    return all_concursos
