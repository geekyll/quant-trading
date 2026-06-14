"""
Upbit Open API client for cryptocurrency trading.
Credentials are loaded from .env via config.py.

API docs: https://docs.upbit.com
"""

import pyupbit

from config import UpbitConfig


class UpbitClient:
    def __init__(self) -> None:
        self.upbit = pyupbit.Upbit(UpbitConfig.access_key, UpbitConfig.secret_key)

    # ------------------------------------------------------------------
    # Account
    # ------------------------------------------------------------------

    def get_balance(self, ticker: str = "KRW") -> float:
        return self.upbit.get_balance(ticker)

    def get_balances(self) -> list[dict]:
        return self.upbit.get_balances()

    # ------------------------------------------------------------------
    # Market
    # ------------------------------------------------------------------

    def get_current_price(self, market: str = "KRW-BTC") -> float:
        return pyupbit.get_current_price(market)

    def get_ohlcv(self, market: str = "KRW-BTC", interval: str = "day", count: int = 200):
        return pyupbit.get_ohlcv(market, interval=interval, count=count)

    # ------------------------------------------------------------------
    # Orders
    # ------------------------------------------------------------------

    def buy_market(self, market: str, amount_krw: float) -> dict:
        return self.upbit.buy_market_order(market, amount_krw)

    def sell_market(self, market: str, volume: float) -> dict:
        return self.upbit.sell_market_order(market, volume)


if __name__ == "__main__":
    client = UpbitClient()
    krw = client.get_balance("KRW")
    btc = client.get_balance("BTC")
    price = client.get_current_price("KRW-BTC")
    print(f"KRW balance : {krw:,.0f} KRW")
    print(f"BTC balance : {btc:.8f} BTC")
    print(f"BTC price   : {price:,.0f} KRW")
