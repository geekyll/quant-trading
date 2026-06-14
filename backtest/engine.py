from pathlib import Path

import matplotlib.pyplot as plt
import pandas as pd

from backtest.metrics import summary
from strategy.ma import add_sma

REPORT_DIR = Path(__file__).parent.parent / "report"
REPORT_DIR.mkdir(exist_ok=True)


def run(df: pd.DataFrame, sma_period: int = 200) -> dict:
    df = add_sma(df, periods=[sma_period])
    col = f"SMA{sma_period}"

    # signal: 1 = invested, 0 = cash
    # shift(1) to avoid lookahead bias — trade on next day's open
    signal = (df["Close"] > df[col]).astype(int).shift(1).fillna(0)

    daily_ret = df["Close"].pct_change().fillna(0)
    strat_ret = signal * daily_ret
    bnh_ret = daily_ret

    strat_equity = (1 + strat_ret).cumprod()
    bnh_equity = (1 + bnh_ret).cumprod()

    return {
        "df": df,
        "signal": signal,
        "strat_equity": strat_equity,
        "strat_returns": strat_ret,
        "bnh_equity": bnh_equity,
        "bnh_returns": bnh_ret,
        "strategy": summary(strat_equity, strat_ret),
        "buy_and_hold": summary(bnh_equity, bnh_ret),
    }


def plot(result: dict, ticker: str, sma_period: int = 200) -> None:
    fig, axes = plt.subplots(2, 1, figsize=(16, 10), gridspec_kw={"height_ratios": [2, 1]})

    # top: equity curves
    ax = axes[0]
    ax.plot(result["strat_equity"].index, result["strat_equity"], label=f"SMA{sma_period} Strategy", color="#1f77b4")
    ax.plot(result["bnh_equity"].index, result["bnh_equity"], label="Buy & Hold", color="#ff7f0e", alpha=0.7)
    ax.set_title(f"{ticker} — SMA{sma_period} Strategy vs Buy & Hold")
    ax.set_ylabel("Growth of $1")
    ax.legend()
    ax.grid(alpha=0.3)

    # bottom: invested vs cash periods
    ax2 = axes[1]
    ax2.fill_between(result["signal"].index, result["signal"], alpha=0.4, color="#1f77b4", label="Invested")
    ax2.set_ylabel("Position")
    ax2.set_xlabel("Date")
    ax2.set_ylim(-0.1, 1.1)
    ax2.legend()
    ax2.grid(alpha=0.3)

    fig.tight_layout()
    path = REPORT_DIR / f"{ticker.lower().replace('-', '_')}_backtest.png"
    fig.savefig(path, dpi=150)
    plt.close(fig)
    print(f"  Chart saved: {path}")


def print_report(ticker: str, result: dict, sma_period: int = 200) -> None:
    s = result["strategy"]
    b = result["buy_and_hold"]
    print(f"\n{'=' * 50}")
    print(f"  {ticker}  |  SMA{sma_period} Strategy vs Buy & Hold")
    print(f"{'=' * 50}")
    print(f"  {'Metric':<18} {'Strategy':>12} {'Buy & Hold':>12}")
    print(f"  {'-' * 44}")
    print(f"  {'Total Return (%)':<18} {s['total_return']:>11.2f}% {b['total_return']:>11.2f}%")
    print(f"  {'CAGR (%)':<18} {s['cagr']:>11.2f}% {b['cagr']:>11.2f}%")
    print(f"  {'MDD (%)':<18} {s['mdd']:>11.2f}% {b['mdd']:>11.2f}%")
    print(f"  {'Sharpe Ratio':<18} {s['sharpe']:>12.3f} {b['sharpe']:>12.3f}")
    print(f"{'=' * 50}")


if __name__ == "__main__":
    from data.collector import load
    from data.universe import TICKERS

    for ticker in TICKERS:
        print(f"\n[{ticker}] Running backtest...")
        df = load(ticker)
        result = run(df)
        print_report(ticker, result)
        plot(result, ticker)
