"""Scraper Blumenau.

Portal: https://www.blumenau.sc.gov.br/governo/secretarias/gestao-publica/concurso-publico
"""
from automacao.municipios.base import DiarioMunicipal


class Blumenau(DiarioMunicipal):
    nome = "Prefeitura de Blumenau"
    fonte = "PMBlumenau-SC"
    base_url = "https://www.blumenau.sc.gov.br"
    pages = [
        "https://www.blumenau.sc.gov.br/governo/secretarias/gestao-publica/concurso-publico",
    ]
