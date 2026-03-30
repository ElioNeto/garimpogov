"""Scraper Caxias do Sul - portal de concursos."""
from automacao.municipios.base import DiarioMunicipal


class CaxiasDoSul(DiarioMunicipal):
    nome = "Prefeitura de Caxias do Sul"
    fonte = "PMCaxias-RS"
    base_url = "https://www.caxias.rs.gov.br"
    pages = [
        "https://www.caxias.rs.gov.br/concursos",
    ]
