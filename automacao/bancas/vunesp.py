from automacao.bancas.base import scrape_banca
BASE_URL = "https://www.vunesp.com.br"
PAGES = [BASE_URL + "/VUNESP/site/concursos.aspx"]
def scrape_vunesp(): return scrape_banca("VUNESP", BASE_URL, PAGES)
