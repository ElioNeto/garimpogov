"""Scraper PCI Concursos - parse direto do HTML via Gemini.

URLs de busca por area:
  https://www.pciconcursos.com.br/concursos/
  (filtrar por nivel=superior e area na pagina)
"""
import logging

from automacao.scraper_base import BaseScraper

logger = logging.getLogger(__name__)

BASE_URL = "https://www.pciconcursos.com.br"


class PCIScraper(BaseScraper):
    nome = "PCI"
    base_url = BASE_URL
    pages = [
        BASE_URL + "/concursos/",
        BASE_URL + "/concursos/nacional/0/0/0/0/0/0/0/1/ti/",
        BASE_URL + "/concursos/nacional/0/0/0/0/0/0/0/1/tecnologia/",
        BASE_URL + "/concursos/nacional/0/0/0/0/0/0/0/1/informatica/",
        BASE_URL + "/concursos/nacional/0/0/0/0/0/0/0/1/ingles/",
        BASE_URL + "/concursos/regiao-sul/0/0/0/0/0/0/0/1/ti/",
        BASE_URL + "/concursos/regiao-sul/0/0/0/0/0/0/0/1/informatica/",
        BASE_URL + "/concursos/regiao-sul/0/0/0/0/0/0/0/1/ingles/",
    ]


def scrape_pci() -> list[dict]:
    return PCIScraper().scrape()
