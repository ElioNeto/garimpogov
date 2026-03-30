from automacao.bancas.base import scrape_banca

BASE_URL = "https://www.concursosfcc.com.br"

PAGES = [
    BASE_URL + "/concursos/abertos-ativos",
    BASE_URL + "/concursos/inscricoes-abertas",
]


def scrape_fcc() -> list[dict]:
    return scrape_banca("FCC", BASE_URL, PAGES)
