"""Sistema de notificação multicanal para resultados da ingestão.

Canais suportados:
  - Slack (OAuth token via chat.postMessage ou webhook)
  - Telegram (bot token + chat_id)
  - Console (logs)

Cada canal é ativado via variável de ambiente:

  # Slack via OAuth (recomendado — usa a Web API)
  SLACK_BOT_TOKEN=xoxb-1234567890-...
  SLACK_CHANNEL=C1234567890

  # Slack via Webhook (alternativa)
  SLACK_WEBHOOK_URL=https://hooks.slack.com/services/...

  # Telegram
  TELEGRAM_BOT_TOKEN=123456:ABC-DEF...
  TELEGRAM_CHAT_ID=-100123456789
"""
import json
import logging
import os
from dataclasses import dataclass, field
from datetime import date
from typing import Optional

import requests

logger = logging.getLogger(__name__)


@dataclass
class IngestionResult:
    """Resultado consolidado de uma execução da pipeline."""
    total_bruto: int = 0
    novos_inseridos: int = 0
    dry_run: bool = False
    fontes: dict[str, int] = field(default_factory=dict)
    perfis: dict[str, int] = field(default_factory=dict)
    erros: list[str] = field(default_factory=list)
    duracao_segundos: float = 0.0


# ── Formatadores de mensagem ─────────────────────────────────────────

def _build_message_text(result: IngestionResult) -> str:
    """Constrói o corpo da mensagem de notificação."""
    hoje = date.today().strftime("%d/%m/%Y")
    lines = [
        f"📋 *GarimpoGov — Relatório de Ingestão*",
        f"📅 {hoje}",
        f"⏱ {result.duracao_segundos:.0f}s",
        "",
    ]

    if result.dry_run:
        lines.append("⚠️ *Modo: DRY RUN* (nada foi gravado em disco)")
        lines.append("")

    if result.erros:
        lines.append(f"❌ *Erros:* {len(result.erros)}")
        for err in result.erros[:5]:
            lines.append(f"  · {err}")
        if len(result.erros) > 5:
            lines.append(f"  · ... e mais {len(result.erros)-5}")
        lines.append("")

    lines.append(f"📊 *Total bruto no escopo:* {result.total_bruto}")
    lines.append(f"✅ *Novos concursos inseridos:* {result.novos_inseridos}")
    lines.append("")

    if result.fontes:
        lines.append("*Por fonte:*")
        for fonte, qtd in sorted(result.fontes.items(), key=lambda x: -x[1]):
            if qtd > 0:
                lines.append(f"  · {fonte}: {qtd}")
        lines.append("")

    if result.perfis:
        lines.append("*Por perfil:*")
        for perfil, qtd in sorted(result.perfis.items(), key=lambda x: -x[1]):
            if qtd > 0:
                lines.append(f"  · {perfil}: {qtd}")
        lines.append("")

    if result.novos_inseridos > 0:
        lines.append("🔗 Detalhes: vide reports/ no repositório")

    return "\n".join(lines)


def _build_slack_blocks(result: IngestionResult) -> list[dict]:
    """Constrói blocks no formato Slack Block Kit para mensagem rica.

    Usado apenas com OAuth (chat.postMessage). Com webhook cai para
    texto plano com mrkdwn.
    """
    blocks = []

    # Header
    blocks.append({
        "type": "header",
        "text": {"type": "plain_text", "text": "📋 GarimpoGov — Relatório de Ingestão"}
    })

    # Metadados
    hoje = date.today().strftime("%d/%m/%Y")
    blocks.append({
        "type": "section",
        "fields": [
            {"type": "mrkdwn", "text": f"*Data:*\n{hoje}"},
            {"type": "mrkdwn", "text": f"*Duração:*\n{result.duracao_segundos:.0f}s"},
        ]
    })

    if result.dry_run:
        blocks.append({
            "type": "section",
            "text": {"type": "mrkdwn", "text": "⚠️ *Modo DRY RUN* — nada foi gravado em disco"}
        })

    # Erros
    if result.erros:
        err_text = "\n".join(f"· {e}" for e in result.erros[:5])
        if len(result.erros) > 5:
            err_text += f"\n· ... e mais {len(result.erros)-5}"
        blocks.append({
            "type": "section",
            "text": {"type": "mrkdwn", "text": f"❌ *Erros ({len(result.erros)}):*\n{err_text}"}
        })

    # Estatísticas
    blocks.append({
        "type": "section",
        "fields": [
            {"type": "mrkdwn", "text": f"*📊 Bruto no escopo:*\n{result.total_bruto}"},
            {"type": "mrkdwn", "text": f"*✅ Novos inseridos:*\n{result.novos_inseridos}"},
        ]
    })

    # Por fonte
    if result.fontes:
        fontes_ord = sorted(result.fontes.items(), key=lambda x: -x[1])
        # Duas colunas para economizar espaço
        linhas = []
        for i in range(0, len(fontes_ord), 2):
            par = fontes_ord[i]
            linha = f"· {par[0]}: {par[1]}"
            if i + 1 < len(fontes_ord):
                linha += f"        · {fontes_ord[i+1][0]}: {fontes_ord[i+1][1]}"
            linhas.append(linha)
        blocks.append({
            "type": "section",
            "text": {"type": "mrkdwn", "text": f"*📡 Por fonte:*\n" + "\n".join(linhas[:10])}
        })

    # Por perfil
    if result.perfis:
        perfis_text = "\n".join(f"· {p}: {q}" for p, q in sorted(result.perfis.items(), key=lambda x: -x[1]))
        blocks.append({
            "type": "section",
            "text": {"type": "mrkdwn", "text": f"*🎯 Por perfil:*\n{perfis_text}"}
        })

    if result.novos_inseridos > 0:
        blocks.append({
            "type": "context",
            "elements": [
                {"type": "mrkdwn", "text": "🔗 Detalhes no repositório — reports/"}
            ]
        })

    # Divider final
    blocks.append({"type": "divider"})

    return blocks


# ── Canais ───────────────────────────────────────────────────────────

def _notify_slack_oauth(text: str, bot_token: str, channel: str, result: IngestionResult) -> bool:
    """Envia notificação para o Slack via Web API (chat.postMessage) com OAuth.

    Usa Block Kit para mensagem mais rica. Se falhar, cai para texto plano.
    """
    try:
        blocks = _build_slack_blocks(result)
        payload = {
            "channel": channel,
            "text": text,  # fallback para notificações push
            "blocks": blocks,
            "mrkdwn": True,
        }
        headers = {
            "Authorization": f"Bearer {bot_token}",
            "Content-Type": "application/json",
        }
        r = requests.post(
            "https://slack.com/api/chat.postMessage",
            json=payload,
            headers=headers,
            timeout=15,
        )
        r.raise_for_status()
        resp = r.json()
        if not resp.get("ok"):
            logger.error(f"Slack API error: {resp.get('error', 'unknown')}")
            return False
        logger.info("Notificação Slack OAuth enviada com sucesso")
        return True
    except Exception as e:
        logger.error(f"Falha ao enviar notificação Slack OAuth: {e}")
        # Fallback: tenta webhook se disponível
        slack_webhook = os.environ.get("SLACK_WEBHOOK_URL")
        if slack_webhook:
            logger.info("Tentando fallback para webhook...")
            return _notify_slack_webhook(text, slack_webhook)
        return False


def _notify_slack_webhook(text: str, webhook_url: str) -> bool:
    """Envia notificação para o Slack via webhook."""
    try:
        payload = {"text": text, "mrkdwn": True}
        r = requests.post(webhook_url, json=payload, timeout=15)
        r.raise_for_status()
        logger.info("Notificação Slack webhook enviada com sucesso")
        return True
    except Exception as e:
        logger.error(f"Falha ao enviar notificação Slack webhook: {e}")
        return False


def _notify_telegram(text: str, bot_token: str, chat_id: str) -> bool:
    """Envia notificação para o Telegram via Bot API."""
    try:
        url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
        payload = {
            "chat_id": chat_id,
            "text": text,
            "parse_mode": "Markdown",
            "disable_web_page_preview": True,
        }
        r = requests.post(url, json=payload, timeout=15)
        r.raise_for_status()
        logger.info("Notificação Telegram enviada com sucesso")
        return True
    except Exception as e:
        logger.error(f"Falha ao enviar notificação Telegram: {e}")
        return False


# ── Orquestrador ────────────────────────────────────────────────────

def notify(result: IngestionResult) -> dict[str, bool]:
    """Envia notificação para todos os canais configurados.

    Ordem de preferência Slack:
      1. OAuth (SLACK_BOT_TOKEN + SLACK_CHANNEL)
      2. Webhook (SLACK_WEBHOOK_URL)

    Returns:
        dict com resultados por canal: {"slack": True, "telegram": False, ...}
    """
    resultados: dict[str, bool] = {}

    text = _build_message_text(result)

    # Sempre loga no console
    logger.info("=== NOTIFICAÇÃO ===")
    for line in text.split("\n"):
        if line.strip():
            logger.info(line)
    logger.info("=== FIM NOTIFICAÇÃO ===")

    # ── Slack ──────────────────────────────────────────────────────
    slack_token = os.environ.get("SLACK_BOT_TOKEN")
    slack_channel = os.environ.get("SLACK_CHANNEL")
    slack_webhook = os.environ.get("SLACK_WEBHOOK_URL")

    if slack_token and slack_channel:
        resultados["slack"] = _notify_slack_oauth(text, slack_token, slack_channel, result)
    elif slack_webhook:
        resultados["slack"] = _notify_slack_webhook(text, slack_webhook)
    else:
        logger.info(
            "Canal Slack não configurado. "
            "Defina SLACK_BOT_TOKEN+SLACK_CHANNEL (OAuth) ou SLACK_WEBHOOK_URL"
        )

    # ── Telegram ───────────────────────────────────────────────────
    bot_token = os.environ.get("TELEGRAM_BOT_TOKEN")
    chat_id = os.environ.get("TELEGRAM_CHAT_ID")
    if bot_token and chat_id:
        resultados["telegram"] = _notify_telegram(text, bot_token, chat_id)
    else:
        logger.info("Canal Telegram não configurado (TELEGRAM_BOT_TOKEN/CHAT_ID vazio)")

    return resultados
