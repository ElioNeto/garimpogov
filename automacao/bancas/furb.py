from automacao.bancas.base import scrape_banca
BASE_URL = "https://www.furb.br"
PAGES = [BASE_URL + "/web/1/1/extra/concurso-publico/geral/1/index.html"]
def scrape_furb(): return scrape_banca("FURB", BASE_URL, PAGES)
