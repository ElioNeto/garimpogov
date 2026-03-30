from automacao.bancas.base import scrape_banca
BASE_URL = "https://fepese.org.br"
PAGES = [BASE_URL + "/concursos-e-selecoes", BASE_URL + "/concursos-e-selecoes?tipo=aberto"]
def scrape_fepese(): return scrape_banca("FEPESE", BASE_URL, PAGES)
