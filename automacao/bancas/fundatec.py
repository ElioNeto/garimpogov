"""FUNDATEC - principal banca do RS.

Responsavel por: IPE PREV RS, IFSC, CRP RS, prefeituras gauchas, etc.
URL: https://www.fundatec.org.br
"""
from automacao.bancas.base import scrape_banca

BASE_URL = "https://www.fundatec.org.br"

PAGES = [
    BASE_URL + "/home/concursos/index",
    BASE_URL + "/home/concursos/index?tipo=aberto",
]


def scrape_fundatec() -> list[dict]:
    return scrape_banca("FUNDATEC", BASE_URL, PAGES)
