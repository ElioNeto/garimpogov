from automacao.bancas.base import scrape_banca

BASE_URL = "https://www.ibfc.org.br"

PAGES = [
    BASE_URL + "/concursos/abertos",
    BASE_URL + "/noticias/concursos-abertos",
]


def scrape_ibfc() -> list[dict]:
    return scrape_banca("IBFC", BASE_URL, PAGES)
