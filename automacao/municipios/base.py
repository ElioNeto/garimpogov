"""Classe base abstrata para scrapers de diários municipais."""
from abc import ABC, abstractmethod
import logging
import re
import time
from datetime import date, timedelta

import requests
from bs4 import BeautifulSoup
from tenacity import retry, stop_after_attempt, wait_exponential

from automacao.filters import matches_scope

logger = logging.getLogger(__name__)

HEADERS = {"User-Agent": "Mozilla/5.0 GarimpoGov/1.0"}

SEARCH_TERMS = [
    "concurso público tecnologia informação",
    "concurso público analista TI",
    "concurso público professor inglês",
    "edital concurso superior",
]


class DiarioMunicipal(ABC):
    nome: str = ""
    base_url: str = ""
    search_url: str = ""
    fonte: str = ""

    @abstractmethod
    def build_params(self, term: str, data_inicio: str, data_fim: str) -> dict:
        """Monta os query params para a busca."""
        ...

    def parse_html(self, html: str) -> list[dict]:
        """Parse padrão — pode ser sobrescrito por subclasses."""
        soup = BeautifulSoup(html, "lxml")
        concursos = []

        items = (
            soup.select("div.resultado") or
            soup.select("div.search-result") or
            soup.select("article") or
            soup.select("li.item") or
            soup.find_all("a", href=re.compile(r"/(edital|concurso|ato|publicacao)"))
        )

        for item in items:
            titulo, link, orgao = "", "", ""

            if item.name == "a":
                titulo = item.get_text(strip=True)
                href = item.get("href", "")
                link = href if href.startswith("http") else self.base_url + href
            else:
                a_tag = item.find("a")
                if a_tag:
                    titulo = a_tag.get_text(strip=True)
                    href = a_tag.get("href", "")
                    link = href if href.startswith("http") else self.base_url + href
                else:
                    titulo = item.get_text(separator=" ", strip=True)[:200]

            if not titulo or not link:
                continue

            entry = {
                "instituicao": orgao or self.nome,
                "orgao": self.nome,
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

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=4, max=20))
    def _fetch(self, params: dict) -> str:
        r = requests.get(self.search_url, params=params, headers=HEADERS, timeout=30)
        r.raise_for_status()
        return r.text

    def scrape(self) -> list[dict]:
        hoje = date.today()
        data_inicio = (hoje - timedelta(days=30)).strftime("%d/%m/%Y")
        data_fim = hoje.strftime("%d/%m/%Y")

        all_results = []
        seen = set()

        for term in SEARCH_TERMS:
            try:
                params = self.build_params(term, data_inicio, data_fim)
                html = self._fetch(params)
                results = self.parse_html(html)
                for c in results:
                    if c["link_edital"] not in seen:
                        seen.add(c["link_edital"])
                        all_results.append(c)
                logger.info(f"{self.fonte} '{term}': {len(results)} no escopo")
                time.sleep(3)
            except Exception as e:
                logger.error(f"Erro {self.fonte} '{term}': {e}")

        logger.info(f"{self.fonte} total: {len(all_results)}")
        return all_results
