"""Fundacao La Salle - prefeituras gauchas e entidades de classe (RS).

URL: https://fundacaolasalle.org.br/concursos/
"""
from automacao.bancas.base import scrape_banca

BASE_URL = "https://fundacaolasalle.org.br"
PAGES = [
    BASE_URL + "/concursos/",
]

def scrape_lasalle() -> list[dict]:
    return scrape_banca("La Salle", BASE_URL, PAGES)
