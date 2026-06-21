"""
Paper Portfolio — 실거래 전 검증용 가상 포트폴리오 (단계 15).

요구사항:
  - 착수금 1,000만원(KRW)
  - 자산을 BTC / NYSE 두 그룹으로 분류해 관리
  - 조건 충족으로 매매 발생 시 그 시점(timestamp)으로 전체 거래내역 저장
    (일시, 분류, 티커, 방향, 수량, 체결가, 거래금액, 예상 수수료, 건별 손익, 누적 손익)
  - TOTAL 집계: 현금 + 평가액, 분류별/전체 손익, 누적 수익률
  - 거래내역 최대 100개 조회, 초과 시 페이지네이션

상태 저장:
  data/paper/portfolio.json  — 현금/포지션/실현손익
  data/paper/trades.csv      — 전체 거래내역 (append)

Run (데모):  uv run python -m paper.portfolio
"""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path

import pandas as pd

DATA_DIR = Path(__file__).parent.parent / "data" / "paper"
DATA_DIR.mkdir(parents=True, exist_ok=True)
PORTFOLIO_FILE = DATA_DIR / "portfolio.json"
TRADES_FILE = DATA_DIR / "trades.csv"

INITIAL_CASH = 10_000_000.0  # 착수금 1,000만원 (KRW)

# 분류별 예상 수수료율 (시장가 기준)
FEE_RATES = {
    "BTC": 0.0005,   # Upbit 0.05%
    "NYSE": 0.0025,  # KIS 해외주식 약 0.25%
}

# 티커 → 분류 매핑
CATEGORY_MAP = {
    "BTC-USD": "BTC",
    "KRW-BTC": "BTC",
    "BTC": "BTC",
    "QQQ": "NYSE",
    "SOXL": "NYSE",
    "SOXS": "NYSE",
}

TRADE_COLUMNS = [
    "timestamp", "category", "ticker", "side",
    "qty", "price", "amount", "fee", "pnl", "cum_pnl",
]


def categorize(ticker: str) -> str:
    return CATEGORY_MAP.get(ticker, "NYSE")


def fee_rate(category: str) -> float:
    return FEE_RATES.get(category, 0.0005)


class PaperPortfolio:
    def __init__(self) -> None:
        self.state = self._load()

    # ------------------------------------------------------------------
    # persistence
    # ------------------------------------------------------------------
    def _load(self) -> dict:
        if PORTFOLIO_FILE.exists():
            return json.loads(PORTFOLIO_FILE.read_text())
        return {
            "initial_cash": INITIAL_CASH,
            "cash": INITIAL_CASH,
            "positions": {},          # ticker -> {qty, avg_price, category}
            "cum_pnl": 0.0,            # 누적 순실현손익 (매수/매도 수수료 모두 반영)
        }

    def save(self) -> None:
        PORTFOLIO_FILE.write_text(json.dumps(self.state, indent=2, ensure_ascii=False))

    def _append_trade(self, row: dict) -> None:
        df = pd.DataFrame([row], columns=TRADE_COLUMNS)
        df.to_csv(TRADES_FILE, mode="a", header=not TRADES_FILE.exists(), index=False)

    # ------------------------------------------------------------------
    # trading
    # ------------------------------------------------------------------
    def buy(self, ticker: str, price: float, amount_krw: float, timestamp: str | None = None) -> dict | None:
        """amount_krw(수수료 포함) 만큼 매수. 체결 거래내역을 반환."""
        category = categorize(ticker)
        rate = fee_rate(category)
        if amount_krw <= 0 or amount_krw > self.state["cash"]:
            amount_krw = min(amount_krw, self.state["cash"])
        cost = amount_krw / (1 + rate)   # 순매수금액
        fee = amount_krw - cost
        qty = cost / price
        if qty <= 0:
            return None

        self.state["cash"] -= amount_krw
        pos = self.state["positions"].get(ticker)
        if pos:
            total_qty = pos["qty"] + qty
            pos["avg_price"] = (pos["avg_price"] * pos["qty"] + price * qty) / total_qty
            pos["qty"] = total_qty
        else:
            self.state["positions"][ticker] = {"qty": qty, "avg_price": price, "category": category}

        return self._finalize(timestamp, category, ticker, "BUY", qty, price, cost, fee, pnl=-fee)

    def sell(self, ticker: str, price: float, qty: float | None = None, timestamp: str | None = None) -> dict | None:
        """보유 수량(기본 전량) 매도. 건별 실현손익 = (체결가-평단)*수량 - 수수료."""
        pos = self.state["positions"].get(ticker)
        if not pos:
            return None
        category = pos["category"]
        rate = fee_rate(category)
        sell_qty = pos["qty"] if qty is None else min(qty, pos["qty"])
        if sell_qty <= 0:
            return None

        proceeds = price * sell_qty
        fee = proceeds * rate
        pnl = (price - pos["avg_price"]) * sell_qty - fee

        self.state["cash"] += proceeds - fee
        pos["qty"] -= sell_qty
        if pos["qty"] <= 1e-12:
            del self.state["positions"][ticker]

        return self._finalize(timestamp, category, ticker, "SELL", sell_qty, price, proceeds, fee, pnl=pnl)

    def _finalize(self, timestamp, category, ticker, side, qty, price, amount, fee, pnl) -> dict:
        self.state["cum_pnl"] += pnl
        row = {
            "timestamp": timestamp or datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "category": category,
            "ticker": ticker,
            "side": side,
            "qty": round(qty, 8),
            "price": round(price, 4),
            "amount": round(amount, 2),
            "fee": round(fee, 2),
            "pnl": round(pnl, 2),
            "cum_pnl": round(self.state["cum_pnl"], 2),
        }
        self._append_trade(row)
        self.save()
        return row

    # ------------------------------------------------------------------
    # valuation / summary
    # ------------------------------------------------------------------
    def summary(self, prices: dict[str, float]) -> dict:
        """prices: {ticker: 현재가}. 분류별/전체 TOTAL 집계."""
        cats: dict[str, dict] = {}
        holdings_value = 0.0
        for ticker, pos in self.state["positions"].items():
            cat = pos["category"]
            price = prices.get(ticker, pos["avg_price"])
            mkt = pos["qty"] * price
            unreal = (price - pos["avg_price"]) * pos["qty"]
            holdings_value += mkt
            c = cats.setdefault(cat, {"holdings_value": 0.0, "unrealized_pnl": 0.0})
            c["holdings_value"] += mkt
            c["unrealized_pnl"] += unreal

        total_value = self.state["cash"] + holdings_value
        initial = self.state["initial_cash"]
        return {
            "cash": round(self.state["cash"], 2),
            "holdings_value": round(holdings_value, 2),
            "total_value": round(total_value, 2),
            "realized_pnl": round(self.state["cum_pnl"], 2),
            "unrealized_pnl": round(sum(c["unrealized_pnl"] for c in cats.values()), 2),
            "total_return_pct": round((total_value / initial - 1) * 100, 2),
            "initial_cash": round(initial, 2),
            "by_category": {
                cat: {k: round(v, 2) for k, v in c.items()} for cat, c in cats.items()
            },
            "positions": self.state["positions"],
        }

    # ------------------------------------------------------------------
    # trade history (최대 100개, 초과 시 페이지네이션)
    # ------------------------------------------------------------------
    @staticmethod
    def load_trades() -> pd.DataFrame:
        if not TRADES_FILE.exists():
            return pd.DataFrame(columns=TRADE_COLUMNS)
        return pd.read_csv(TRADES_FILE)

    @classmethod
    def trades_page(cls, page: int = 1, page_size: int = 100) -> dict:
        """최신순 거래내역을 page_size(기본 100)씩 페이지네이션."""
        df = cls.load_trades()
        df = df.iloc[::-1].reset_index(drop=True)  # 최신순
        total = len(df)
        pages = max(1, (total + page_size - 1) // page_size)
        page = max(1, min(page, pages))
        start = (page - 1) * page_size
        chunk = df.iloc[start : start + page_size]
        return {
            "page": page,
            "page_size": page_size,
            "total_trades": total,
            "total_pages": pages,
            "trades": chunk.to_dict("records"),
        }


if __name__ == "__main__":
    # 데모: 새 포트폴리오로 매수 → 매도 시나리오
    pf = PaperPortfolio()
    print(f"착수금: {pf.state['cash']:,.0f} KRW")
    t1 = pf.buy("BTC-USD", price=96_000_000, amount_krw=3_000_000)
    print("BUY :", t1)
    t2 = pf.sell("BTC-USD", price=98_000_000)
    print("SELL:", t2)
    print("\n요약:")
    s = pf.summary({"BTC-USD": 98_000_000})
    for k, v in s.items():
        print(f"  {k}: {v}")
    print("\n거래내역(page 1):")
    page = pf.trades_page(page=1)
    print(f"  총 {page['total_trades']}건 / {page['total_pages']}페이지")
