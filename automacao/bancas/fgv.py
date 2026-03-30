"""FGV Conhecimento - atuante em SC e PR (TCE SC, TJ SC, etc.).

URL: https://conhecimento.fgv.br
"""
from automacao.bancas.base import scrape_banca

BASE_URL = "https://conhecimento.fgv.br"

PAGES = [
    BASE_URL + "/concursos/abertos",
    BASE_URL + "/concursos",
]


def scrape_fgv() -> list[dict]:
    return scrape_banca("FGV", BASE_URL, PAGES)
