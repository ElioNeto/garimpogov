"""Diário Oficial de Blumenau.

Portal: https://www.blumenau.sc.gov.br/secretarias/sad/concursos-publicos
"""
import logging
import re

import requests
from bs4 import BeautifulSoup

from automacao.filters import matches_scope
from automacao.municipios.base import DiarioMunicipal, HEADERS

logger = logging.getLogger(__name__)


class Blumenau(DiarioMunicipal):
    nome = "Prefeitura de Blumenau"
    fonte = "PMBlumenau-SC"
    base_url = "https://www.blumenau.sc.gov.br"
    search_url = "https://www.blumenau.sc.gov.br/secretarias/sad/concursos-publicos"

    def build_params(self, term: str, data_inicio: str, data_fim: str) -> dict:
        return {}

    def parse_html(self, html: str) -> list[dict]:
        soup = BeautifulSoup(html, "lxml")
        concursos = []

        links = (
            soup.find_all("a", href=re.compile(r"concurso|edital|selecao", re.I)) or
            soup.select("div.field-items a") or
            soup.select("ul.menu a")
        )

        for a in links:
            titulo = a.get_text(strip=True)
            href = a.get("href", "")
            if not href or not titulo:
                continue
            link = href if href.startswith("http") else self.base_url + href

            entry = {
                "instituicao": self.nome,
                "orgao": "Blumenau - SC",
                "cargos": [titulo],
                "salario_maximo": None,
                "link_edital": link,
                "data_encerramento": None,
                "status": "aberto",
                "fonte": self.fonte,
            }
            if matches_scope(entry):
                concursos.append(entry)

        return concursos

    def scrape(self) -> list[dict]:
        logger.info(f"Scraping {self.fonte}...")
        try:
            r = requests.get(self.search_url, headers=HEADERS, timeout=30)
            r.raise_for_status()
            results = self.parse_html(r.text)
            seen = set()
            unique = [c for c in results if c["link_edital"] not in seen and not seen.add(c["link_edital"])]
            logger.info(f"{self.fonte} total: {len(unique)}")
            return unique
        except Exception as e:
            logger.error(f"Erro {self.fonte}: {e}")
            return []
