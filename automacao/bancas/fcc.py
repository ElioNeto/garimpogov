from automacao.bancas.base import scrape_banca
BASE_URL = "https://www.concursosfcc.com.br"
PAGES = [BASE_URL + "/concursos/abertos-ativos"]
def scrape_fcc(): return scrape_banca("FCC", BASE_URL, PAGES)
