"""Instituto Legalle - banca do RS (Badesul, municipios gaucho).

URL: https://www.institutolegalle.com.br
"""
from automacao.bancas.base import scrape_banca

BASE_URL = "https://www.institutolegalle.com.br"

PAGES = [
    BASE_URL + "/concursos",
    BASE_URL + "/concursos/abertos",
]


def scrape_legalle() -> list[dict]:
    return scrape_banca("Legalle", BASE_URL, PAGES)
