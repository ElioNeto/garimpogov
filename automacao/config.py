"""Escopo de busca do GarimpoGov.

Só são ingeridos concursos que correspondam a pelo menos um dos perfis abaixo.
"""

# ---------------------------------------------------------------------------
# Perfis de vaga aceitos
# ---------------------------------------------------------------------------
# Cada perfil é um dict com:
#   keywords  – ao menos UMA deve aparecer no texto do concurso (case-insensitive)
#   nivel     – nível de escolaridade exigido (usado para filtrar)
# ---------------------------------------------------------------------------

TARGET_PROFILES = [
    {
        "name": "TI - Ensino Superior",
        "keywords": [
            "tecnologia da informação", "analista de ti", "analista de sistemas",
            "desenvolvedor", "desenvolvimento de software", "engenheiro de software",
            "programador", "infraestrutura de ti", "suporte de ti",
            "segurança da informação", "banco de dados", "redes de computadores",
            "ciência da computação", "sistemas de informação", "engenharia de computação",
            "ti ", " ti,", "técnico em informática",
        ],
        "nivel_keywords": ["superior", "graduação", "bacharel", "licenciatura"],
    },
    {
        "name": "Professor de Inglês",
        "keywords": [
            "professor de inglês", "professor de lingua inglesa",
            "professor de língua inglesa", "docente de inglês",
            "inglês", "lingua inglesa", "língua inglesa",
        ],
        "nivel_keywords": ["superior", "graduação", "licenciatura", "médio", "qualquer"],
    },
]

# Palavras-chave para busca no DOU
DOU_SEARCH_TERMS = [
    "concurso público tecnologia informação",
    "concurso público analista sistemas",
    "concurso público desenvolvedor",
    "concurso público professor inglês",
    "edital concurso TI superior",
]
