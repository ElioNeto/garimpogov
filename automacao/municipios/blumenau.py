"""Scraper Blumenau - portal de concursos."""
from automacao.municipios.base import DiarioMunicipal


class Blumenau(DiarioMunicipal):
    nome = "Prefeitura de Blumenau"
    fonte = "PMBlumenau-SC"
    base_url = "https://www.blumenau.sc.gov.br"
    pages = [
        "https://www.blumenau.sc.gov.br/secretarias/sad/concursos-publicos",
    ]
