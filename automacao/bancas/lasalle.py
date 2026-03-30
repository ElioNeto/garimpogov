from automacao.bancas.base import scrape_banca
BASE_URL = "https://fundacaolasalle.org.br"
PAGES = [BASE_URL + "/concursos/"]
def scrape_lasalle(): return scrape_banca("La Salle", BASE_URL, PAGES)
