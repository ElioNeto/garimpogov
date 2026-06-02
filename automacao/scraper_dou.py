"""Scraper DOU - usa endpoint de pesquisa correto do IN.gov.br.

O endpoint real usado pelo portal eh via POST no SOLR interno.
Fallback: scraping da pagina de busca HTML + Gemini para extrair.
"""
import logging
from datetime import date, timedelta

from tenacity import retry, stop_after_attempt, wait_exponential

from automacao.ai_extractor import extract_concursos_from_html
from automacao.config import DOU_SEARCH_TERMS
from automacao.scraper_base import BaseScraper

logger = logging.getLogger(__name__)

# URL correta da pesquisa do DOU (retorna HTML, nao JSON)
DOU_SEARCH_URL = "https://www.in.gov.br/consulta/-/buscar/dou"
BASE_URL = "https://www.in.gov.br"


class DOUScraper(BaseScraper):
    nome = "DOU"
    base_url = DOU_SEARCH_URL

    def __init__(self, days_back: int = 30):
        self.days_back = days_back

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=2, min=5, max=30))
    def _fetch_page(self, url: str) -> str:
        return super()._fetch_page(url)

    def _fetch_dou(self, term: str, data_inicio: str, data_fim: str) -> str:
        params = {
            "q": term,
            "exactDate": "personalizado",
            "published": data_inicio,
            "endDate": data_fim,
            "s": "todos",
            "p": 1,
        }
        return self._make_session().get(DOU_SEARCH_URL, params=params, timeout=self.timeout).text

    def scrape(self) -> list[dict]:
        hoje = date.today()
        data_fim = hoje.strftime("%d/%m/%Y")
        data_inicio = (hoje - timedelta(days=self.days_back)).strftime("%d/%m/%Y")

        all_concursos = []
        seen = set()

        for term in DOU_SEARCH_TERMS:
            logger.info(f"DOU buscando: '{term}'")
            try:
                html = self._fetch_dou(term, data_inicio, data_fim)
                results = extract_concursos_from_html(html, base_url=BASE_URL, fonte="DOU")
                for c in results:
                    key = c.get("link_edital", "") or c.get("instituicao", "")
                    if key not in seen:
                        seen.add(key)
                        all_concursos.append(c)
                logger.info(f"DOU '{term}': {len(results)} extraidos")
            except Exception as e:
                logger.error(f"Erro DOU [{term}]: {e}")

        logger.info(f"DOU total extraido: {len(all_concursos)}")
        return all_concursos


def scrape_dou(days_back: int = 30) -> list[dict]:
    return DOUScraper(days_back=days_back).scrape()
