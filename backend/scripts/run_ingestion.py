"""Main ingestion orchestrator - called by GitHub Actions daily."""
import logging
import sys
import os

# Ensure backend/ is in path when run from project root
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from scripts.scraper import scrape_all_sources
from scripts.pdf_processor import process_pdf
from scripts.vector_store import (
    get_db_connection,
    concurso_exists,
    insert_concurso,
    insert_chunks,
)
from scripts.commit_backup import generate_report, save_and_commit_report
from app.utils.helpers import parse_salary, parse_date

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s: %(message)s"
)
logger = logging.getLogger(__name__)


def run():
    logger.info("=== GarimpoGov Ingestion Pipeline START ===")

    # 1. Scrape
    concursos_raw = scrape_all_sources()
    logger.info(f"Scraped {len(concursos_raw)} raw concursos")

    conn = get_db_connection()
    newly_ingested = []

    for raw in concursos_raw:
        link = raw.get("link_edital")
        if not link:
            logger.warning("Concurso without link_edital, skipping")
            continue

        # 2. Idempotency check
        existing_id = concurso_exists(conn, link)
        if existing_id:
            logger.info(f"Already exists: {link}")
            continue

        # Parse salary and date
        raw["salario_maximo_float"] = parse_salary(str(raw.get("salario_maximo") or ""))
        raw["data_encerramento_dt"] = parse_date(str(raw.get("data_encerramento") or ""))

        # Determine PDF URL - try link_edital if it ends with .pdf
        pdf_url = link if link.lower().endswith(".pdf") else None

        # 3. Process PDF if available
        if pdf_url:
            r2_url, chunks = process_pdf(pdf_url)
            raw["pdf_url"] = r2_url
        else:
            chunks = []
            raw["pdf_url"] = None
            logger.info(f"No PDF URL for {link}, skipping PDF processing")

        # 4. Insert concurso
        concurso_id = insert_concurso(conn, raw)
        logger.info(f"Inserted concurso {concurso_id} - {raw.get('instituicao')}")

        # 5. Insert chunks with embeddings
        if chunks:
            n_chunks = insert_chunks(conn, concurso_id, chunks)
            logger.info(f"Inserted {n_chunks} chunks for {concurso_id}")

        newly_ingested.append(raw)

    conn.close()

    # 6. Backup report
    report = generate_report(newly_ingested)
    save_and_commit_report(report)

    logger.info(f"=== Pipeline DONE: {len(newly_ingested)} new concursos ===")


if __name__ == "__main__":
    run()
