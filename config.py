import os
from pathlib import Path

from dotenv import load_dotenv

load_dotenv(Path(__file__).parent / ".env")


class KISConfig:
    app_key: str = os.environ.get("APP_KEY", "")
    app_secret: str = os.environ.get("APP_SECRET", "")
    account_no: str = os.environ.get("ACCOUNT_NO", "")
    use_mock: bool = os.environ.get("USE_MOCK", "true").lower() == "true"


class UpbitConfig:
    access_key: str = os.environ.get("UPBIT_ACCESS_KEY", "")
    secret_key: str = os.environ.get("UPBIT_SECRET_KEY", "")
    # 실거래 토글. 기본 false → 페이퍼(가상) 모드. true 일 때만 실주문.
    live: bool = os.environ.get("UPBIT_LIVE", "false").lower() == "true"


class DiscordConfig:
    webhook_url: str = os.environ.get("DISCORD_WEBHOOK_URL", "")


class TelegramConfig:
    bot_token: str = os.environ.get("TELEGRAM_BOT_TOKEN", "")
    chat_id: str = os.environ.get("TELEGRAM_CHAT_ID", "")
