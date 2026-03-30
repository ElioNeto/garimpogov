from automacao.bancas.base import scrape_banca
BASE_URL = "https://portalfaurgs.com.br"
PAGES = [BASE_URL + "/concursosfaurgs", "https://www.faurgs.com.br/concursos/"]
def scrape_faurgs(): return scrape_banca("FAURGS", BASE_URL, PAGES)
