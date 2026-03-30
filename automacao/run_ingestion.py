"""Orquestrador principal da ingestão - chamado pelo GitHub Actions."""
import logging
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from automacao.scraper_pci import scrape_pci
from automacao.scraper_dou import scrape_dou
from automacao.pdf_processor import process_pdf
from automacao.vector_store import (
    get_db_connection,
    concurso_exists,
    insert_concurso,
    insert_chunks,
)
from automacao.commit_backup import generate_report, save_and_commit_report

# Helpers de parse reutilizados do backend
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "backend"))
from app.utils.helpers import parse_salary, parse_date

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)

DRY_RUN = os.environ.get("DRY_RUN", "false").lower() == "true"


def run():
    logger.info("=== GarimpoGov Ingestion Pipeline START ===")
    logger.info(f"Modo: {'DRY RUN' if DRY_RUN else 'PRODUÇÃO'}")
    logger.info("Escopo: TI (nível superior) + Professor de Inglês")

    # 1. Coleta de fontes
    concursos_raw = []
    concursos_raw.extend(scrape_pci())
    concursos_raw.extend(scrape_dou(days_back=7))

    logger.info(f"Total bruto no escopo: {len(concursos_raw)}")

    if DRY_RUN:
        logger.info("[DRY RUN] Pulando gravação no banco.")
        for c in concursos_raw[:5]:
            logger.info(f"  Exemplo: {c['instituicao']} | {c.get('cargos')} | {c.get('link_edital')}")
        return

    conn = get_db_connection()
    newly_ingested = []

    for raw in concursos_raw:
        link = raw.get("link_edital")
        if not link:
            continue

        if concurso_exists(conn, link):
            logger.debug(f"Já existe: {link}")
            continue

        raw["salario_maximo_float"] = parse_salary(str(raw.get("salario_maximo") or ""))
        raw["data_encerramento_dt"] = parse_date(str(raw.get("data_encerramento") or ""))

        pdf_url = link if link.lower().endswith(".pdf") else None
        if pdf_url:
            r2_url, chunks = process_pdf(pdf_url)
            raw["pdf_url"] = r2_url
        else:
            chunks = []
            raw["pdf_url"] = None

        concurso_id = insert_concurso(conn, raw)
        logger.info(f"Inserido: {concurso_id} - {raw.get('instituicao')}")

        if chunks:
            n = insert_chunks(conn, concurso_id, chunks)
            logger.info(f"  {n} chunks inseridos")

        newly_ingested.append(raw)

    conn.close()

    report = generate_report(newly_ingested)
    save_and_commit_report(report)

    logger.info(f"=== Pipeline DONE: {len(newly_ingested)} novos concursos ===")


if __name__ == "__main__":
    run()
