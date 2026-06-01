"""Testes para o filtro de escopo (automacao/filters.py).

B29: testa regras de perfil com cenários reais e borda.
"""
import pytest
from automacao.filters import matches_scope


class TestMatchesScope:
    """Cobertura das regras de filtro."""

    # ── Perfil: Professor de Inglês (qualquer nível) ──────────────────

    def test_prof_ingles_qualquer_nivel(self):
        """Professor de Inglês aceita qualquer nível."""
        concurso = {
            "instituicao": "Prefeitura de Joinville",
            "cargos": ["professor de inglês"],
        }
        assert matches_scope(concurso) is True

    def test_prof_ingles_medio(self):
        """Professor de Inglês aceita ensino médio."""
        concurso = {
            "instituicao": "Prefeitura",
            "cargos": ["professor de inglês", "ensino médio"],
        }
        assert matches_scope(concurso) is True

    # ── Perfil: TI (nível superior obrigatório) ───────────────────────

    def test_ti_superior_explicito(self):
        """TI com nível superior explícito → aprovado."""
        concurso = {
            "instituicao": "Banco do Brasil",
            "cargos": ["analista de sistemas", "nível superior"],
        }
        assert matches_scope(concurso) is True

    def test_ti_sem_nivel_superior_pass(self):
        """TI sem menção de nível mas com keyword → aprovado (falso-positivo aceito)."""
        concurso = {
            "instituicao": "Empresa de TI",
            "cargos": ["desenvolvedor"],
        }
        assert matches_scope(concurso) is True

    def test_ti_medio_explicito_block(self):
        """TI com menção explícita de nível médio → rejeitado."""
        concurso = {
            "instituicao": "Prefeitura",
            "cargos": ["técnico em informática", "nível médio"],
        }
        assert matches_scope(concurso) is False

    def test_ti_fundamental_block(self):
        """TI com menção de fundamental → rejeitado."""
        concurso = {
            "instituicao": "Prefeitura",
            "cargos": ["auxiliar de TI", "ensino fundamental"],
        }
        assert matches_scope(concurso) is False

    # ── Sem keyword → rejeitado ───────────────────────────────────────

    def test_sem_keyword_rejeita(self):
        """Concurso sem qualquer keyword de perfil → rejeitado."""
        concurso = {
            "instituicao": "Prefeitura de Santos",
            "cargos": ["auxiliar de serviços gerais"],
        }
        assert matches_scope(concurso) is False

    def test_keyword_orgao(self):
        """Keyword no orgao → aprovado."""
        concurso = {
            "instituicao": "Secretaria de Educação",
            "cargos": [],
            "orgao": "tecnologia da informação",
        }
        assert matches_scope(concurso) is True

    # ── Casos reais de filtro (B2) ────────────────────────────────────

    def test_concurso_superior_mas_medio_no_texto(self):
        """Concurso com 'nível superior' explícito + 'médio' na descrição → aprovado.
        
        O concurso tem vagas de nível superior (analista de TI), mesmo que
        a descrição mencione que também há vagas de nível médio.
        """
        concurso = {
            "instituicao": "Prefeitura",
            "cargos": ["analista de TI", "nível superior"],
            "orgao": "concurso para ensino médio e superior",
        }
        # 'nível superior' está nos cargos → aprovado
        assert matches_scope(concurso) is True

    def test_concurso_apenas_superior(self):
        """Apenas nível superior, sem médio no texto → aprovado."""
        concurso = {
            "instituicao": "Banco do Brasil",
            "cargos": ["escriturário", "nível superior"],
            "orgao": "agente de tecnologia",
        }
        assert matches_scope(concurso) is True

    # ── Novos casos com regex word boundary ────────────────────────────

    def test_ti_word_boundary(self):
        """'TI' como palavra isolada → aprovado (regex \\bti\\b)."""
        concurso = {
            "instituicao": "Secretaria de TI",
            "cargos": ["analista"],
        }
        assert matches_scope(concurso) is True

    def test_ti_dentro_de_palavra(self):
        """'ti' dentro de palavra (ex: 'atividades') → NÃO aprovado."""
        concurso = {
            "instituicao": "Prefeitura",
            "cargos": ["atividades administrativas"],
        }
        assert matches_scope(concurso) is False

    def test_prof_de_ingles_variante(self):
        """'prof de inglês' → aprovado."""
        concurso = {
            "instituicao": "Prefeitura",
            "cargos": ["prof de inglês"],
        }
        assert matches_scope(concurso) is True

    def test_prof_ponto_de_ingles(self):
        """'prof. de inglês' → aprovado."""
        concurso = {
            "instituicao": "Escola",
            "cargos": ["prof. de inglês"],
        }
        assert matches_scope(concurso) is True

    def test_dba_keyword(self):
        """'dba' → aprovado."""
        concurso = {
            "instituicao": "Empresa",
            "cargos": ["dba senior"],
        }
        assert matches_scope(concurso) is True

    def test_front_end(self):
        """'front-end', 'front end' → aprovado (regex front.?end)."""
        concurso = {
            "instituicao": "Tech Co",
            "cargos": ["front-end developer"],
        }
        assert matches_scope(concurso) is True

    def test_back_end(self):
        """'back end' → aprovado."""
        concurso = {
            "instituicao": "Tech Co",
            "cargos": ["back end developer"],
        }
        assert matches_scope(concurso) is True

    def test_cientifico_nao_confunde_ti(self):
        """'técnico científico' → NÃO deve casar com 'ti' (regra de word boundary)."""
        concurso = {
            "instituicao": "IFSC",
            "cargos": ["técnico científico"],
        }
        assert matches_scope(concurso) is False

    def test_ti_medio_explicito_sem_superior(self):
        """TI com 'nível médio' e SEM 'superior' → rejeitado."""
        concurso = {
            "instituicao": "Prefeitura",
            "cargos": ["técnico em informática", "nível médio"],
        }
        assert matches_scope(concurso) is False
