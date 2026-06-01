"""Cliente LLM via OpenRouter — apenas modelos gratuitos, com fallback automático.

Se um modelo retornar erro (exceto 429 rate-limit), tenta o próximo da lista
de modelos gratuitos. Isso garante resiliência mesmo que um modelo específico
esteja fora do ar ou com limite excedido.

Modelos free confirmados no OpenRouter (jun/2026):
  - google/gemini-2.0-flash-lite  ← rápido, 30 RPM
  - google/gemini-2.0-flash        ← melhor qualidade
  - meta-llama/llama-3.2-3b-instruct   ← leve, gratuito
  - microsoft/phi-3-medium-4k-instruct  ← gratuito

Uso:
    from automacao.llm_client import generate, generate_stream
    texto = generate("prompt")
    async for chunk in generate_stream("prompt"): ...
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
# Listas de modelos gratuitos (ordem = preferência)
# ---------------------------------------------------------------------------
# A primeira posição pode ser sobrescrita via variável de ambiente.
# As demais são fallbacks caso o modelo principal falhe.

FREE_EXTRACTION_MODELS: list[str] = [
    "google/gemini-2.0-flash-lite",   # padrão — rápido, 30 RPM, gratuito
    "google/gemini-2.0-flash",        # fallback 1 — mesma família
    "meta-llama/llama-3.2-3b-instruct",  # fallback 2 — leve
    "microsoft/phi-3-medium-4k-instruct",  # fallback 3
]

FREE_CHAT_MODELS: list[str] = [
    "google/gemini-2.0-flash",        # padrão — melhor qualidade, gratuito
    "google/gemini-2.0-flash-lite",   # fallback 1 — rápido
    "meta-llama/llama-3.2-3b-instruct",  # fallback 2
    "microsoft/phi-3-medium-4k-instruct",  # fallback 3
]

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


# ---------------------------------------------------------------------------
# Utilitário HTTP
# ---------------------------------------------------------------------------

def _call_openrouter(body: dict) -> tuple[int, str]:
    """Faz a chamada HTTP e retorna (status_code, response_text).

    Não levanta exceção para erros HTTP — quem chama decide o que fazer.
    """
    import httpx

    resp = httpx.post(
        "https://openrouter.ai/api/v1/chat/completions",
        headers={**_HEADERS, "Authorization": f"Bearer {_api_key()}"},
        json=body,
        timeout=120,
    )
    return resp.status_code, resp.text


def _is_retryable(status: int) -> bool:
    """Erros 429 (rate-limit) e 5xx (servidor) são retryáveis."""
    return status == 429 or status >= 500


# ===================================================================
# GERAÇÃO SÍNCRONA (usada por ai_extractor.py)
# ===================================================================


def generate(
    prompt: str,
    *,
    model: str | None = None,
    temperature: float = 0.0,
    max_tokens: int = 4096,
) -> str:
    """Chamada síncrona de completion com fallback entre modelos free.

    Tenta cada modelo da lista em ordem até um responder com sucesso.
    Erros rate-limit (429) e de servidor (5xx) são retryáveis com backoff.
    Erros 4xx (exceto 429) pulam para o próximo modelo imediatamente.
    """
    # Monta a lista de modelos: configurado via env + fallbacks
    configured = model or os.environ.get("OPENROUTER_EXTRACTION_MODEL")
    models = FREE_EXTRACTION_MODELS.copy()
    if configured and configured != models[0]:
        models.insert(0, configured)

    last_error: Exception | None = None

    for i, candidate in enumerate(models):
        if i > 0:
            logger.warning("Fallback para modelo: %s", candidate)

        body: dict = {
            "model": candidate,
            "messages": [{"role": "user", "content": prompt}],
            "temperature": temperature,
            "max_tokens": max_tokens,
        }

        # Tenta até 3 vezes com backoff para erros retryáveis
        for attempt in range(3):
            try:
                _rate_limit()
                status, text = _call_openrouter(body)

                if status == 200:
                    data = json.loads(text)
                    return data["choices"][0]["message"]["content"]

                # Log do erro
                logger.error(
                    "OpenRouter HTTP %d no modelo %s (attempt %d): %.300s",
                    status, candidate, attempt + 1, text,
                )

                # Se não for retryável, pula para o próximo modelo
                if not _is_retryable(status):
                    break

                # Se é retryável, espera e tenta de novo
                if attempt < 2:
                    wait = (2 ** attempt) * 15  # 15s, 30s
                    logger.info("Aguardando %ds antes de retentar %s...", wait, candidate)
                    time.sleep(wait)

            except Exception as e:
                last_error = e
                logger.error(
                    "Exceção no modelo %s (attempt %d): %s", candidate, attempt + 1, e
                )
                if attempt < 2:
                    time.sleep((2 ** attempt) * 15)

    # Se chegou aqui, todos os modelos falharam
    raise RuntimeError(
        f"Todos os modelos gratuitos falharam. Último erro: {last_error}"
    ) from last_error


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
    """Stream de tokens com fallback entre modelos free.

    Uso:
        async for chunk in generate_stream("minha pergunta"):
            acumula(chunk)

    Se o modelo atual falhar com erro 4xx (não retryável), pula para o
    próximo da lista de modelos gratuitos.
    """
    configured = model or os.environ.get("OPENROUTER_CHAT_MODEL")
    models = FREE_CHAT_MODELS.copy()
    if configured and configured != models[0]:
        models.insert(0, configured)

    import httpx

    last_error: Exception | None = None

    for i, candidate in enumerate(models):
        if i > 0:
            logger.warning("Fallback streaming para modelo: %s", candidate)

        body = {
            "model": candidate,
            "messages": [{"role": "user", "content": prompt}],
            "temperature": temperature,
            "max_tokens": max_tokens,
            "stream": True,
        }

        try:
            async with httpx.AsyncClient(timeout=120) as client:
                async with client.stream(
                    "POST",
                    "https://openrouter.ai/api/v1/chat/completions",
                    headers={**_HEADERS, "Authorization": f"Bearer {_api_key()}"},
                    json=body,
                ) as resp:
                    if resp.status_code == 200:
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
                        return  # streaming completo com sucesso

                    # Erro — loga e tenta próximo modelo
                    try:
                        err_body = await resp.aread()
                    except Exception:
                        err_body = b"(could not read)"
                    logger.error(
                        "OpenRouter HTTP %d no modelo %s (stream): %.300s",
                        resp.status_code, candidate,
                        err_body[:500].decode(errors="replace"),
                    )

                    # Se é retryável (429/5xx), tenta de novo com o mesmo modelo
                    if resp.status_code == 429 or resp.status_code >= 500:
                        logger.warning("Rate limit/servidor — re-tentando modelo %s em 30s...", candidate)
                        import asyncio
                        await asyncio.sleep(30)
                        continue  # tenta o mesmo modelo de novo

                    # 4xx não retryável → pula para o próximo modelo
                    break

        except Exception as e:
            last_error = e
            logger.error("Exceção no streaming com %s: %s", candidate, e)
            # Tenta o próximo modelo
            continue

    # Se chegou aqui, todos falharam
    yield f"Desculpe, ocorreu um erro ao gerar a resposta. Último erro: {last_error}"
