"""Scraper Joinville.

Portal: https://www.joinville.sc.gov.br/concurso-publico/
"""
from automacao.municipios.base import DiarioMunicipal


class Joinville(DiarioMunicipal):
    nome = "Prefeitura de Joinville"
    fonte = "PMJ-SC"
    base_url = "https://www.joinville.sc.gov.br"
    pages = [
        # URL correta
        "https://www.joinville.sc.gov.br/concurso-publico/",
    ]
