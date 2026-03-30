"""FAURGS - Fundacao de Apoio da UFRGS (RS).

Organiza concursos para UFRGS, IFRS, Banrisul, TJ-RS, TCE-RS, etc.
URL real com concursos listados: https://portalfaurgs.com.br/concursosfaurgs
"""
from automacao.bancas.base import scrape_banca

BASE_URL = "https://portalfaurgs.com.br"
PAGES = [
    BASE_URL + "/concursosfaurgs",
    "https://www.faurgs.com.br/concursos/",
]

def scrape_faurgs() -> list[dict]:
    return scrape_banca("FAURGS", BASE_URL, PAGES)
