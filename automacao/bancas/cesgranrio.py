"""CESGRANRIO - uma das maiores bancas do Brasil.

Atuação: Petrobras, Caixa Econômica, IBGE, BNDES, CNEN, etc.
URL: https://www.cesgranrio.org.br
"""
from automacao.bancas.base import scrape_banca

BASE_URL = "https://www.cesgranrio.org.br"

PAGES = [
    BASE_URL + "/concursos",
    BASE_URL + "/concursos/abertos",
    BASE_URL + "/concursos/andamento",
]


def scrape_cesgranrio() -> list[dict]:
    return scrape_banca("CESGRANRIO", BASE_URL, PAGES)
