"""Scraper Porto Alegre - portal de concursos da PMPA."""
from automacao.municipios.base import DiarioMunicipal


class PortoAlegre(DiarioMunicipal):
    nome = "Prefeitura de Porto Alegre"
    fonte = "DOPA-POA"
    base_url = "https://prefeitura.poa.br"
    pages = [
        "https://prefeitura.poa.br/sma/concursos-e-selecoes",
        "https://prefeitura.poa.br/sma/concursos-e-selecoes?page=1",
    ]
