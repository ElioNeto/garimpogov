"""Scraper Porto Alegre.

Portal de concursos da PMPA:
https://prefeitura.poa.br/smgae/concursos-publicos
"""
from automacao.municipios.base import DiarioMunicipal


class PortoAlegre(DiarioMunicipal):
    nome = "Prefeitura de Porto Alegre"
    fonte = "DOPA-POA"
    base_url = "https://prefeitura.poa.br"
    pages = [
        # URL correta do portal de concursos da PMPA
        "https://prefeitura.poa.br/smgae/concursos-publicos",
    ]
