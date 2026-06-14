"""
Paper trading simulator.
Reads current signals, updates virtual portfolio, and logs every trade.
State is persisted in data/paper_portfolio.json and data/paper_trades.csv.
"""

import json
from datetime import date
from pathlib import Path

import pandas as pd

from data.collector import load
from strategy.signals import current_signals

DATA_DIR = Path(__file__).parent.parent / "data"
PORTFOLIO_FILE = DATA_DIR / "paper_portfolio.json"
TRADES_FILE = DATA_DIR / "paper_trades.csv"
INITIAL_CASH = 100_000.0


def _load_portfolio() -> dict:
    if PORTFOLIO_FILE.exists():
        return json.loads(PORTFOLIO_FILE.read_text())
    return {"cash": INITIAL_CASH, "positions": {}}


def _save_portfolio(portfolio: dict) -> None:
    PORTFOLIO_FILE.write_text(json.dumps(portfolio, indent=2))


def _append_trade(row: dict) -> None:
    df = pd.DataFrame([row])
    df.to_csv(TRADES_FILE, mode="a", header=not TRADES_FILE.exists(), index=False)


def get_portfolio_value(portfolio: dict) -> float:
    total = portfolio["cash"]
    for ticker, pos in portfolio["positions"].items():
        df = load(ticker)
        price = float(df["Close"].iloc[-1])
        total += pos["qty"] * price
    return total


def run_once(dry_run: bool = False) -> list[dict]:
    portfolio = _load_portfolio()
    signals = current_signals()
    today = date.today().isoformat()
    executed = []

    for s in signals:
        ticker = s["ticker"]
        price = s["close"]
        signal = s["signal"]
        position = portfolio["positions"].get(ticker)

        if signal == "BUY" and position is None:
            qty = int((portfolio["cash"] / len(signals)) / price)
            if qty < 1:
                continue
            cost = qty * price
            if not dry_run:
                portfolio["cash"] -= cost
                portfolio["positions"][ticker] = {"qty": qty, "avg_price": price}
                _append_trade(
                    {"date": today, "ticker": ticker, "side": "BUY", "qty": qty, "price": price, "total": cost}
                )
            executed.append({"ticker": ticker, "side": "BUY", "qty": qty, "price": price})

        elif signal == "SELL" and position is not None:
            qty = position["qty"]
            proceeds = qty * price
            if not dry_run:
                portfolio["cash"] += proceeds
                del portfolio["positions"][ticker]
                _append_trade(
                    {"date": today, "ticker": ticker, "side": "SELL", "qty": qty, "price": price, "total": proceeds}
                )
            executed.append({"ticker": ticker, "side": "SELL", "qty": qty, "price": price})

    if not dry_run:
        _save_portfolio(portfolio)

    portfolio_value = get_portfolio_value(portfolio)
    print(f"Portfolio value: ${portfolio_value:,.2f}  (cash: ${portfolio['cash']:,.2f})")
    for ex in executed:
        print(f"  {ex['side']:4s}  {ex['ticker']:8s}  qty={ex['qty']}  @${ex['price']:.2f}")

    return executed


def load_trades() -> pd.DataFrame:
    if not TRADES_FILE.exists():
        return pd.DataFrame()
    return pd.read_csv(TRADES_FILE, parse_dates=["date"])


if __name__ == "__main__":
    print("=== Paper Trade ===")
    run_once()
