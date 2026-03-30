"""AMAUC - Associacao dos Municipios do Alto Uruguai Catarinense.

Organiza concursos para municipios do Alto Uruguai (SC).
URL: https://www.amauc.org.br
"""
from automacao.bancas.base import scrape_banca

BASE_URL = "https://www.amauc.org.br"
PAGES = [
    BASE_URL + "/concursos",
    BASE_URL + "/processos-seletivos",
]

def scrape_amauc() -> list[dict]:
    return scrape_banca("AMAUC", BASE_URL, PAGES)
