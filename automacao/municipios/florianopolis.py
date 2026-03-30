"""Scraper Florianopolis.

Portal RH: https://www.pmf.sc.gov.br/entidades/rh/
Concursos: listados na pagina de RH
"""
from automacao.municipios.base import DiarioMunicipal


class Florianopolis(DiarioMunicipal):
    nome = "Prefeitura de Florianopolis"
    fonte = "PMF-SC"
    base_url = "https://www.pmf.sc.gov.br"
    timeout = 45
    pages = [
        "https://www.pmf.sc.gov.br/entidades/rh/index.php?cms=concursos+publicos",
        "https://www.pmf.sc.gov.br/entidades/rh/index.php?cms=selecao+publica",
    ]
