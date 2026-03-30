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

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

CHUNK_SIZE = 1000
CHUNK_OVERLAP = 200
HEADERS = {"User-Agent": "Mozilla/5.0 GarimpoGov/1.0"}


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
    try:
        pdf_bytes = download_pdf(pdf_url)
    except Exception as e:
        logger.error(f"Falha download PDF {pdf_url}: {e}")
        return None, []

    filename = f"{uuid.uuid4()}.pdf"
    try:
        r2_url = upload_to_r2(pdf_bytes, filename)
    except Exception as e:
        logger.warning(f"Upload R2 falhou, usando URL original: {e}")
        r2_url = pdf_url

    try:
        text = extract_text(pdf_bytes)
        splitter = RecursiveCharacterTextSplitter(
            chunk_size=CHUNK_SIZE,
            chunk_overlap=CHUNK_OVERLAP,
            separators=["\n\n", "\n", ". ", " ", ""],
        )
        chunks = splitter.split_text(text)
        logger.info(f"Extraidos {len(chunks)} chunks")
        return r2_url, chunks
    except Exception as e:
        logger.error(f"Extracao PDF falhou: {e}")
        return r2_url, []
