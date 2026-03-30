"""AMEOSC - Associacao dos Municipios do Extremo Oeste de SC.

Organiza concursos para municipios do oeste catarinense.
URL: https://www.ameosc.org.br
"""
from automacao.bancas.base import scrape_banca

BASE_URL = "https://www.ameosc.org.br"
PAGES = [
    BASE_URL + "/concursos",
    BASE_URL + "/processos-seletivos",
]

def scrape_ameosc() -> list[dict]:
    return scrape_banca("AMEOSC", BASE_URL, PAGES)
