"""VUNESP - Fundacao Vunesp, atuante em todo o Brasil incluindo Sul.

URL: https://www.vunesp.com.br
"""
from automacao.bancas.base import scrape_banca

BASE_URL = "https://www.vunesp.com.br"
PAGES = [
    BASE_URL + "/VUNESP/site/concursos.aspx",
]

def scrape_vunesp() -> list[dict]:
    return scrape_banca("VUNESP", BASE_URL, PAGES)
