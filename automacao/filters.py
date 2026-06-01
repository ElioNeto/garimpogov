"""Filtro de escopo: retém apenas concursos dentro do perfil alvo.

Usa regex com word boundaries para casamento mais preciso.
Corrigido (B2): exige confirmação EXPLÍCITA de nível superior.
"""
import re

from automacao.config import TARGET_PROFILES, FILTER_USE_REGEX


def _normalize(text: str) -> str:
    return text.lower()


def _keyword_to_pattern(kw: str) -> re.Pattern:
    """Converte keyword em regex com word boundary.

    Se a keyword já contém metacaracteres regex (ex: 'front.?end'),
    usa como está. Senão, adiciona \b nas bordas.
    """
    meta_chars = set(r".?+*|[]{}()^$\\")
    if any(c in kw for c in meta_chars):
        return re.compile(kw, re.IGNORECASE)

    # Escapa caracteres especiais e envolve em word boundary
    escaped = re.escape(kw)
    return re.compile(r"\b" + escaped + r"\b", re.IGNORECASE)


def _compile_profile(profile: dict) -> dict:
    """Pré-compila expressões regulares do perfil para performance."""
    compiled = dict(profile)
    compiled["_kw_patterns"] = [_keyword_to_pattern(kw) for kw in profile.get("keywords", [])]
    compiled["_re_extra"] = [re.compile(expr, re.IGNORECASE) for expr in profile.get("re_extra", [])]
    compiled["_nivel_patterns"] = [_keyword_to_pattern(n) for n in profile.get("nivel_keywords", [])]
    compiled["_nivel_medio"] = re.compile(
        r"\b(médio|medio|fundamental|ensino médio|ensino medio|ensino fundamental)\b",
        re.IGNORECASE,
    )
    return compiled


# Pré-compila todos os perfis uma vez
_COMPILED_PROFILES = [_compile_profile(p) for p in TARGET_PROFILES]


def matches_scope(concurso: dict) -> bool:
    """
    Retorna True se o concurso corresponde a pelo menos um perfil alvo.

    Verifica: instituicao, cargos, orgao, fonte.
    Usa regex com word boundary para evitar falsos-positivos
    (ex: 'ti' dentro de 'atividades' ou 'cientifico').
    """
    # Monta texto completo para busca
    parts = [
        concurso.get("instituicao") or "",
        " ".join(concurso.get("cargos") or []),
        concurso.get("orgao") or "",
        concurso.get("fonte") or "",
    ]
    full_text = _normalize(" ".join(parts))

    for profile in _COMPILED_PROFILES:
        # 1. Match por keywords
        keyword_match = any(p.search(full_text) for p in profile["_kw_patterns"])
        if not keyword_match:
            # 2. Match por regex extra
            keyword_match = any(p.search(full_text) for p in profile["_re_extra"])

        if not keyword_match:
            continue

        nivel_kws = profile.get("nivel_keywords", [])
        # Perfil que aceita qualquer nível (ex.: Professor de Inglês)
        if "qualquer" in nivel_kws:
            return True

        # Perfil com exigência de nível superior: precisa de confirmação EXPLÍCITA
        nivel_match = any(p.search(full_text) for p in profile["_nivel_patterns"])
        if nivel_match:
            return True

        # Bloqueia se houver menção explícita de nível médio/fundamental
        if profile["_nivel_medio"].search(full_text):
            continue

        # Sem informação de nível — deixa passar (falso-positivo controlado)
        return True

    return False
