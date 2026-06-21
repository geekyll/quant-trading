"""
주문 실행 계층 (단계 16).

live_signal 의 action(BUY/SELL/HOLD)을 받아 실제 체결로 연결한다.
paper 모드(기본): paper.portfolio.PaperPortfolio 가상 체결.
live 모드(UPBIT_LIVE=true): broker.upbit.UpbitClient 실주문.

포지션 추적으로 중복 매수·연속 매도를 방지한다 (in_position 으로 action 판정).

Run (데모, paper):  uv run python -m broker.executor
"""

from __future__ import annotations

from broker.safety import SafetyGuard
from config import UpbitConfig
from data.intraday import to_market
from paper.portfolio import PaperPortfolio, categorize

DEFAULT_ALLOCATION_KRW = 3_000_000.0  # 1회 매수 배분 금액


class TradeExecutor:
    def __init__(self, live: bool | None = None, allocation_krw: float = DEFAULT_ALLOCATION_KRW) -> None:
        self.live = UpbitConfig.live if live is None else live
        self.allocation_krw = allocation_krw
        self.pf = PaperPortfolio()
        self.guard = SafetyGuard()
        self.upbit = None
        if self.live:
            from broker.upbit import UpbitClient

            self.upbit = UpbitClient()

    # ------------------------------------------------------------------
    def in_position(self, ticker: str) -> bool:
        if self.live:
            coin = to_market(ticker).split("-")[-1]  # KRW-BTC -> BTC
            return self.upbit.get_balance(coin) > 0
        return ticker in self.pf.state["positions"]

    def buy(self, ticker: str, price: float) -> dict | None:
        if self.live:
            order = self.upbit.buy_market(to_market(ticker), self.allocation_krw)
            return {"mode": "live", "side": "BUY", "ticker": ticker, "order": order}
        return self.pf.buy(ticker, price=price, amount_krw=self.allocation_krw)

    def sell(self, ticker: str, price: float) -> dict | None:
        if self.live:
            coin = to_market(ticker).split("-")[-1]
            volume = self.upbit.get_balance(coin)
            if volume <= 0:
                return None
            order = self.upbit.sell_market(to_market(ticker), volume)
            return {"mode": "live", "side": "SELL", "ticker": ticker, "order": order}
        return self.pf.sell(ticker, price=price)

    def execute(self, signal: dict, ticker: str, price: float) -> dict | None:
        """live_signal 결과(action)에 따라 체결. 거래가 없으면 None."""
        action = signal["action"]
        if action == "HOLD":
            return None
        ok, reason = self.guard.can_trade(action)
        if not ok:
            print(f"  [safety] {action} 차단: {reason}")
            return None
        if action == "BUY":
            return self.buy(ticker, price)
        if action == "SELL":
            return self.sell(ticker, price)
        return None


if __name__ == "__main__":
    ex = TradeExecutor(live=False)
    cat = categorize("BTC-USD")
    print(f"mode={'LIVE' if ex.live else 'PAPER'}  category={cat}")
    print("in_position(BTC-USD):", ex.in_position("BTC-USD"))
