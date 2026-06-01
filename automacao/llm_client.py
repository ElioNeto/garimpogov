"""Cliente LLM via OpenRouter — apenas modelos gratuitos.

Modelos free confirmados no OpenRouter:
  - google/gemini-2.0-flash-lite  (extração, 30 RPM)
  - google/gemini-2.0-flash        (chat, qualidade superior)
  - meta-llama/llama-3.2-3b-instruct (alternativa leve)

Uso no pipeline de ingestão (síncrono):
    from automacao.llm_client import generate
    texto = generate("prompt", model="google/gemini-2.0-flash-lite")

Uso no backend RAG (assíncrono, streaming):
    from automacao.llm_client import generate_stream
    async for chunk in generate_stream("prompt"):
        ...

Requer OPENROUTER_API_KEY no ambiente.
"""
from __future__ import annotations

import json
import logging
import os
import threading
import time
from typing import AsyncIterator, Optional

from tenacity import retry, stop_after_attempt, wait_exponential

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Rate limiting
# ---------------------------------------------------------------------------
_rate_lock = threading.Lock()
_last_call: float = 0.0
MIN_INTERVAL = 2.5  # segundos entre chamadas → ~24 RPM


def _rate_limit() -> None:
    with _rate_lock:
        global _last_call
        elapsed = time.monotonic() - _last_call
        if elapsed < MIN_INTERVAL:
            wait = MIN_INTERVAL - elapsed
            logger.debug(f"Rate limit: aguardando {wait:.2f}s")
            time.sleep(wait)
        _last_call = time.monotonic()


# ---------------------------------------------------------------------------
# Headers padrão
# ---------------------------------------------------------------------------
_HEADERS: dict[str, str] = {
    "User-Agent": "GarimpoGov/1.0",
    "Content-Type": "application/json",
}


def _api_key() -> str:
    key = os.environ.get("OPENROUTER_API_KEY")
    if not key:
        raise RuntimeError(
            "OPENROUTER_API_KEY não definida. "
            "Defina a variável de ambiente com sua chave do OpenRouter."
        )
    return key


# ===================================================================
# GERAÇÃO SÍNCRONA (usada por ai_extractor.py)
# ===================================================================


@retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=2, min=30, max=120))
def generate(
    prompt: str,
    *,
    model: str | None = None,
    response_format: dict | None = None,
    temperature: float = 0.0,
    max_tokens: int = 4096,
) -> str:
    """Chamada síncrona de completion via OpenRouter.

    Parâmetros
    ----------
    prompt
        Prompt completo (já formatado com contexto, scope etc.).
    model
        Nome do modelo OpenRouter (ex: ``"google/gemini-2.0-flash-lite"``).
        Se omitido, lê ``OPENROUTER_EXTRACTION_MODEL`` env ou usa default.
    response_format
        Opcional. Ex: ``{"type": "json_object"}`` para garantir JSON.
    """
    _rate_limit()

    model = model or os.environ.get(
        "OPENROUTER_EXTRACTION_MODEL", "google/gemini-2.0-flash-lite"
    )

    body: dict = {
        "model": model,
        "messages": [{"role": "user", "content": prompt}],
        "temperature": temperature,
        "max_tokens": max_tokens,
    }
    if response_format:
        body["response_format"] = response_format

    import httpx

    resp = httpx.post(
        "https://openrouter.ai/api/v1/chat/completions",
        headers={**_HEADERS, "Authorization": f"Bearer {_api_key()}"},
        json=body,
        timeout=120,
    )
    resp.raise_for_status()
    data = resp.json()
    return data["choices"][0]["message"]["content"]


# ===================================================================
# GERAÇÃO ASSÍNCRONA COM STREAMING (usada por rag.py)
# ===================================================================


async def generate_stream(
    prompt: str,
    *,
    model: str | None = None,
    temperature: float = 0.0,
    max_tokens: int = 2048,
) -> AsyncIterator[str]:
    """Stream de tokens via OpenRouter.

    Uso:
        async for chunk in generate_stream("minha pergunta"):
            acumula(chunk)
    """
    model = model or os.environ.get(
        "OPENROUTER_CHAT_MODEL", "google/gemini-2.0-flash"
    )

    body = {
        "model": model,
        "messages": [{"role": "user", "content": prompt}],
        "temperature": temperature,
        "max_tokens": max_tokens,
        "stream": True,
    }

    import httpx

    async with httpx.AsyncClient(timeout=120) as client:
        async with client.stream(
            "POST",
            "https://openrouter.ai/api/v1/chat/completions",
            headers={**_HEADERS, "Authorization": f"Bearer {_api_key()}"},
            json=body,
        ) as resp:
            resp.raise_for_status()
            async for line in resp.aiter_lines():
                if not line.startswith("data: "):
                    continue
                data_str = line[6:].strip()
                if not data_str or data_str == "[DONE]":
                    break
                try:
                    chunk = json.loads(data_str)
                    delta = chunk.get("choices", [{}])[0].get("delta", {})
                    content = delta.get("content")
                    if content:
                        yield content
                except json.JSONDecodeError:
                    continue
