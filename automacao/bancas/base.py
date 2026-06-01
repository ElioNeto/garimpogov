"""Base para scrapers de bancas organizadoras.

Usa BaseScraper internamente (B16) mas mantém a API funcional
`scrape_banca(nome, base_url, pages)` para compatibilidade com
todos os scrapers de banca existentes.
"""
import logging

from automacao.scraper_base import BaseScraper

logger = logging.getLogger(__name__)


class _BancaScraper(BaseScraper):
    """Wrapper interno que adapta os parâmetros da função ao BaseScraper."""
    def __init__(self, nome: str, base_url: str, pages: list[str], verify_ssl: bool = True, timeout: int = 30):
        self.nome = nome
        self.base_url = base_url
        self.pages = pages
        self.verify_ssl = verify_ssl
        self.timeout = timeout


def scrape_banca(nome: str, base_url: str, pages: list[str], verify_ssl: bool = True, timeout: int = 30) -> list[dict]:
    """Executa scraping de uma banca organizadora.

    Args:
        nome: Identificador da fonte (ex: "FGV")
        base_url: URL base do site
        pages: Lista de URLs a visitar
        verify_ssl: Verificar SSL (default True)
        timeout: Timeout da requisição (default 30s)

    Returns:
        Lista de concursos encontrados no escopo.
    """
    scraper = _BancaScraper(nome, base_url, pages, verify_ssl, timeout)
    return scraper.scrape()
