"""PDF processor: download, upload para R2, extrai texto, divide em chunks."""
import logging
import os
import tempfile
import uuid
from typing import Optional

import boto3
from botocore.client import Config
import fitz
import requests
from langchain_text_splitters import RecursiveCharacterTextSplitter
from tenacity import retry, stop_after_attempt, wait_exponential

from automacao.config import CHUNK_SIZE, CHUNK_OVERLAP, DEFAULT_HEADERS

logger = logging.getLogger(__name__)
HEADERS = DEFAULT_HEADERS


def get_r2_client():
    return boto3.client(
        "s3",
        endpoint_url=os.environ["R2_ENDPOINT_URL"],
        aws_access_key_id=os.environ["R2_ACCESS_KEY_ID"],
        aws_secret_access_key=os.environ["R2_SECRET_ACCESS_KEY"],
        config=Config(signature_version="s3v4"),
        region_name="auto",
    )


@retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=2, max=10))
def download_pdf(url: str) -> bytes:
    logger.info(f"Downloading PDF: {url}")
    r = requests.get(url, headers=HEADERS, timeout=60, stream=True)
    r.raise_for_status()
    return r.content


def upload_to_r2(pdf_bytes: bytes, filename: str) -> str:
    bucket = os.environ["R2_BUCKET_NAME"]
    key = f"editais/{filename}"
    client = get_r2_client()
    client.put_object(Bucket=bucket, Key=key, Body=pdf_bytes, ContentType="application/pdf")
    endpoint = os.environ["R2_ENDPOINT_URL"].rstrip("/")
    return f"{endpoint}/{bucket}/{key}"


def extract_text(pdf_bytes: bytes) -> str:
    with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as f:
        f.write(pdf_bytes)
        tmp = f.name
    try:
        doc = fitz.open(tmp)
        parts = []
        for n, page in enumerate(doc):
            t = page.get_text()
            if t.strip():
                parts.append(f"[Pagina {n+1}]\n{t}")
        doc.close()
        return "\n\n".join(parts)
    finally:
        os.unlink(tmp)


def process_pdf(pdf_url: str) -> tuple[Optional[str], list[str]]:
    # B14: logging estruturado por etapa com metadados
    logger.info("[PDF] Iniciando processamento", extra={"url": pdf_url})
    try:
        pdf_bytes = download_pdf(pdf_url)
        logger.info(f"[PDF] Download OK: {len(pdf_bytes)} bytes", extra={"url": pdf_url})
    except Exception as e:
        logger.error(f"[PDF] Falha download: {e}", extra={"url": pdf_url})
        return None, []

    filename = f"{uuid.uuid4()}.pdf"
    try:
        r2_url = upload_to_r2(pdf_bytes, filename)
        logger.info(f"[PDF] Upload R2 OK: {r2_url}", extra={"url": pdf_url, "r2_url": r2_url})
    except Exception as e:
        logger.warning(f"[PDF] Upload R2 falhou, usando URL original: {e}", extra={"url": pdf_url})
        r2_url = pdf_url

    try:
        text = extract_text(pdf_bytes)
        logger.info(f"[PDF] Texto extraido: {len(text)} chars", extra={"url": pdf_url})
        splitter = RecursiveCharacterTextSplitter(
            chunk_size=CHUNK_SIZE,
            chunk_overlap=CHUNK_OVERLAP,
            separators=["\n\n", "\n", ". ", " ", ""],
        )
        chunks = splitter.split_text(text)
        logger.info(f"[PDF] Chunking OK: {len(chunks)} chunks", extra={"url": pdf_url, "chunks": len(chunks)})
        return r2_url, chunks
    except Exception as e:
        logger.error(f"[PDF] Extracao/chunking falhou: {e}", extra={"url": pdf_url})
        return r2_url, []
