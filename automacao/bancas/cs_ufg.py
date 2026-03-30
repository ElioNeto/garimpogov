"""CS-UFG - organiza concursos de universidades federais do Sul (UFFS, etc.).

URL: https://cs.ufg.br
"""
from automacao.bancas.base import scrape_banca

BASE_URL = "https://cs.ufg.br"

PAGES = [
    BASE_URL + "/p/concursos-em-andamento",
]


def scrape_cs_ufg() -> list[dict]:
    return scrape_banca("CS-UFG", BASE_URL, PAGES)
