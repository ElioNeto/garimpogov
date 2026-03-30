"""ACAFE - Associacao Catarinense das Fundacoes Educacionais (SC).

Organiza concursos para municipios e autarquias de SC.
URL: https://www.acafe.org.br/new/index.php?cdProcessoSeletivo=concurso
"""
from automacao.bancas.base import scrape_banca

BASE_URL = "https://www.acafe.org.br"
PAGES = [
    BASE_URL + "/new/index.php?cdProcessoSeletivo=concurso",
    BASE_URL + "/new/index.php",
]

def scrape_acafe() -> list[dict]:
    return scrape_banca("ACAFE", BASE_URL, PAGES)
