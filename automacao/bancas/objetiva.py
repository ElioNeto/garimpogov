from automacao.bancas.base import scrape_banca

BASE_URL = "https://www.objetiva.srv.br"

PAGES = [
    BASE_URL + "/concurso_em_aberto/",
]


def scrape_objetiva() -> list[dict]:
    return scrape_banca("OBJETIVA", BASE_URL, PAGES)
