from automacao.bancas.base import scrape_banca
BASE_URL = "https://www.amauc.org.br"
PAGES = [BASE_URL + "/concursos", BASE_URL + "/processos-seletivos"]
def scrape_amauc(): return scrape_banca("AMAUC", BASE_URL, PAGES)
