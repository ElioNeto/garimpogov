"""Orquestrador principal da ingestão - chamado pelo GitHub Actions.

Processa todas as fontes registradas (portais, bancas, diários oficiais,
municípios) em paralelo e salva os resultados em JSON no repositório.

Ao final, gera relatório markdown, commita JSON + relatório no repositório e
envia notificação multicanal (Slack + Telegram).

NÃO depende de banco de dados PostgreSQL — tudo vai para data/concursos.json.
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
        logger.info(f"[{nome}] OK — {len(dados)} no escopo")
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

    logger.info(f"Scraping concluído: {len(resultados)} concursos no escopo, {len(erros)} fontes com erro")
    return resultados, erros


def run():
    inicio = time.monotonic()

    logger.info("=" * 60)
    logger.info("GarimpoGov Ingestion Pipeline START")
    logger.info(f"Modo: {'DRY RUN' if DRY_RUN else 'PRODUÇÃO'}")
    logger.info(f"Escopo: TI + Professor de Inglês")
    logger.info(f"Fontes registradas: {len(FONTES)} + {len(MUNICIPIOS)} municipios")
    logger.info("=" * 60)

    # ── Fase 1: Scraping ──────────────────────────────────────────
    concursos_raw, erros_scraping = scrape_fontes()
    logger.info(f"Total bruto no escopo: {len(concursos_raw)}")

    if DRY_RUN:
        logger.info("[DRY RUN] Pulando gravação em disco.")
        for c in concursos_raw[:20]:
            logger.info(
                f"  [{c.get('fonte','?')}] {c.get('instituicao','?')} "
                f"| {c.get('cargos')} | {c.get('link_edital','')}"
            )
        duracao = time.monotonic() - inicio
        save_and_notify(
            newly_ingested=[],
            total_bruto=len(concursos_raw),
            erros=erros_scraping,
            duracao_segundos=duracao,
            dry_run=True,
        )
        return

    # ── Fase 2: Merge no JSON ─────────────────────────────────────
    newly_ingested = merge_new(concursos_raw)

    # ── Fase 3: Relatório + Notificação ───────────────────────────
    duracao = time.monotonic() - inicio

    resultados_notificacao = save_and_notify(
        newly_ingested=newly_ingested,
        total_bruto=len(concursos_raw),
        erros=erros_scraping,
        duracao_segundos=duracao,
        dry_run=False,
    )

    logger.info("=" * 60)
    logger.info(f"Pipeline DONE: {len(newly_ingested)} novos concursos")
    logger.info(f"Duração: {duracao:.0f}s")
    logger.info(f"Total bruto no escopo: {len(concursos_raw)}")
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
