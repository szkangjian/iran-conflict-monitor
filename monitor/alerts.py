import logging
import requests
from config import TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID
from monitor.storage import get_unalerted_events, mark_alerted

logger = logging.getLogger(__name__)

SEVERITY_EMOJI = {
    "critical": "🚨",
    "high": "⚠️",
    "medium": "📌",
    "low": "ℹ️",
}


def _send_telegram(text: str):
    if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID:
        return
    try:
        resp = requests.post(
            f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage",
            json={"chat_id": TELEGRAM_CHAT_ID, "text": text, "parse_mode": "HTML"},
            timeout=10,
        )
        resp.raise_for_status()
    except Exception as exc:
        logger.error("Telegram alert failed: %s", exc)


def send_pending_alerts():
    events = get_unalerted_events()
    if not events:
        return
    for ev in events:
        emoji = SEVERITY_EMOJI.get(ev["severity"], "")
        tags = f"\n<i>Tags: {ev['tags']}</i>" if ev.get("tags") else ""
        msg = (
            f"{emoji} <b>[{ev['severity'].upper()}] {ev['title']}</b>\n"
            f"Source: {ev['source']}\n"
            f"{ev.get('url', '')}"
            f"{tags}"
        )
        _send_telegram(msg)
        mark_alerted(ev["id"])
        logger.info("Alert sent for event %d: %s", ev["id"], ev["title"][:60])
