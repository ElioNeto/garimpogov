from automacao.bancas.base import scrape_banca
BASE_URL = "https://ippec.org.br"
PAGES = [BASE_URL + "/paginas/concursos", BASE_URL + "/"]
def scrape_ippec(): return scrape_banca("IPPEC", BASE_URL, PAGES)
