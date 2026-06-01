"""CONSULPLAN - banca com atuação nacional (IBGE, TRFs, prefeituras).

URL: https://www.consulplan.net
"""
from automacao.bancas.base import scrape_banca

BASE_URL = "https://www.consulplan.net"

PAGES = [
    BASE_URL + "/concursos",
    BASE_URL + "/concursos/em-andamento",
    BASE_URL + "/concursos/inscricoes-abertas",
]


def scrape_consulplan() -> list[dict]:
    return scrape_banca("CONSULPLAN", BASE_URL, PAGES)
