"""Quadrix - banca nacional com concursos em CFO, CRM, conselhos (Sul).

URL: https://quadrix.org.br
"""
from automacao.bancas.base import scrape_banca

BASE_URL = "https://quadrix.org.br"
PAGES = [
    BASE_URL + "/concursos",
    BASE_URL + "/concursos/abertos",
]

def scrape_quadrix() -> list[dict]:
    return scrape_banca("Quadrix", BASE_URL, PAGES)
