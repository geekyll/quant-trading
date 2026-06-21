"""
안전장치 (단계 20).

실거래 전·후로 폭주를 막는 가드. executor가 체결 직전에 확인한다.
  - Kill switch: data/paper/KILL 파일 존재 또는 TRADING_HALT=true → 모든 매매 차단
  - 일일 최대 주문 수 초과 → 신규 매매 차단
  - 일일 손실 한도(누적 손익이 -한도 이하) → 신규 매수 차단 (매도/청산은 허용)

Run:  uv run python -m broker.safety
"""

from __future__ import annotations

import os
from datetime import date
from pathlib import Path

from paper.portfolio import PaperPortfolio

KILL_FILE = Path(__file__).parent.parent / "data" / "paper" / "KILL"
MAX_ORDERS_PER_DAY = 10
DAILY_LOSS_LIMIT = 500_000.0  # 당일 누적 손실이 이 금액(KRW)을 넘으면 신규 매수 차단


class SafetyGuard:
    def __init__(
        self,
        max_orders_per_day: int = MAX_ORDERS_PER_DAY,
        daily_loss_limit: float = DAILY_LOSS_LIMIT,
    ) -> None:
        self.max_orders = max_orders_per_day
        self.loss_limit = daily_loss_limit

    def _today_trades(self):
        trades = PaperPortfolio.load_trades()
        if trades.empty:
            return trades
        return trades[trades["timestamp"].str.startswith(date.today().isoformat())]

    def can_trade(self, side: str) -> tuple[bool, str]:
        if KILL_FILE.exists() or os.environ.get("TRADING_HALT", "").lower() == "true":
            return False, "kill switch 작동 중 — 모든 매매 차단"

        today = self._today_trades()
        if len(today) >= self.max_orders:
            return False, f"일일 최대 주문 수({self.max_orders}) 초과"

        if side == "BUY" and not today.empty:
            today_pnl = float(today["pnl"].sum())
            if today_pnl <= -self.loss_limit:
                return False, f"일일 손실 한도(-{self.loss_limit:,.0f}) 도달 — 신규 매수 차단"

        return True, "ok"


if __name__ == "__main__":
    guard = SafetyGuard()
    for side in ("BUY", "SELL"):
        ok, reason = guard.can_trade(side)
        print(f"{side}: {ok} ({reason})")
    print(f"kill file: {KILL_FILE} (exists={KILL_FILE.exists()})")
