"""Pipeline principal de ingestao.

Fontes:
  1. Portais agregadores: PCI Concursos, QConcursos, Estrategia Concursos
  2. Bancas do Sul: FUNDATEC, FEPESE, FGV, CEBRASPE, Legalle, FAFIPA, CS-UFG, AOCP
"""
import logging
import sys

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

    all_raw: list[dict] = []

    # 1. Portais agregadores
    logger.info("[1/2] Portais agregadores (PCI + QConcursos + Estrategia)")
    all_raw += scrape_pci()
    all_raw += scrape_qconcursos()
    all_raw += scrape_estrategia()

    # 2. Bancas do Sul
    logger.info("[2/2] Bancas organizadoras da regiao Sul")
    for fn in ALL_BANCAS:
        try:
            all_raw += fn()
        except Exception as e:
            logger.error(f"Erro banca {fn.__name__}: {e}")

    logger.info(f"Total bruto no escopo: {len(all_raw)}")

    new_count = ingest_concursos(all_raw)
    commit_report(all_raw, new_count)

    logger.info(f"=== Pipeline DONE: {new_count} novos concursos ===")


if __name__ == "__main__":
    run()
