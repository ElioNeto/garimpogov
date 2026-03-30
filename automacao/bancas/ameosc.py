from automacao.bancas.base import scrape_banca
BASE_URL = "https://www.ameosc.org.br"
PAGES = [BASE_URL + "/concursos", BASE_URL + "/processos-seletivos"]
def scrape_ameosc(): return scrape_banca("AMEOSC", BASE_URL, PAGES)
