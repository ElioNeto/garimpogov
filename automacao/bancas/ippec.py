"""IPPEC - Instituto de Pesquisa, Pos-Graduacao e Ensino de Cascavel (PR/SC).

Organiza concursos para municipios do oeste do PR e SC.
URL: https://ippec.org.br/paginas/concursos
"""
from automacao.bancas.base import scrape_banca

BASE_URL = "https://ippec.org.br"
PAGES = [
    BASE_URL + "/paginas/concursos",
    BASE_URL + "/",  # home lista concursos em andamento
]

def scrape_ippec() -> list[dict]:
    return scrape_banca("IPPEC", BASE_URL, PAGES)
