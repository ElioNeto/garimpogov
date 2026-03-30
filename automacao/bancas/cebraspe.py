from automacao.bancas.base import scrape_banca

BASE_URL = "https://www.cebraspe.org.br"

PAGES = [
    BASE_URL + "/concursos",
    BASE_URL + "/concursos/CEBRASPE_CONCURSOS_ABERTOS",
]


def scrape_cebraspe() -> list[dict]:
    return scrape_banca("CEBRASPE", BASE_URL, PAGES)
