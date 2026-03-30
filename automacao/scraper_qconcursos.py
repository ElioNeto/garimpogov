"""QConcursos - coleta HTML, sem Gemini."""
import logging
import time
import requests

logger = logging.getLogger(__name__)

BASE_URL = "https://www.qconcursos.com"
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/120 Safari/537.36",
    "Accept-Language": "pt-BR,pt;q=0.9",
    "Referer": "https://www.qconcursos.com/",
}
PAGES = [
    BASE_URL + "/concursos/abertos",
    BASE_URL + "/concursos/abertos?area=tecnologia-da-informacao",
    BASE_URL + "/concursos/abertos?area=professor",
]


def scrape_qconcursos() -> list[tuple[str, str, str]]:
    session = requests.Session()
    session.headers.update(HEADERS)
    results = []
    for url in PAGES:
        try:
            r = session.get(url, timeout=30)
            r.raise_for_status()
            results.append((r.text, BASE_URL, "QConcursos"))
            logger.info(f"QConcursos [{url}]: HTML coletado")
            time.sleep(1)
        except Exception as e:
            logger.warning(f"QConcursos [{url}]: {e}")
    return results
