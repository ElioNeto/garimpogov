"""Pipeline principal - estrategia BATCH.

Fase 1 (HTTP puro): coleta HTML de todas as fontes em paralelo.
Fase 2 (Gemini):    1 chamada a cada 18k chars de texto consolidado.
Resultado: 2-4 chamadas Gemini por execucao completa.
"""
import logging
import sys

from automacao.ai_extractor import extract_batch
from automacao.bancas import ALL_BANCAS
from automacao.commit_backup import commit_report
from automacao.ingestor import ingest_concursos
from automacao.scraper_estrategia import scrape_estrategia
from automacao.scraper_pci import scrape_pci
from automacao.scraper_qconcursos import scrape_qconcursos

logging.basicConfig(
    level=logging.INFO,
    format="%(levelname)s:%(name)s:%(message)s",
    handlers=[logging.StreamHandler(sys.stdout)],
)
logger = logging.getLogger(__name__)


def run():
    logger.info("=== GarimpoGov Ingestion Pipeline START ===")
    logger.info("Escopo: TI (nivel superior) + Professor de Ingles | Regiao Sul")

    # FASE 1: coleta de HTML (sem Gemini)
    logger.info("[FASE 1] Coletando HTML das fontes...")
    all_pages: list[tuple[str, str, str]] = []

    # Portais agregadores
    all_pages += scrape_pci()
    all_pages += scrape_qconcursos()
    all_pages += scrape_estrategia()

    # Bancas do Sul
    for fn in ALL_BANCAS:
        try:
            all_pages += fn()
        except Exception as e:
            logger.error(f"Erro {fn.__name__}: {e}")

    logger.info(f"[FASE 1] {len(all_pages)} paginas coletadas")

    # FASE 2: extracao via Gemini em batch
    logger.info("[FASE 2] Extraindo concursos via Gemini (batch)...")
    all_raw = extract_batch(all_pages)
    logger.info(f"Total bruto no escopo: {len(all_raw)}")

    # Ingestao
    new_count = ingest_concursos(all_raw)
    commit_report(all_raw, new_count)
    logger.info(f"=== Pipeline DONE: {new_count} novos concursos ===")


if __name__ == "__main__":
    run()
