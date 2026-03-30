"""Generate a markdown report and commit it to GitHub."""
import logging
import os
import subprocess
from datetime import date
from typing import List

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def generate_report(concursos: List[dict]) -> str:
    """Generate a markdown report of today's ingested concursos."""
    today = date.today().strftime("%d/%m/%Y")
    lines = [
        f"# Relatorio de Ingestion - {today}",
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
            lines.append(f"### {c.get('instituicao', 'N/A')}")
            lines.append(f"- **Link:** {c.get('link_edital', 'N/A')}")
            lines.append(f"- **Status:** {c.get('status', 'N/A')}")
            if c.get('cargos'):
                cargos_str = ", ".join(c['cargos'])
                lines.append(f"- **Cargos:** {cargos_str}")
            lines.append("")

    return "\n".join(lines)


def save_and_commit_report(report_content: str) -> None:
    """Save report to reports/ directory and commit to GitHub."""
    today = date.today().strftime("%Y-%m-%d")
    report_path = f"reports/{today}.md"

    os.makedirs("reports", exist_ok=True)
    with open(report_path, "w", encoding="utf-8") as f:
        f.write(report_content)

    logger.info(f"Report saved to {report_path}")

    # Configure git (GitHub Actions environment)
    subprocess.run(["git", "config", "user.email", "github-actions@github.com"], check=True)
    subprocess.run(["git", "config", "user.name", "GitHub Actions"], check=True)
    subprocess.run(["git", "add", report_path], check=True)

    result = subprocess.run(
        ["git", "diff", "--cached", "--quiet"],
        capture_output=True
    )
    if result.returncode != 0:
        subprocess.run(
            ["git", "commit", "-m", f"chore: ingestion report {today}"],
            check=True
        )
        subprocess.run(["git", "push"], check=True)
        logger.info("Report committed and pushed")
    else:
        logger.info("No changes to commit")
