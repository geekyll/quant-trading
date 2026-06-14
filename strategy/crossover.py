from pathlib import Path

import matplotlib.pyplot as plt
import pandas as pd

from backtest.metrics import summary
from strategy.ma import add_sma

REPORT_DIR = Path(__file__).parent.parent / "report"

PAIRS = [
    (50, 200),
    (20, 100),
    (100, 200),
]


def run(df: pd.DataFrame, fast: int, slow: int) -> dict:
    df = add_sma(df, periods=[fast, slow])
    fast_col, slow_col = f"SMA{fast}", f"SMA{slow}"

    signal = (df[fast_col] > df[slow_col]).astype(int).shift(1).fillna(0)
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
        "strategy": summary(strat_equity, strat_ret),
        "buy_and_hold": summary(bnh_equity, bnh_ret),
        "label": f"SMA{fast}/SMA{slow}",
    }


def compare_all(df: pd.DataFrame, ticker: str) -> list[dict]:
    results = []
    for fast, slow in PAIRS:
        r = run(df, fast, slow)
        r["pair"] = (fast, slow)
        results.append(r)
    return results


def plot_comparison(results: list[dict], ticker: str) -> None:
    fig, ax = plt.subplots(figsize=(16, 6))
    colors = ["#1f77b4", "#ff7f0e", "#2ca02c"]
    for i, r in enumerate(results):
        ax.plot(r["strat_equity"].index, r["strat_equity"], label=r["label"], color=colors[i])
    ax.plot(
        results[0]["bnh_equity"].index,
        results[0]["bnh_equity"],
        label="Buy & Hold",
        color="black",
        alpha=0.4,
        linestyle="--",
    )
    ax.set_title(f"{ticker} — Crossover Strategy Comparison")
    ax.set_ylabel("Growth of $1")
    ax.legend()
    ax.grid(alpha=0.3)
    fig.tight_layout()
    path = REPORT_DIR / f"{ticker.lower().replace('-', '_')}_crossover.png"
    fig.savefig(path, dpi=150)
    plt.close(fig)
    print(f"  Chart saved: {path}")


def print_comparison(results: list[dict], ticker: str) -> None:
    b = results[0]["buy_and_hold"]
    print(f"\n{'=' * 62}")
    print(f"  {ticker}  —  Crossover Strategy Comparison")
    print(f"{'=' * 62}")
    print(f"  {'Strategy':<16} {'CAGR':>8} {'MDD':>8} {'Sharpe':>8} {'Total':>10}")
    print(f"  {'-' * 58}")
    for r in results:
        s = r["strategy"]
        print(f"  {r['label']:<16} {s['cagr']:>7.2f}% {s['mdd']:>7.2f}% {s['sharpe']:>8.3f} {s['total_return']:>9.2f}%")
    print(f"  {'Buy & Hold':<16} {b['cagr']:>7.2f}% {b['mdd']:>7.2f}% {b['sharpe']:>8.3f} {b['total_return']:>9.2f}%")
    print(f"{'=' * 62}")


if __name__ == "__main__":
    from data.collector import load
    from data.universe import TICKERS

    for ticker in TICKERS:
        print(f"\n[{ticker}] Running crossover comparison...")
        df = load(ticker)
        results = compare_all(df, ticker)
        print_comparison(results, ticker)
        plot_comparison(results, ticker)
