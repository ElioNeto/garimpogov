"""Pipeline principal de ingestao.

Fontes:
  1. PCI Concursos
  2. QConcursos
  3. Estrategia Concursos
  4. Bancas: CEBRASPE, FGV, FCC, VUNESP, IBFC, CS-UFG, OBJETIVA
  5. DOU
  6. DOERS + DOESC
  7. Municipios
"""
import logging
import sys

from automacao.bancas import ALL_BANCAS
from automacao.commit_backup import commit_report
from automacao.ingestor import ingest_concursos
from automacao.municipios.blumenau import Blumenau
from automacao.municipios.caxias_do_sul import CaxiasDoSul
from automacao.municipios.florianopolis import Florianopolis
from automacao.municipios.joinville import Joinville
from automacao.municipios.porto_alegre import PortoAlegre
from automacao.scraper_dou import scrape_dou
from automacao.scraper_estrategia import scrape_estrategia
from automacao.scraper_pci import scrape_pci
from automacao.scraper_qconcursos import scrape_qconcursos
from automacao.scraper_rs import scrape_doers
from automacao.scraper_sc import scrape_doesc

logging.basicConfig(
    level=logging.INFO,
    format="%(levelname)s:%(name)s:%(message)s",
    handlers=[logging.StreamHandler(sys.stdout)],
)
logger = logging.getLogger(__name__)


def run():
    logger.info("=== GarimpoGov Ingestion Pipeline START ===")
    logger.info("Escopo: TI (nivel superior) + Professor de Ingles")

    all_raw: list[dict] = []

    # 1. Portais agregadores
    logger.info("[1/4] Portais agregadores (PCI + QConcursos + Estrategia)")
    all_raw += scrape_pci()
    all_raw += scrape_qconcursos()
    all_raw += scrape_estrategia()

    # 2. Bancas organizadoras
    logger.info("[2/4] Bancas organizadoras")
    for fn in ALL_BANCAS:
        try:
            all_raw += fn()
        except Exception as e:
            logger.error(f"Erro banca {fn.__name__}: {e}")

    # 3. Diarios oficiais
    logger.info("[3/4] Diarios Oficiais (DOU + DOERS + DOESC)")
    all_raw += scrape_dou()
    all_raw += scrape_doers()
    all_raw += scrape_doesc()

    # 4. Municipios
    logger.info("[4/4] Municipios")
    for cls in [PortoAlegre, Florianopolis, Joinville, CaxiasDoSul, Blumenau]:
        try:
            all_raw += cls().scrape()
        except Exception as e:
            logger.error(f"Erro {cls.__name__}: {e}")

    logger.info(f"Total bruto no escopo: {len(all_raw)}")

    # Ingestao no banco
    new_count = ingest_concursos(all_raw)

    # Backup no Git
    commit_report(all_raw, new_count)

    logger.info(f"=== Pipeline DONE: {new_count} novos concursos ===")


if __name__ == "__main__":
    run()
