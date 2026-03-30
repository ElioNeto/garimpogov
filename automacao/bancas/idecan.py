"""IDECAN - Instituto de Desenvolvimento Educacional, Cultural e do Cidadao.

Organiza concursos federais e estaduais com atuacao no Sul.
URL: https://idecan.org.br
"""
from automacao.bancas.base import scrape_banca

BASE_URL = "https://idecan.org.br"
PAGES = [
    BASE_URL + "/concursos",
    BASE_URL + "/concursos/inscricoes-abertas",
]

def scrape_idecan() -> list[dict]:
    return scrape_banca("IDECAN", BASE_URL, PAGES)
