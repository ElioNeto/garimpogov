"""Scraper Caxias do Sul.

Portal: https://www.caxias.rs.gov.br/concursos/
Alternativa via SMARh: https://smrh.caxias.rs.gov.br
"""
from automacao.municipios.base import DiarioMunicipal


class CaxiasDoSul(DiarioMunicipal):
    nome = "Prefeitura de Caxias do Sul"
    fonte = "PMCaxias-RS"
    base_url = "https://www.caxias.rs.gov.br"
    timeout = 45
    pages = [
        "https://www.caxias.rs.gov.br/concursos/",
        "https://www.caxias.rs.gov.br/site/conteudo/concursos-publicos",
    ]
