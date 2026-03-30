from automacao.bancas.base import scrape_banca
BASE_URL = "https://quadrix.org.br"
PAGES = [BASE_URL + "/concursos", BASE_URL + "/concursos/abertos"]
def scrape_quadrix(): return scrape_banca("Quadrix", BASE_URL, PAGES)
