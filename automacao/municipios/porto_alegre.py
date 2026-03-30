"""Diário Oficial de Porto Alegre - DOPA.

Portal: http://dopaonlineupload.procempa.com.br
Busca: https://dopaonline.procempa.com.br/#/pesquisa

O DOPA usa uma SPA Angular — fallback via portal de concursos da PMPA.
"""
import logging
import re
import time
from datetime import date, timedelta

import requests
from bs4 import BeautifulSoup
from tenacity import retry, stop_after_attempt, wait_exponential

from automacao.filters import matches_scope
from automacao.municipios.base import DiarioMunicipal, SEARCH_TERMS, HEADERS

logger = logging.getLogger(__name__)


class PortoAlegre(DiarioMunicipal):
    nome = "Prefeitura de Porto Alegre"
    fonte = "DOPA-POA"
    # Portal de concursos da PMPA (mais acessível que o DOPA SPA)
    base_url = "https://prefeitura.poa.br"
    search_url = "https://prefeitura.poa.br/sma/concursos-e-selecoes"

    def build_params(self, term: str, data_inicio: str, data_fim: str) -> dict:
        return {}  # página estática, sem params de busca

    def parse_html(self, html: str) -> list[dict]:
        soup = BeautifulSoup(html, "lxml")
        concursos = []

        # Links de editais de concursos na página da PMPA
        links = (
            soup.find_all("a", href=re.compile(r"concurso|edital|selecao", re.I)) or
            soup.select("div.view-content a") or
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
                "orgao": "Porto Alegre - RS",
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
            # Deduplica
            seen = set()
            unique = []
            for c in results:
                if c["link_edital"] not in seen:
                    seen.add(c["link_edital"])
                    unique.append(c)
            logger.info(f"{self.fonte} total: {len(unique)}")
            return unique
        except Exception as e:
            logger.error(f"Erro {self.fonte}: {e}")
            return []
