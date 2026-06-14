"""
Notification helpers for Discord and Telegram.
Credentials are loaded from .env via config.py.
"""

import requests

from config import DiscordConfig, TelegramConfig


def send_discord(message: str) -> bool:
    url = DiscordConfig.webhook_url
    if not url:
        print("[notify] DISCORD_WEBHOOK_URL not set — skipping")
        return False
    resp = requests.post(url, json={"content": message}, timeout=10)
    return resp.status_code == 204


def send_telegram(message: str) -> bool:
    token = TelegramConfig.bot_token
    chat_id = TelegramConfig.chat_id
    if not token or not chat_id:
        print("[notify] TELEGRAM_BOT_TOKEN or TELEGRAM_CHAT_ID not set — skipping")
        return False
    url = f"https://api.telegram.org/bot{token}/sendMessage"
    resp = requests.post(url, json={"chat_id": chat_id, "text": message, "parse_mode": "Markdown"}, timeout=10)
    return resp.ok


def send(message: str) -> None:
    send_discord(message)
    send_telegram(message)


def format_signals(signals: list[dict]) -> str:
    lines = ["**Daily Trading Signals**"]
    for s in signals:
        emoji = "🟢" if s["signal"] == "BUY" else "🔴"
        lines.append(f"{emoji} `{s['ticker']}` {s['signal']}  close={s['close']:.2f}")
    return "\n".join(lines)
