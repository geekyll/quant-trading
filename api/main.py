from fastapi import FastAPI

from backtest.engine import run as backtest_run
from backtest.paper_trade import _load_portfolio, get_portfolio_value, load_trades
from data.collector import load
from data.universe import UNIVERSE
from strategy.signals import current_signals

app = FastAPI(title="Quant Trading API", version="0.1.0")


@app.get("/health")
def health() -> dict:
    return {"status": "ok"}


@app.get("/signals")
def signals(sma_period: int = 200) -> list[dict]:
    return current_signals(sma_period)


@app.get("/portfolio")
def portfolio() -> dict:
    p = _load_portfolio()
    return {
        "cash": round(p["cash"], 2),
        "positions": p["positions"],
        "total_value": round(get_portfolio_value(p), 2),
    }


@app.get("/trades")
def trades() -> list[dict]:
    df = load_trades()
    if df.empty:
        return []
    return df.to_dict(orient="records")


@app.get("/performance/{ticker}")
def performance(ticker: str, sma_period: int = 200) -> dict:
    df = load(ticker)
    result = backtest_run(df, sma_period)
    return {
        "ticker": ticker,
        "sma_period": sma_period,
        "strategy": result["strategy"],
        "buy_and_hold": result["buy_and_hold"],
    }


@app.get("/universe")
def universe() -> list[dict]:
    return [{"ticker": a.ticker, "name": a.name, "start": a.start} for a in UNIVERSE]
