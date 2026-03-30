"""PCI Concursos - coleta HTML, sem Gemini."""
import logging
import time
import requests

logger = logging.getLogger(__name__)

BASE_URL = "https://www.pciconcursos.com.br"
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/120 Safari/537.36",
    "Accept-Language": "pt-BR,pt;q=0.9",
}
PAGES = [
    BASE_URL + "/concursos/",
    BASE_URL + "/concursos/regiao-sul/0/0/0/0/0/0/0/1/ti/",
    BASE_URL + "/concursos/regiao-sul/0/0/0/0/0/0/0/1/informatica/",
    BASE_URL + "/concursos/regiao-sul/0/0/0/0/0/0/0/1/ingles/",
    BASE_URL + "/concursos/nacional/0/0/0/0/0/0/0/1/ti/",
    BASE_URL + "/concursos/nacional/0/0/0/0/0/0/0/1/informatica/",
    BASE_URL + "/concursos/nacional/0/0/0/0/0/0/0/1/ingles/",
]


def scrape_pci() -> list[tuple[str, str, str]]:
    session = requests.Session()
    session.headers.update(HEADERS)
    results = []
    for url in PAGES:
        try:
            r = session.get(url, timeout=30)
            r.raise_for_status()
            results.append((r.text, BASE_URL, "PCI"))
            logger.info(f"PCI [{url}]: HTML coletado")
            time.sleep(1)
        except Exception as e:
            logger.warning(f"PCI [{url}]: {e}")
    return results
