"""FURB - Fundacao Universidade Regional de Blumenau (SC).

Organiza concursos para municipios do Vale do Itajai e regiao.
URL: https://www.furb.br/concursos
"""
from automacao.bancas.base import scrape_banca

BASE_URL = "https://www.furb.br"
PAGES = [
    BASE_URL + "/web/1/1/extra/concurso-publico/geral/1/index.html",
    BASE_URL + "/concursos",
]

def scrape_furb() -> list[dict]:
    return scrape_banca("FURB", BASE_URL, PAGES)
