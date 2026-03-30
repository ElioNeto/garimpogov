from automacao.bancas.base import scrape_banca
BASE_URL = "https://www.acafe.org.br"
PAGES = [BASE_URL + "/new/index.php?cdProcessoSeletivo=concurso"]
def scrape_acafe(): return scrape_banca("ACAFE", BASE_URL, PAGES)
