"""Gera relatório markdown e faz commit no GitHub."""
import logging
import os
import subprocess
from datetime import date
from typing import List

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def generate_report(concursos: List[dict]) -> str:
    today = date.today().strftime("%d/%m/%Y")
    lines = [
        f"# Relatório de Ingestão - {today}",
        "",
        f"**Total de novos concursos:** {len(concursos)}",
        "",
        "## Concursos Ingeridos",
        "",
    ]
    if not concursos:
        lines.append("_Nenhum novo concurso encontrado hoje._")
    else:
        for c in concursos:
            fonte = c.get("fonte", "PCI")
            lines.append(f"### [{fonte}] {c.get('instituicao', 'N/A')}")
            lines.append(f"- **Link:** {c.get('link_edital', 'N/A')}")
            lines.append(f"- **Status:** {c.get('status', 'N/A')}")
            if c.get("cargos"):
                lines.append(f"- **Cargos:** {', '.join(c['cargos'])}")
            lines.append("")
    return "\n".join(lines)


def save_and_commit_report(report_content: str) -> None:
    today = date.today().strftime("%Y-%m-%d")
    report_path = f"reports/{today}.md"
    os.makedirs("reports", exist_ok=True)
    with open(report_path, "w", encoding="utf-8") as f:
        f.write(report_content)
    logger.info(f"Relatório salvo em {report_path}")

    subprocess.run(["git", "add", report_path], check=True)
    result = subprocess.run(["git", "diff", "--cached", "--quiet"], capture_output=True)
    if result.returncode != 0:
        subprocess.run(["git", "commit", "-m", f"chore: ingestion report {today}"], check=True)
        subprocess.run(["git", "push"], check=True)
        logger.info("Relatório commitado")
    else:
        logger.info("Sem mudanças para commitar")
