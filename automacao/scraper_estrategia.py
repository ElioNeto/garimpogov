"""Scraper Estrategia Concursos - concursos com inscricoes abertas.

URL: https://www.estrategiaconcursos.com.br/concursos/abertos/
Lista concursos com titulo, orgao, banca, inscricoes e link do edital.

Usa Playwright para renderizar JS e obter o HTML completo.
Requer: ``playwright install chromium`` (executar uma vez apos instalar a lib).
"""
import asyncio
import logging

from playwright.async_api import async_playwright
from tenacity import retry, stop_after_attempt, wait_exponential

from automacao.scraper_base import BaseScraper

logger = logging.getLogger(__name__)

BASE_URL = "https://www.estrategiaconcursos.com.br"


class EstrategiaScraper(BaseScraper):
    nome = "Estrategia"
    base_url = BASE_URL
    pages = [
        BASE_URL + "/concursos/abertos/",
        BASE_URL + "/concursos/abertos/?area=ti",
        BASE_URL + "/concursos/abertos/?area=professor",
    ]

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=2, min=5, max=30))
    def _fetch_page(self, url: str) -> str:
        """Busca o HTML renderizado via Playwright.

        O metodo base (requests) nao funciona porque o Estrategia
        carrega o conteudo dinamicamente com JavaScript.

        Nota: Se chamado de dentro de um loop de eventos existente,
        ``asyncio.run()`` falhara. Nesse caso, refatore ``scrape()``
        para ser async ou use ``asyncio.get_event_loop().run_until_complete()``.
        """
        async def _inner() -> str:
            async with async_playwright() as p:
                browser = await p.chromium.launch(
                    headless=True,
                    args=["--no-sandbox"],
                )
                context = await browser.new_context(
                    viewport={"width": 1280, "height": 800},
                )
                page = await context.new_page()
                await page.goto(url, wait_until="networkidle", timeout=30000)
                html = await page.content()
                await browser.close()
                return html

        return asyncio.run(_inner())


def scrape_estrategia() -> list[dict]:
    return EstrategiaScraper().scrape()
