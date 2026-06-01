"""Embeddings locais via sentence-transformers (sem API externa).

Modelo: paraphrase-multilingual-MiniLM-L12-v2
  - 384 dimensões, multilíngue (ótimo para português)
  - Leve (~470 MB em disco), roda em CPU
  - Gratuito, sem chave de API

Uso:
    from automacao.embeddings import embed_text, embed_chunks_batch
    vec = embed_text("texto")
    vecs = embed_chunks_batch(["texto1", "texto2"])
"""
from __future__ import annotations

import logging
import threading

logger = logging.getLogger(__name__)

_EMBEDDING_DIM = 384
_model_instance = None
_model_lock = threading.Lock()


def _get_model():
    """Lazy-load do modelo sentence-transformers (thread-safe)."""
    global _model_instance
    if _model_instance is None:
        with _model_lock:
            if _model_instance is None:
                from sentence_transformers import SentenceTransformer

                logger.info("Carregando modelo de embedding sentence-transformers...")
                _model_instance = SentenceTransformer(
                    "paraphrase-multilingual-MiniLM-L12-v2"
                )
                logger.info("Modelo de embedding carregado.")
    return _model_instance


def get_embedding_dim() -> int:
    """Retorna a dimensão dos embeddings gerados."""
    return _EMBEDDING_DIM


def embed_text(text: str) -> list[float]:
    """Gera embedding para um único texto."""
    model = _get_model()
    vec = model.encode(text, normalize_embeddings=True)
    return vec.tolist()


def embed_chunks_batch(texts: list[str]) -> list[list[float]]:
    """Gera embeddings em lote (mais eficiente que chamadas individuais)."""
    if not texts:
        return []
    model = _get_model()
    vecs = model.encode(texts, normalize_embeddings=True)
    return [v.tolist() for v in vecs]
