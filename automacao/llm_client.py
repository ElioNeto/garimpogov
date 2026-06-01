"""Cliente LLM via OpenRouter — apenas modelos gratuitos, com fallback dinâmico.

A lista de modelos gratuitos é obtida automaticamente da API do OpenRouter
(https://openrouter.ai/api/v1/models) e filtrada por preço zero.

Se um modelo retornar erro (exceto 429 rate-limit), tenta o próximo.
O cache é atualizado a cada hora.

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

logger = logging.getLogger(__name__)

# ===================================================================
# Descoberta dinâmica de modelos gratuitos via API OpenRouter
# ===================================================================

_FREE_MODELS_CACHE: list[str] | None = None
_FREE_MODELS_CACHE_TIME: float = 0
_CACHE_TTL = 3600  # 1 hora
_cache_lock = threading.Lock()

# Fallback hardcoded caso a API não responda
_FALLBACK_FREE_MODELS = [
    "google/gemini-2.0-flash-lite",
    "google/gemini-2.0-flash",
    "meta-llama/llama-3.2-3b-instruct",
    "microsoft/phi-3-medium-4k-instruct",
]


def _fetch_free_models() -> list[str]:
    """Consulta a API do OpenRouter e retorna lista de modelos com preço zero."""
    import httpx

    try:
        resp = httpx.get(
            "https://openrouter.ai/api/v1/models",
            headers={"User-Agent": "GarimpoGov/1.0"},
            timeout=15,
        )
        resp.raise_for_status()
        data = resp.json()

        free_models = []
        for model in data.get("data", []):
            pricing = model.get("pricing", {})
            prompt_price = pricing.get("prompt", "0")
            completion_price = pricing.get("completion", "0")
            if prompt_price == "0" and completion_price == "0":
                free_models.append(model["id"])

        if not free_models:
            logger.warning("API retornou lista vazia de modelos free — usando fallback")
            return _FALLBACK_FREE_MODELS.copy()

        # Ordena: prefere Google, depois Llama/Mistral/Phi, depois resto
        def sort_key(m: str) -> tuple:
            low = m.lower()
            if "google" in low:
                return (0, m)
            if "llama" in low or "mistral" in low or "phi" in low:
                return (1, m)
            return (2, m)

        free_models.sort(key=sort_key)
        logger.info(
            "Modelos free carregados da API (%d): %s ...",
            len(free_models), free_models[:6],
        )
        return free_models

    except Exception as e:
        logger.warning("Falha ao buscar modelos free da API (%s) — usando fallback", e)
        return _FALLBACK_FREE_MODELS.copy()


def _get_free_models() -> list[str]:
    """Retorna lista de modelos free (cache com TTL de 1 hora)."""
    global _FREE_MODELS_CACHE, _FREE_MODELS_CACHE_TIME

    now = time.monotonic()
    if _FREE_MODELS_CACHE is not None and (now - _FREE_MODELS_CACHE_TIME) < _CACHE_TTL:
        return _FREE_MODELS_CACHE

    with _cache_lock:
        # Double-check dentro do lock
        if _FREE_MODELS_CACHE is not None and (now - _FREE_MODELS_CACHE_TIME) < _CACHE_TTL:
            return _FREE_MODELS_CACHE

        _FREE_MODELS_CACHE = _fetch_free_models()
        _FREE_MODELS_CACHE_TIME = time.monotonic()
        return _FREE_MODELS_CACHE


def _build_model_list(
    configured: str | None,
    preferred_first: str,
) -> list[str]:
    """Monta lista priorizada: configurado → preferido → free sorted.

    O modelo configurado (env var) vem primeiro.
    Depois o preferred_first (default para o propósito) se diferente.
    Depois os demais free models.
    """
    all_free = _get_free_models()

    # Se configured veio de parâmetro explícito, usa ele; senão lê da env
    effective = configured or os.environ.get(
        "OPENROUTER_EXTRACTION_MODEL"
    ) or os.environ.get(
        "OPENROUTER_CHAT_MODEL"
    )

    ordered: list[str] = []
    seen: set[str] = set()

    if effective and effective not in seen:
        ordered.append(effective)
        seen.add(effective)

    if preferred_first not in seen:
        ordered.append(preferred_first)
        seen.add(preferred_first)

    for m in all_free:
        if m not in seen:
            ordered.append(m)
            seen.add(m)

    # Se por algum motivo a lista ficou vazia
    if not ordered:
        ordered = _FALLBACK_FREE_MODELS.copy()

    return ordered


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


def _call_openrouter(body: dict) -> tuple[int, str]:
    """Faz chamada HTTP POST e retorna (status_code, response_text)."""
    import httpx

    resp = httpx.post(
        "https://openrouter.ai/api/v1/chat/completions",
        headers={**_HEADERS, "Authorization": f"Bearer {_api_key()}"},
        json=body,
        timeout=120,
    )
    return resp.status_code, resp.text


def _is_retryable(status: int) -> bool:
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
    """Chamada síncrona de completion com fallback dinâmico.

    Tenta o modelo configurado primeiro. Se falhar, percorre a lista de
    modelos gratuitos obtida da API do OpenRouter.
    """
    models = _build_model_list(
        configured=model or os.environ.get("OPENROUTER_EXTRACTION_MODEL"),
        preferred_first="google/gemini-2.0-flash-lite",
    )

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

        for attempt in range(3):
            try:
                _rate_limit()
                status, text = _call_openrouter(body)

                if status == 200:
                    data = json.loads(text)
                    return data["choices"][0]["message"]["content"]

                logger.error(
                    "OpenRouter HTTP %d no modelo %s (attempt %d): %.300s",
                    status, candidate, attempt + 1, text,
                )

                if not _is_retryable(status):
                    break

                if attempt < 2:
                    wait = (2 ** attempt) * 15
                    logger.info("Aguardando %ds antes de retentar %s...", wait, candidate)
                    time.sleep(wait)

            except Exception as e:
                last_error = e
                logger.error(
                    "Exceção no modelo %s (attempt %d): %s", candidate, attempt + 1, e
                )
                if attempt < 2:
                    time.sleep((2 ** attempt) * 15)

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
    """Stream de tokens com fallback dinâmico entre modelos free.

    Uso:
        async for chunk in generate_stream("minha pergunta"):
            acumula(chunk)
    """
    models = _build_model_list(
        configured=model or os.environ.get("OPENROUTER_CHAT_MODEL"),
        preferred_first="google/gemini-2.0-flash",
    )

    import httpx
    import asyncio

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
                        return

                    try:
                        err_body = await resp.aread()
                    except Exception:
                        err_body = b"(could not read)"
                    logger.error(
                        "OpenRouter HTTP %d no modelo %s (stream): %.300s",
                        resp.status_code, candidate,
                        err_body[:500].decode(errors="replace"),
                    )

                    if resp.status_code == 429 or resp.status_code >= 500:
                        logger.warning(
                            "Rate limit/servidor — re-tentando modelo %s em 30s...", candidate
                        )
                        await asyncio.sleep(30)
                        continue

                    break

        except Exception as e:
            last_error = e
            logger.error("Exceção no streaming com %s: %s", candidate, e)
            continue

    yield f"Desculpe, ocorreu um erro ao gerar a resposta. Último erro: {last_error}"
