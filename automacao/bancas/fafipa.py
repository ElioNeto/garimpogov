"""FAFIPA - banca do Parana (Foz do Iguacu, municipios paranaenses).

URL: https://www.fafipa.org
"""
from automacao.bancas.base import scrape_banca

BASE_URL = "https://www.fafipa.org"

PAGES = [
    BASE_URL + "/concursos-abertos",
    BASE_URL + "/concursos",
]


def scrape_fafipa() -> list[dict]:
    return scrape_banca("FAFIPA", BASE_URL, PAGES)
