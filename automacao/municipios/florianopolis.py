"""Scraper Florianopolis - portal RH da PMF."""
from automacao.municipios.base import DiarioMunicipal


class Florianopolis(DiarioMunicipal):
    nome = "Prefeitura de Florianopolis"
    fonte = "PMF-SC"
    base_url = "https://www.pmf.sc.gov.br"
    pages = [
        "https://www.pmf.sc.gov.br/entidades/rh/index.php?cms=concursos+publicos",
    ]
