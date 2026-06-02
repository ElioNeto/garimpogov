"""Gera relatório markdown, faz commit e notifica.

O relatório é commitado no repositório (reports/YYYY-MM-DD.md).
A notificação multicanal (Slack + Telegram) é disparada ao final.
"""
import logging
import os
import subprocess
from collections import Counter
from datetime import date
from typing import List

from automacao.notifier import IngestionResult, notify

logger = logging.getLogger(__name__)


def generate_report(
    concursos: List[dict],
    total_bruto: int = 0,
    erros: list[str] = None,
    duracao_segundos: float = 0.0,
    dry_run: bool = False,
) -> str:
    """Gera relatório markdown com estatísticas detalhadas.

    Args:
        concursos: Lista de concursos ingeridos nesta execução.
        total_bruto: Total de concursos encontrados (antes do insert).
        erros: Lista de erros ocorridos durante a pipeline.
        duracao_segundos: Tempo total de execução.
        dry_run: Se foi uma execução dry-run.

    Returns:
        Conteúdo do relatório em markdown.
    """
    today = date.today().strftime("%d/%m/%Y")
    lines = [
        f"# Relatório de Ingestão - {today}",
        "",
    ]

    if dry_run:
        lines.append("⚠️ *Modo DRY RUN* — nada foi gravado em disco.")
        lines.append("")

    # Estatísticas gerais
    lines.append("## 📊 Estatísticas Gerais")
    lines.append("")
    lines.append(f"| Métrica | Valor |")
    lines.append(f"|---------|-------|")
    lines.append(f"| Total bruto no escopo | {total_bruto} |")
    lines.append(f"| Novos concursos inseridos | {len(concursos)} |")
    lines.append(f"| Duração | {duracao_segundos:.0f}s |")
    if erros:
        lines.append(f"| Erros | {len(erros)} |")
    lines.append("")

    # Por fonte
    if concursos:
        fontes = Counter(c.get("fonte", "Desconhecida") for c in concursos)
        lines.append("## 📡 Por Fonte")
        lines.append("")
        lines.append(f"| Fonte | Quantidade |")
        lines.append(f"|-------|-----------|")
        for fonte, qtd in fontes.most_common():
            lines.append(f"| {fonte} | {qtd} |")
        lines.append("")

        # Por perfil (heurística simples: cargos contendo "inglês" ou "ingres" = inglês)
        perfis = Counter()
        for c in concursos:
            cargos_text = " ".join(c.get("cargos") or []).lower()
            if any(w in cargos_text for w in ["inglês", "ingles", "teacher", "english", "língua inglesa"]):
                perfis["Professor de Inglês"] += 1
            elif any(w in cargos_text for w in ["ti", "tecnologia", "informática", "analista", "desenvolvedor", "programador", "dados", "sistemas", "computação", "redes", "suporte"]):
                perfis["TI"] += 1
            else:
                perfis["Outros"] += 1
        lines.append("## 🎯 Por Perfil")
        lines.append("")
        lines.append(f"| Perfil | Quantidade |")
        lines.append(f"|-------|-----------|")
        for perfil, qtd in perfis.most_common():
            lines.append(f"| {perfil} | {qtd} |")
        lines.append("")

    # Erros
    if erros:
        lines.append("## ❌ Erros")
        lines.append("")
        for err in erros:
            lines.append(f"- {err}")
        lines.append("")

    # Detalhamento
    lines.append("## 📋 Concursos Ingeridos")
    lines.append("")
    if not concursos:
        lines.append("_Nenhum novo concurso encontrado hoje._")
    else:
        for c in concursos:
            fonte = c.get("fonte", "?")
            lines.append(f"### [{fonte}] {c.get('instituicao', 'N/A')}")
            lines.append(f"- **Link:** {c.get('link_edital', 'N/A')}")
            if c.get("cargos"):
                lines.append(f"- **Cargos:** {', '.join(c['cargos'])}")
            lines.append("")
    return "\n".join(lines)


def save_and_commit_artifacts(report_content: str) -> None:
    """Salva o relatório em reports/ e o JSON em data/, depois faz commit + push."""
    today = date.today().strftime("%Y-%m-%d")
    report_path = f"reports/{today}.md"
    os.makedirs("reports", exist_ok=True)
    with open(report_path, "w", encoding="utf-8") as f:
        f.write(report_content)
    logger.info(f"Relatório salvo em {report_path}")

    # Lista de arquivos para commitar
    files_to_add = [report_path, "data/concursos.json"]

    for fpath in files_to_add:
        if os.path.exists(fpath):
            subprocess.run(["git", "add", fpath], check=True)

    result = subprocess.run(["git", "diff", "--cached", "--quiet"], capture_output=True)
    if result.returncode != 0:
        try:
            subprocess.run(
                ["git", "commit", "-m", f"chore: ingestion artifacts {today}"],
                check=True,
                capture_output=True,
                text=True,
            )
            # Pull rebase antes do push para evitar conflito com commits concorrentes
            subprocess.run(
                ["git", "pull", "--rebase", "--autostash"],
                check=False,
                capture_output=True,
                text=True,
            )
            subprocess.run(["git", "push"], check=True, capture_output=True, text=True)
            logger.info("Relatório + JSON commitados e enviados ao repositório")
        except subprocess.CalledProcessError as e:
            logger.warning(f"Falha ao commitar/push: {e.stderr or e}")
            logger.warning("Os artefatos estão salvos em disco localmente.")
    else:
        logger.info("Sem mudanças para commitar")


def save_and_notify(
    newly_ingested: List[dict],
    total_bruto: int = 0,
    erros: list[str] = None,
    duracao_segundos: float = 0.0,
    dry_run: bool = False,
) -> dict[str, bool]:
    """Gera relatório, commita e notifica.

    Returns:
        Resultados da notificação por canal (pode ser vazio se nada configurado).
    """
    report = generate_report(
        concursos=newly_ingested,
        total_bruto=total_bruto,
        erros=erros,
        duracao_segundos=duracao_segundos,
        dry_run=dry_run,
    )

    if not dry_run:
        try:
            save_and_commit_artifacts(report)
        except Exception as e:
            logger.error(f"Erro ao salvar/commitar artefatos: {e}")

    # Monta resultado para notificação
    result = IngestionResult(
        total_bruto=total_bruto,
        novos_inseridos=len(newly_ingested),
        dry_run=dry_run,
        erros=erros or [],
        duracao_segundos=duracao_segundos,
    )

    # Preenche fontes
    for c in newly_ingested:
        fonte = c.get("fonte", "?")
        result.fontes[fonte] = result.fontes.get(fonte, 0) + 1

    # Preenche perfis
    for c in newly_ingested:
        cargos_text = " ".join(c.get("cargos") or []).lower()
        if any(w in cargos_text for w in ["inglês", "ingles", "teacher", "english"]):
            result.perfis["Professor de Inglês"] = result.perfis.get("Professor de Inglês", 0) + 1
        elif any(w in cargos_text for w in ["ti", "tecnologia", "informática", "analista"]):
            result.perfis["TI"] = result.perfis.get("TI", 0) + 1

    return notify(result)
