from automacao.bancas.base import scrape_banca
BASE_URL = "https://www.ieses.org.br"
PAGES = [BASE_URL + "/concursos", BASE_URL + "/concursos/inscricoes-abertas"]
def scrape_ieses(): return scrape_banca("IESES", BASE_URL, PAGES)
