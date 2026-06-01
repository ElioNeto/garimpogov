"""Escopo de busca do GarimpoGov.

Só são ingeridos concursos que correspondam a pelo menos um dos perfis abaixo.
"""

import os


# ---------------------------------------------------------------------------
# Perfis de vaga aceitos
# ---------------------------------------------------------------------------
# Cada perfil é um dict com:
#   keywords  – ao menos UMA deve aparecer no texto do concurso (case-insensitive)
#   nivel     – nível de escolaridade exigido (usado para filtrar)
# ---------------------------------------------------------------------------

# ---------------------------------------------------------------------------
# Perfis de vaga aceitos
# ---------------------------------------------------------------------------
# Cada perfil é um dict com:
#   keywords    – palavras-chave (usadas com re.IGNORECASE + word boundary)
#   nivel_keywords – nível de escolaridade exigido
#   re_extra    – expressões regulares extras (opcional, compilado internamente)
# ---------------------------------------------------------------------------

TARGET_PROFILES = [
    {
        "name": "TI",
        "keywords": [
            # ── Cargos e áreas de TI ──
            "tecnologia da informação", "analista de ti", "analista de sistemas",
            "analista de software", "analista de tecnologia", "analista de informática",
            "desenvolvedor", "desenvolvimento de software", "engenheiro de software",
            "programador", "programador de software", "arquiteto de software",
            "infraestrutura de ti", "suporte de ti", "administrador de ti",
            "segurança da informação", "segurança cibernética",
            "banco de dados", "administrador de banco de dados", "dba",
            "redes de computadores", "administrador de redes", "analista de redes",
            "ciência da computação", "sistemas de informação", "engenharia de computação",
            "técnico em informática", "técnico de informática", "tecnólogo em informática",
            "tecnólogo em análise de sistemas",
            # ── Cargos modernos de TI ──
            "engenheiro de dados", "cientista de dados", "data science",
            "engenheiro de machine learning", "ml ops",
            "devops", "sre", "cloud computing", "computação em nuvem",
            "gestão de ti", "governança de ti", "itil", "coBIT",
            "desenvolvimento web", "desenvolvimento mobile",
            "inteligência artificial", "machine learning", "deep learning",
            "suporte técnico", "analista de suporte", "help desk", "service desk",
            "analista de infraestrutura", "analista de segurança",
            "projetos de ti", "projetos de tecnologia", "gerente de ti",
            "sistemas", "informática", "software",
            "automação de testes", "qualidade de software", "qa",
            # ── Abreviações e variantes ──
            "bi ", " big data", "iot", "ia ",
            "front.?end", "back.?end", "full.?stack",
        ],
        "nivel_keywords": ["superior", "graduação", "bacharel", "licenciatura", "tecnólogo"],
        "re_extra": [
            r"\bti\b",
            r"\bt\.i\.\b",
            r"\btic\b",
            r"\bt\.i\b",
            r"tecnolog(ia|ico|ica)",
            r"informát(ica|ico)",
            r"computaç(ão|cional)",
            r"\bsoftware\b",
            r"\bdesenvolvimento\b.*\bsoftware\b",
            r"\bengenharia\b.*\bsoftware\b",
            r"\bprogramaç(ão|ol)\b",
        ],
    },
    {
        "name": "Professor de Inglês / Língua Estrangeira",
        "keywords": [
            # ── Professor de Inglês ──
            "professor de inglês", "professor de lingua inglesa",
            "professor de língua inglesa", "docente de inglês",
            "professor de idiomas inglês", "instrutor de inglês",
            "magistério inglês",
            # ── Língua Estrangeira ──
            "professor de língua estrangeira", "professor de lingua estrangeira",
            "professor de idiomas estrangeiros",
            "língua estrangeira moderna", "lingua estrangeira moderna",
            # ── Termos genéricos ──
            "inglês", "lingua inglesa", "língua inglesa",
            "língua estrangeira", "lingua estrangeira",
            "teacher", "english teacher",
            "educação bilíngue", "bilingual education",
            "inglês instrumental", "ingles instrumenta",
            "proficiência em inglês", "proficiencia em ingles",
        ],
        "nivel_keywords": ["superior", "graduação", "licenciatura", "médio", "qualquer"],
        "re_extra": [
            r"\bprof\s*\.?\s*(de\s*)?ingl(e|ê)s\b",
            r"\bprofessor\b.*\b(ingl(e|ê)s|inglesa|estrangeir)\b",
            r"\bteacher\b",
            r"\benglish\b",
            r"\blingu(a|age) inglesa\b",
            r"\blingu(a|age) estrangeira\b",
            r"\bidiomas?\b",
            r"\bingle?s\b",
            r"\bestrangeiro\b",
        ],
    },
]

# Configuração do filtro: usar regex com word boundaries
FILTER_USE_REGEX: bool = True

# ---------------------------------------------------------------------------
# B7: Configuração de modelos LLM
# A diferença entre os modelos é INTENCIONAL:
# - OPENROUTER_EXTRACTION_MODEL (ou fallback GEMINI_EXTRACTION_MODEL):
#   usado na ingestão (automacao/ai_extractor.py) para extrair dados de HTML.
#   Precisa ser rápido e barato -> google/gemini-2.0-flash-lite
# - OPENROUTER_CHAT_MODEL (ou fallback GEMINI_CHAT_MODEL):
#   usado no chat RAG (backend/app/services/rag.py) para responder perguntas.
#   Precisa de melhor qualidade -> google/gemini-2.0-flash
# Ambos usam o mesmo modelo de embedding: text-embedding-004 (Google, gratuito)
#
# Provedor: OpenRouter (se OPENROUTER_API_KEY estiver definida)
# Fallback:  Google Gemini (via GEMINI_API_KEY)
# ---------------------------------------------------------------------------
GEMINI_EXTRACTION_MODEL: str = os.environ.get("GEMINI_EXTRACTION_MODEL", "gemini-2.0-flash-lite")
GEMINI_CHAT_MODEL: str = os.environ.get("GEMINI_CHAT_MODEL", "gemini-1.5-flash")

# Nomes de modelo no OpenRouter (usam formato "provedor/modelo")
OPENROUTER_EXTRACTION_MODEL: str = os.environ.get("OPENROUTER_EXTRACTION_MODEL", "google/gemini-2.0-flash-lite")
OPENROUTER_CHAT_MODEL: str = os.environ.get("OPENROUTER_CHAT_MODEL", "google/gemini-2.0-flash")

# Palavras-chave para busca no DOU e outros diários oficiais
DOU_SEARCH_TERMS = [
    "concurso público tecnologia informação",
    "concurso público analista sistemas",
    "concurso público desenvolvedor",
    "concurso público professor inglês",
    "edital concurso TI superior",
    "concurso público segurança informação",
    "concurso público ciência dados",
    "concurso público engenharia software",
]

# ---------------------------------------------------------------------------
# Configuração do pipeline
# ---------------------------------------------------------------------------

# B25: Configuração de chunking de PDF
CHUNK_SIZE: int = int(os.environ.get("CHUNK_SIZE", "1000"))
CHUNK_OVERLAP: int = int(os.environ.get("CHUNK_OVERLAP", "200"))

# B19/B27: Intervalo entre requisições a sites (mínimo para não bloquear).
# O rate limiter do extrator Gemini (ai_extractor.py) já garante 2.5s entre
# chamadas à API, então o sleep do scraper é apenas para ser gentil com o site.
SCRAPER_SLEEP_SECONDS: float = float(os.environ.get("SCRAPER_SLEEP_SECONDS", "0.5"))

# User-Agent padrão para todos os scrapers
DEFAULT_HEADERS: dict = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    )
}
