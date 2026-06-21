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


def format_trade(trade: dict, signal: dict, summary: dict, live: bool) -> str:
    """체결 알림 (단계 18). 페이퍼 체결은 수수료·손익·TOTAL 포함."""
    mode = "실거래" if live else "페이퍼"
    emoji = "🟢" if trade.get("side") == "BUY" else "🔴"
    lines = [
        f"{emoji} *[{mode}] {trade.get('side')}* `{trade.get('ticker')}`",
        f"레짐: {signal['regime']} / 전략: {signal['strategy']}",
    ]
    if "price" in trade:  # 페이퍼 체결 상세
        lines += [
            f"체결가: {trade['price']:,.0f}  수량: {trade['qty']}",
            f"거래금액: {trade['amount']:,.0f}  수수료: {trade['fee']:,.0f}",
            f"건별 손익: {trade['pnl']:,.0f}  누적: {trade['cum_pnl']:,.0f}",
        ]
    lines += [
        "─────────────",
        f"TOTAL: {summary['total_value']:,.0f} KRW ({summary['total_return_pct']:+.2f}%)",
        f"현금: {summary['cash']:,.0f}  평가: {summary['holdings_value']:,.0f}",
    ]
    return "\n".join(lines)


def format_spike(ticker: str, spike: dict, signal: dict) -> str:
    """큰 변동 감지 알림 (단계 14, 매매 없을 때)."""
    return (
        f"⚡ *큰 변동 감지* `{ticker}`\n"
        f"{spike['reason']}\n"
        f"현재가: {spike['price']:,.0f}\n"
        f"레짐: {signal['regime']} / 전략: {signal['strategy']} / 액션: {signal['action']}"
    )
