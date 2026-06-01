"""IADES - Instituto Americano de Desenvolvimento.

Atuação: EBSERH, SES, conselhos regionais, prefeituras.
URL: https://www.iades.org.br
"""
from automacao.bancas.base import scrape_banca

BASE_URL = "https://www.iades.org.br"

PAGES = [
    BASE_URL + "/concursos",
    BASE_URL + "/concursos/abertos",
    BASE_URL + "/concursos/inscricoes-abertas",
]


def scrape_iades() -> list[dict]:
    return scrape_banca("IADES", BASE_URL, PAGES)
