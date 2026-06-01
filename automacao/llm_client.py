"""Cliente LLM unificado — OpenRouter (primário) com fallback Google Gemini.

Uso no pipeline de ingestão (síncrono):
    from automacao.llm_client import generate
    texto = generate("prompt", model="google/gemini-2.0-flash-lite")

Uso no backend RAG (assíncrono, streaming):
    from automacao.llm_client import generate_stream
    async for chunk in generate_stream("prompt"):
        ...

Estratégia de provedor:
  1. Se OPENROUTER_API_KEY estiver definida → usa OpenRouter (OpenAI-compatible)
  2. Senão → fallback para Google Gemini via google.genai SDK
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
# Rate limiting (compartilhado entre provedores)
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
# Utilitários
# ---------------------------------------------------------------------------
_HEADERS: dict[str, str] = {
    "User-Agent": "GarimpoGov/1.0",
    "Content-Type": "application/json",
}


def _openrouter_key() -> str | None:
    return os.environ.get("OPENROUTER_API_KEY")


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
    """Chamada síncrona de completion.

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
    key = _openrouter_key()
    if key:
        return _generate_openrouter(
            prompt,
            model=model,
            response_format=response_format,
            temperature=temperature,
            max_tokens=max_tokens,
            api_key=key,
        )
    return _generate_gemini(prompt, temperature=temperature, max_tokens=max_tokens)


def _generate_openrouter(
    prompt: str,
    *,
    model: str | None,
    response_format: dict | None,
    temperature: float,
    max_tokens: int,
    api_key: str,
) -> str:
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
        headers={**_HEADERS, "Authorization": f"Bearer {api_key}"},
        json=body,
        timeout=120,
    )
    resp.raise_for_status()
    data = resp.json()
    return data["choices"][0]["message"]["content"]


def _generate_gemini(
    prompt: str,
    *,
    temperature: float,
    max_tokens: int,
) -> str:
    _rate_limit()
    from google import genai
    from google.genai import types

    client = genai.Client(api_key=os.environ["GEMINI_API_KEY"])
    model = os.environ.get("GEMINI_EXTRACTION_MODEL", "gemini-2.0-flash-lite")
    response = client.models.generate_content(
        model=model,
        contents=prompt,
        config=types.GenerateContentConfig(
            temperature=temperature,
            max_output_tokens=max_tokens,
        ),
    )
    return response.text


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
    """Stream de tokens via OpenRouter (ou fallback Gemini).

    Uso:
        async for chunk in generate_stream("minha pergunta"):
            acumula(chunk)
    """
    key = _openrouter_key()
    if key:
        async for chunk in _generate_openrouter_stream(
            prompt,
            model=model,
            temperature=temperature,
            max_tokens=max_tokens,
            api_key=key,
        ):
            yield chunk
    else:
        async for chunk in _generate_gemini_stream(
            prompt, temperature=temperature, max_tokens=max_tokens
        ):
            yield chunk


async def _generate_openrouter_stream(
    prompt: str,
    *,
    model: str | None,
    temperature: float,
    max_tokens: int,
    api_key: str,
) -> AsyncIterator[str]:
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
            headers={**_HEADERS, "Authorization": f"Bearer {api_key}"},
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


async def _generate_gemini_stream(
    prompt: str,
    *,
    temperature: float,
    max_tokens: int,
) -> AsyncIterator[str]:
    from google import genai

    client = genai.Client(api_key=os.environ.get("GEMINI_API_KEY", ""))
    model = os.environ.get("GEMINI_CHAT_MODEL", "gemini-1.5-flash")
    response = client.models.generate_content_stream(
        model=model,
        contents=prompt,
    )
    for chunk in response:
        if chunk.text:
            yield chunk.text
