"""Scraper Tec Concursos - maior portal de concursos do Brasil.

URL: https://www.tecconcursos.com.br/concursos
O site é Angular SPA (renderiza via JS), então usa Playwright.

Necessário: playwright install chromium

Áreas-alvo: TI, tecnologia, professor de inglês
"""
import asyncio
import logging

from playwright.async_api import async_playwright

from automacao.ai_extractor import extract_concursos_from_html
from automacao.scraper_base import BaseScraper

logger = logging.getLogger(__name__)

BASE_URL = "https://www.tecconcursos.com.br"

# Termos de busca especializados para o Tec Concursos
SEARCH_TERMS = [
    "tecnologia+da+informacao",
    "analista+de+sistemas",
    "desenvolvedor",
    "professor+de+ingles",
    "professor+de+lingua+inglesa",
    "tecnologia",
    "informatica",
]


class TecConcursosScraper(BaseScraper):
    nome = "TecConcursos"
    base_url = BASE_URL
    pages = [
        BASE_URL + "/concursos",
        *(BASE_URL + f"/concursos?q={t}" for t in SEARCH_TERMS),
    ]

    async def _fetch_page_async(self, url: str) -> str:
        async with async_playwright() as p:
            browser = await p.chromium.launch(
                headless=True,
                args=["--no-sandbox", "--disable-setuid-sandbox"],
            )
            context = await browser.new_context(
                viewport={"width": 1280, "height": 800},
                user_agent=(
                    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) "
                    "Chrome/120.0.0.0 Safari/537.36"
                ),
            )
            page = await context.new_page()
            await page.goto(url, wait_until="networkidle", timeout=30000)
            # Espera Angular renderizar
            await page.wait_for_timeout(3000)
            content = await page.content()
            await browser.close()
            return content

    def _fetch_page(self, url: str) -> str:
        return asyncio.run(self._fetch_page_async(url))


def scrape_tec() -> list[dict]:
    return TecConcursosScraper().scrape()
