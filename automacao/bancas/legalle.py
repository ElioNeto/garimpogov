from automacao.bancas.base import scrape_banca
BASE_URL = "https://www.institutolegalle.com.br"
PAGES = [BASE_URL + "/concursos", BASE_URL + "/concursos/abertos"]
def scrape_legalle(): return scrape_banca("Legalle", BASE_URL, PAGES)
