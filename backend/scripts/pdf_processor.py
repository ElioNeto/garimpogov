"""PDF processor: download, upload to R2, extract text, split into chunks."""
import logging
import os
import tempfile
import uuid
from typing import Optional

import boto3
from botocore.client import Config
import fitz  # PyMuPDF
from langchain.text_splitter import RecursiveCharacterTextSplitter
import requests
from tenacity import retry, stop_after_attempt, wait_exponential

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

CHUNK_SIZE = 1000
CHUNK_OVERLAP = 200

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    )
}


def get_r2_client():
    """Create boto3 S3 client configured for Cloudflare R2."""
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
    """Download PDF from URL, return bytes."""
    logger.info(f"Downloading PDF from {url}")
    response = requests.get(url, headers=HEADERS, timeout=60, stream=True)
    response.raise_for_status()
    content = response.content

    # Check if it looks like a PDF
    if not content.startswith(b"%PDF"):
        logger.warning(f"Content from {url} may not be a valid PDF")

    return content


def upload_to_r2(pdf_bytes: bytes, filename: str) -> str:
    """Upload PDF to Cloudflare R2 and return public URL."""
    bucket = os.environ["R2_BUCKET_NAME"]
    key = f"editais/{filename}"

    client = get_r2_client()
    client.put_object(
        Bucket=bucket,
        Key=key,
        Body=pdf_bytes,
        ContentType="application/pdf",
    )

    # Construct public URL (requires bucket to be public in R2 settings)
    endpoint = os.environ["R2_ENDPOINT_URL"].rstrip("/")
    public_url = f"{endpoint}/{bucket}/{key}"
    logger.info(f"Uploaded PDF to R2: {public_url}")
    return public_url


def extract_text_from_pdf(pdf_bytes: bytes) -> str:
    """Extract all text from PDF using PyMuPDF."""
    with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as f:
        f.write(pdf_bytes)
        tmp_path = f.name

    try:
        doc = fitz.open(tmp_path)
        text_parts = []
        for page_num, page in enumerate(doc):
            text = page.get_text()
            if text.strip():
                text_parts.append(f"[Pagina {page_num + 1}]\n{text}")
        doc.close()
        return "\n\n".join(text_parts)
    finally:
        os.unlink(tmp_path)


def split_text_into_chunks(text: str) -> list[str]:
    """Split text into overlapping chunks using LangChain splitter."""
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=CHUNK_SIZE,
        chunk_overlap=CHUNK_OVERLAP,
        separators=["\n\n", "\n", ". ", " ", ""],
    )
    return splitter.split_text(text)


def process_pdf(pdf_url: str) -> tuple[Optional[str], list[str]]:
    """Full pipeline: download -> upload to R2 -> extract -> chunk.
    Returns (r2_public_url, list_of_chunks).
    """
    try:
        pdf_bytes = download_pdf(pdf_url)
    except Exception as e:
        logger.error(f"Failed to download PDF {pdf_url}: {e}")
        return None, []

    # Upload to R2
    filename = f"{uuid.uuid4()}.pdf"
    try:
        r2_url = upload_to_r2(pdf_bytes, filename)
    except Exception as e:
        logger.warning(f"R2 upload failed, continuing without storage: {e}")
        r2_url = pdf_url  # Fallback to original URL

    # Extract text and chunk
    try:
        text = extract_text_from_pdf(pdf_bytes)
        chunks = split_text_into_chunks(text)
        logger.info(f"Extracted {len(chunks)} chunks from PDF")
        return r2_url, chunks
    except Exception as e:
        logger.error(f"PDF text extraction failed: {e}")
        return r2_url, []
