"""Scraper Joinville - portal de concursos."""
from automacao.municipios.base import DiarioMunicipal


class Joinville(DiarioMunicipal):
    nome = "Prefeitura de Joinville"
    fonte = "PMJ-SC"
    base_url = "https://www.joinville.sc.gov.br"
    pages = [
        "https://www.joinville.sc.gov.br/servicos/concursos-publicos/",
    ]
