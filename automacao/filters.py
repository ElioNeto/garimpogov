"""Filtro de escopo: retém apenas concursos dentro do perfil alvo."""
import re
from automacao.config import TARGET_PROFILES


def _normalize(text: str) -> str:
    return text.lower()


def matches_scope(concurso: dict) -> bool:
    """
    Retorna True se o concurso corresponde a pelo menos um perfil alvo.
    Verifica: instituicao, cargos, texto livre.
    """
    # Monta texto completo para busca
    parts = [
        concurso.get("instituicao") or "",
        " ".join(concurso.get("cargos") or []),
        concurso.get("orgao") or "",
    ]
    full_text = _normalize(" ".join(parts))

    for profile in TARGET_PROFILES:
        keyword_match = any(kw.lower() in full_text for kw in profile["keywords"])
        if not keyword_match:
            continue

        # Se o perfil exige nível superior, verifica se o texto NÃO menciona
        # exclusivamente nível médio/fundamental sem superior
        nivel_kws = profile.get("nivel_keywords", [])
        if "qualquer" in nivel_kws:
            return True
        nivel_match = any(n in full_text for n in nivel_kws)
        if nivel_match or not any(n in full_text for n in ["médio", "medio", "fundamental"]):
            return True

    return False
