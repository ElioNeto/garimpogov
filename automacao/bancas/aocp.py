"""AOCP - banca atuante em PR, SC e RS (UFFS, UTFPR, municipios).

URL: https://www.aocp.com.br
"""
from automacao.bancas.base import scrape_banca

BASE_URL = "https://www.aocp.com.br"

PAGES = [
    BASE_URL + "/concursos",
    BASE_URL + "/concursos/em-andamento",
]


def scrape_aocp() -> list[dict]:
    return scrape_banca("AOCP", BASE_URL, PAGES)
