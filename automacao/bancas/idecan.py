from automacao.bancas.base import scrape_banca
BASE_URL = "https://idecan.org.br"
PAGES = [BASE_URL + "/concursos", BASE_URL + "/concursos/inscricoes-abertas"]
def scrape_idecan(): return scrape_banca("IDECAN", BASE_URL, PAGES)
