"""Orquestrador principal da ingestão - chamado pelo GitHub Actions.

Processa todas as fontes registradas (portais, bancas, diários oficiais,
municípios) em paralelo e gera dois arquivos markdown:
  - data/concursos_abertos.md  → TODOS os concursos encontrados
  - data/concursos_filtrados.md → apenas TI + Professor de Inglês

NÃO depende de banco de dados PostgreSQL — tudo vai para .md no repositório.
"""
import logging
import os
import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Callable

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

# ── Portais nacionais ────────────────────────────────────────────────
from automacao.scraper_pci import scrape_pci
from automacao.scraper_tec import scrape_tec
from automacao.scraper_qconcursos import scrape_qconcursos
from automacao.scraper_estrategia import scrape_estrategia

# ── Diários oficiais ─────────────────────────────────────────────────
from automacao.scraper_dou import scrape_dou
from automacao.scraper_rs import scrape_doers
from automacao.scraper_sc import scrape_doesc
from automacao.scraper_doesp import scrape_doesp
from automacao.scraper_doerj import scrape_doerj
from automacao.scraper_doemg import scrape_doemg
from automacao.scraper_doepr import scrape_doepr
from automacao.scraper_doeba import scrape_doeba

# ── Bancas organizadoras ────────────────────────────────────────────
from automacao.bancas.acafe import scrape_acafe
from automacao.bancas.amauc import scrape_amauc
from automacao.bancas.ameosc import scrape_ameosc
from automacao.bancas.aocp import scrape_aocp
from automacao.bancas.cebraspe import scrape_cebraspe
from automacao.bancas.cesgranrio import scrape_cesgranrio
from automacao.bancas.consulplan import scrape_consulplan
from automacao.bancas.cs_ufg import scrape_cs_ufg
from automacao.bancas.fafipa import scrape_fafipa
from automacao.bancas.faurgs import scrape_faurgs
from automacao.bancas.fcc import scrape_fcc
from automacao.bancas.fepese import scrape_fepese
from automacao.bancas.fgv import scrape_fgv
from automacao.bancas.fundatec import scrape_fundatec
from automacao.bancas.furb import scrape_furb
from automacao.bancas.iades import scrape_iades
from automacao.bancas.ibfc import scrape_ibfc
from automacao.bancas.idecan import scrape_idecan
from automacao.bancas.ieses import scrape_ieses
from automacao.bancas.ippec import scrape_ippec
from automacao.bancas.lasalle import scrape_lasalle
from automacao.bancas.legalle import scrape_legalle
from automacao.bancas.objetiva import scrape_objetiva
from automacao.bancas.quadrix import scrape_quadrix
from automacao.bancas.vunesp import scrape_vunesp

# ── Diários municipais ──────────────────────────────────────────────
from automacao.municipios.porto_alegre import PortoAlegre
from automacao.municipios.florianopolis import Florianopolis
from automacao.municipios.joinville import Joinville
from automacao.municipios.caxias_do_sul import CaxiasDoSul
from automacao.municipios.blumenau import Blumenau

# ── Pipeline comum ─────────────────────────────────────────────────
from automacao.json_store import merge_new, load_all, save_all
from automacao.filters import matches_scope
from automacao.commit_backup import save_and_notify

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)

DRY_RUN = os.environ.get("DRY_RUN", "false").lower() == "true"

# Número de scrapers rodando simultaneamente
# O rate limiter do OpenRouter (2.5s entre chamadas) é global com lock,
# então múltiplas threads competem pela mesma cota — o que é desejado.
PARALLEL_WORKERS = int(os.environ.get("PARALLEL_WORKERS", "6"))

# ---------------------------------------------------------------------------
# Registro de fontes: cada entrada é (nome, callable)
# O callable deve retornar list[dict]
# ---------------------------------------------------------------------------

FONTES: list[tuple[str, Callable[[], list[dict]]]] = [
    # ── Portais nacionais ──
    ("PCI Concursos", scrape_pci),
    ("Tec Concursos", scrape_tec),
    ("QConcursos", scrape_qconcursos),
    ("Estrategia", scrape_estrategia),
    # ── Diários oficiais federais/estaduais ──
    ("DOU", lambda: scrape_dou(days_back=7)),
    ("DOE-RS", scrape_doers),
    ("DOE-SC", scrape_doesc),
    ("DOE-SP", scrape_doesp),
    ("DOE-RJ", scrape_doerj),
    ("DOE-MG", scrape_doemg),
    ("DOE-PR", scrape_doepr),
    ("DOE-BA", scrape_doeba),
    # ── Bancas organizadoras (25) ──
    ("ACAFe", scrape_acafe),
    ("AMAUC", scrape_amauc),
    ("AMEOSC", scrape_ameosc),
    ("AOCP", scrape_aocp),
    ("CEBRASPE", scrape_cebraspe),
    ("CESGRANRIO", scrape_cesgranrio),
    ("CONSULPLAN", scrape_consulplan),
    ("CS-UFG", scrape_cs_ufg),
    ("FAFIPA", scrape_fafipa),
    ("FAURGS", scrape_faurgs),
    ("FCC", scrape_fcc),
    ("FEPESE", scrape_fepese),
    ("FGV", scrape_fgv),
    ("FUNDATEC", scrape_fundatec),
    ("FURB", scrape_furb),
    ("IADES", scrape_iades),
    ("IBFC", scrape_ibfc),
    ("IDECAN", scrape_idecan),
    ("IESES", scrape_ieses),
    ("IPPEC", scrape_ippec),
    ("LaSalle", scrape_lasalle),
    ("Legalle", scrape_legalle),
    ("Objetiva", scrape_objetiva),
    ("Quadrix", scrape_quadrix),
    ("VUNESP", scrape_vunesp),
]

# ── Diários municipais ──
MUNICIPIOS: list[tuple[str, Callable[[], list[dict]]]] = [
    ("Porto Alegre", PortoAlegre().scrape),
    ("Florianópolis", Florianopolis().scrape),
    ("Joinville", Joinville().scrape),
    ("Caxias do Sul", CaxiasDoSul().scrape),
    ("Blumenau", Blumenau().scrape),
]


def _scrape_source(nome: str, func: Callable[[], list[dict]]) -> tuple[str, list[dict], str | None]:
    """Executa um scraper individual e retorna (nome, resultados, erro).

    Usado como alvo do ThreadPoolExecutor para paralelismo.
    """
    logger.info(f"[{nome}] Iniciando...")
    try:
        dados = func()
        logger.info(f"[{nome}] OK — {len(dados)} extraidos")
        return nome, dados, None
    except Exception as e:
        msg = f"[{nome}] Falha: {e}"
        logger.error(msg)
        return nome, [], msg


def scrape_fontes() -> tuple[list[dict], list[str]]:
    """Executa scraping de todas as fontes registradas em paralelo.

    Returns:
        (resultados, erros) — resultados é a lista de concursos no escopo,
        erros é a lista de mensagens de erro por fonte.
    """
    todas_as_fontes = FONTES + MUNICIPIOS
    n_total = len(todas_as_fontes)

    logger.info(f"Processando {n_total} fontes com {PARALLEL_WORKERS} workers paralelos...")

    resultados = []
    erros = []
    concluidas = 0

    with ThreadPoolExecutor(max_workers=PARALLEL_WORKERS) as executor:
        futures = {
            executor.submit(_scrape_source, nome, func): nome
            for nome, func in todas_as_fontes
        }

        for future in as_completed(futures):
            nome = futures[future]
            try:
                _, dados, erro = future.result()
                resultados.extend(dados)
                if erro:
                    erros.append(erro)
            except Exception as e:
                msg = f"[{nome}] Erro inesperado na thread: {e}"
                logger.error(msg)
                erros.append(msg)

            concluidas += 1
            logger.info(f"Progresso: {concluidas}/{n_total} fontes concluídas")

    logger.info(f"Scraping concluído: {len(resultados)} concursos extraidos, {len(erros)} fontes com erro")
    return resultados, erros


def _generate_concursos_abertos_md(concursos: list[dict]) -> str:
    """Gera markdown com TODOS os concursos abertos."""
    from datetime import date
    today = date.today().strftime("%d/%m/%Y")
    lines = [
        f"# GarimpoGov — Todos os Concursos Abertos",
        f"",
        f"_Atualizado em {today}_",
        f"",
        f"Total: **{len(concursos)}** concursos encontrados.",
        f"",
        "---",
        "",
    ]
    if not concursos:
        lines.append("_Nenhum concurso encontrado._")
    else:
        # Agrupa por fonte
        from collections import defaultdict
        por_fonte = defaultdict(list)
        for c in concursos:
            por_fonte[c.get("fonte", "Outros")].append(c)

        for fonte in sorted(por_fonte.keys()):
            items = por_fonte[fonte]
            lines.append(f"## {fonte} ({len(items)})")
            lines.append("")
            for c in items:
                inst = c.get("instituicao", "N/A")
                link = c.get("link_edital", "")
                cargos = ", ".join(c.get("cargos") or [])
                orgao = c.get("orgao", "")
                salario = c.get("salario_maximo", "")
                encerra = c.get("data_encerramento", "")
                lines.append(f"### {inst}")
                if link:
                    lines.append(f"[🔗 Edital]({link})")
                if cargos:
                    lines.append(f"- **Cargos:** {cargos}")
                if orgao:
                    lines.append(f"- **Órgão/Local:** {orgao}")
                if salario:
                    lines.append(f"- **Salário máx.:** {salario}")
                if encerra:
                    lines.append(f"- **Encerramento:** {encerra}")
                lines.append("")
            lines.append("---")
            lines.append("")
    return "\n".join(lines)


def _generate_concursos_filtrados_md(concursos: list[dict]) -> str:
    """Gera markdown com os concursos filtrados (TI + Professor de Inglês)."""
    return _generate_concursos_abertos_md(concursos).replace(
        "# GarimpoGov — Todos os Concursos Abertos",
        "# GarimpoGov — Concursos Filtrados (TI + Professor de Inglês)",
    )


def _save_md(filepath: str, content: str):
    os.makedirs(os.path.dirname(filepath), exist_ok=True)
    with open(filepath, "w", encoding="utf-8") as f:
        f.write(content)
    logger.info(f"Salvo {filepath} ({len(content)} bytes)")


def run():
    inicio = time.monotonic()

    logger.info("=" * 60)
    logger.info("GarimpoGov Ingestion Pipeline START")
    logger.info(f"Modo: {'DRY RUN' if DRY_RUN else 'PRODUÇÃO'}")
    logger.info(f"Escopo: TI + Professor de Inglês (filtro local)")
    logger.info(f"Fontes registradas: {len(FONTES)} + {len(MUNICIPIOS)} municipios")
    logger.info("=" * 60)

    # ── Fase 1: Scraping (todos os concursos, sem filtro) ─────────
    concursos_raw, erros_scraping = scrape_fontes()
    logger.info(f"Total extraído (todos os concursos): {len(concursos_raw)}")

    # ── Fase 2: Filtro local ─────────────────────────────────────
    concursos_filtrados = [c for c in concursos_raw if matches_scope(c)]
    logger.info(f"Após filtro local (TI + Professor): {len(concursos_filtrados)}")

    if DRY_RUN:
        logger.info("[DRY RUN] Pulando gravação em disco.")
        for c in concursos_filtrados[:20]:
            logger.info(
                f"  [{c.get('fonte','?')}] {c.get('instituicao','?')} "
                f"| {c.get('cargos')} | {c.get('link_edital','')}"
            )
        duracao = time.monotonic() - inicio
        save_and_notify(
            newly_ingested=[],
            total_bruto=len(concursos_filtrados),
            erros=erros_scraping,
            duracao_segundos=duracao,
            dry_run=True,
        )
        return

    # ── Fase 3: Merge no JSON + geração dos .md ──────────────────
    from automacao.json_store import _dedup_key as _json_key, purge_all
    existing_before = {_json_key(c) for c in load_all()}

    # Limpa entradas antigas com placeholder E concursos já encerrados
    purge_all()

    # Salva TODOS os concursos no JSON (dedup por link_edital)
    merge_new(concursos_raw)

    # Gera concursos_abertos.md a partir do acervo completo (já merged)
    todos = load_all()
    md_abertos = _generate_concursos_abertos_md(todos)
    _save_md("data/concursos_abertos.md", md_abertos)

    # Gera concursos_filtrados.md a partir do acervo completo filtrado
    md_filtrados = _generate_concursos_filtrados_md(
        [c for c in todos if matches_scope(c)]
    )
    _save_md("data/concursos_filtrados.md", md_filtrados)

    # ── Fase 4: Relatório + Notificação (só novos filtrados) ────
    duracao = time.monotonic() - inicio

    # Apenas concursos filtrados que são realmente novos
    newly_ingested_filtered = [
        c for c in concursos_filtrados
        if _json_key(c) not in existing_before
    ]
    logger.info(
        f"Novos no filtro: {len(newly_ingested_filtered)} "
        f"(de {len(concursos_filtrados)} totais no filtro)"
    )

    resultados_notificacao = save_and_notify(
        newly_ingested=newly_ingested_filtered,
        total_bruto=len(concursos_filtrados),
        erros=erros_scraping,
        duracao_segundos=duracao,
        dry_run=False,
    )

    logger.info("=" * 60)
    logger.info(f"Pipeline DONE: {len(concursos_filtrados)} concursos no filtro")
    logger.info(f"Arquivos: data/concursos_abertos.md + data/concursos_filtrados.md")
    logger.info(f"Total bruto (todos): {len(concursos_raw)}")
    logger.info(f"Duração: {duracao:.0f}s")
    if erros_scraping:
        logger.info(f"Erros: {len(erros_scraping)}")
    if resultados_notificacao:
        for canal, ok in resultados_notificacao.items():
            status = "✅" if ok else "❌"
            logger.info(f"Notificação {canal}: {status}")
    else:
        logger.info(
            "Nenhum canal de notificação configurado. "
            "Para ativar, defina no repositório (Settings → Secrets):\n"
            "  • SLACK_BOT_TOKEN + SLACK_CHANNEL\n"
            "  • ou SLACK_WEBHOOK_URL\n"
            "  • ou TELEGRAM_BOT_TOKEN + TELEGRAM_CHAT_ID\n"
            "As notificações são opcionais — o pipeline funciona sem elas."
        )
    logger.info("=" * 60)


if __name__ == "__main__":
    run()
