"""IESES - Instituto de Estudos Superiores (SC/RS).

Organiza concursos para TRT, TJ, cartórios e municipios do Sul.
URL: https://www.ieses.org.br
"""
from automacao.bancas.base import scrape_banca

BASE_URL = "https://www.ieses.org.br"
PAGES = [
    BASE_URL + "/concursos",
    BASE_URL + "/concursos/inscricoes-abertas",
]

def scrape_ieses() -> list[dict]:
    return scrape_banca("IESES", BASE_URL, PAGES)
