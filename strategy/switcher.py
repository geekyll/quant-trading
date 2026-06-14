"""
Regime-Adaptive Strategy Switcher for BTC.

Regime   → Strategy
-------    ---------
BULL        Volatility Breakout (k=0.5)
SIDEWAYS_UP Grid / Mean-Reversion
BEAR        Cash (no position)
SIDEWAYS_DOWN Cash (no position)
"""

from pathlib import Path

import matplotlib.patches as mpatches
import matplotlib.pyplot as plt
import pandas as pd

from backtest.metrics import summary
from strategy.grid import signal as grid_signal
from strategy.regime import Regime, detect
from strategy.volatility_breakout import signal as vb_signal

REPORT_DIR = Path(__file__).parent.parent / "report"
REGIME_COLORS = {
    Regime.BULL: "#2ca02c",
    Regime.SIDEWAYS_UP: "#1f77b4",
    Regime.BEAR: "#d62728",
    Regime.SIDEWAYS_DOWN: "#ff7f0e",
    None: "#cccccc",
}


def run(
    df: pd.DataFrame,
    k: float = 0.5,
    adx_bull: float = 25,
    adx_side: float = 20,
    grid_window: int = 20,
    grid_std: float = 1.5,
) -> dict:
    regime = detect(df, adx_bull=adx_bull, adx_side=adx_side)
    daily_ret = df["Close"].pct_change().fillna(0)

    vb_ret = vb_signal(df, k=k)
    grid_pos = grid_signal(df, window=grid_window, std_mult=grid_std)
    grid_ret = grid_pos * daily_ret

    # combine: pick return based on regime each day
    combined_ret = pd.Series(0.0, index=df.index)
    active_strategy = pd.Series("CASH", index=df.index, dtype=str)

    for i in range(len(df)):
        r = regime.iloc[i]
        if r == Regime.BULL:
            combined_ret.iloc[i] = vb_ret.iloc[i]
            active_strategy.iloc[i] = "VB"
        elif r == Regime.SIDEWAYS_UP:
            combined_ret.iloc[i] = grid_ret.iloc[i]
            active_strategy.iloc[i] = "GRID"
        else:
            combined_ret.iloc[i] = 0.0
            active_strategy.iloc[i] = "CASH"

    equity = (1 + combined_ret).cumprod()
    bnh_equity = (1 + daily_ret).cumprod()

    return {
        "regime": regime,
        "active_strategy": active_strategy,
        "returns": combined_ret,
        "equity": equity,
        "bnh_equity": bnh_equity,
        "metrics": summary(equity, combined_ret),
        "bnh_metrics": summary(bnh_equity, daily_ret),
    }


def plot(result: dict, ticker: str = "BTC-USD") -> None:
    fig, axes = plt.subplots(3, 1, figsize=(16, 12), gridspec_kw={"height_ratios": [3, 1, 1]})

    # --- equity curve ---
    ax = axes[0]
    ax.plot(result["equity"].index, result["equity"], label="Adaptive Strategy", color="#1f77b4", linewidth=1.5)
    ax.plot(result["bnh_equity"].index, result["bnh_equity"], label="Buy & Hold", color="black", alpha=0.4, linewidth=1)
    ax.set_title(f"{ticker} — Regime-Adaptive Strategy vs Buy & Hold")
    ax.set_ylabel("Growth of $1")
    ax.legend()
    ax.grid(alpha=0.3)

    # --- regime background on equity ---
    regime = result["regime"]
    prev_r, start = None, regime.index[0]
    for i, (date, r) in enumerate(regime.items()):
        if r != prev_r or i == len(regime) - 1:
            if prev_r is not None:
                ax.axvspan(start, date, alpha=0.08, color=REGIME_COLORS.get(prev_r, "#ccc"))
            start = date
            prev_r = r

    # --- active strategy bar ---
    ax2 = axes[1]
    strategy_map = {"VB": 1.0, "GRID": 0.5, "CASH": 0.0}
    strategy_vals = result["active_strategy"].map(strategy_map)
    colors = result["active_strategy"].map({"VB": "#2ca02c", "GRID": "#1f77b4", "CASH": "#d62728"})
    ax2.bar(strategy_vals.index, strategy_vals, color=colors, width=1.0)
    ax2.set_ylabel("Strategy")
    ax2.set_yticks([0, 0.5, 1.0])
    ax2.set_yticklabels(["CASH", "GRID", "VB"])
    ax2.grid(alpha=0.3)

    patches = [
        mpatches.Patch(color="#2ca02c", label="Volatility Breakout (BULL)"),
        mpatches.Patch(color="#1f77b4", label="Grid/MeanRev (SIDEWAYS)"),
        mpatches.Patch(color="#d62728", label="Cash (BEAR)"),
    ]
    ax2.legend(handles=patches, loc="upper left", fontsize=8)

    # --- regime distribution ---
    ax3 = axes[2]
    regime_counts = result["regime"].value_counts()
    regime_counts.index = [str(r) for r in regime_counts.index]
    bar_colors = [REGIME_COLORS.get(Regime(r.split(".")[-1]) if "." in r else r, "#ccc") for r in regime_counts.index]
    ax3.bar(regime_counts.index, regime_counts.values, color=bar_colors)
    ax3.set_ylabel("Days")
    ax3.set_title("Regime Distribution")
    ax3.grid(alpha=0.3)

    fig.tight_layout()
    path = REPORT_DIR / f"{ticker.lower().replace('-', '_')}_adaptive.png"
    fig.savefig(path, dpi=150)
    plt.close(fig)
    print(f"Chart saved: {path}")


def print_report(result: dict, ticker: str = "BTC-USD") -> None:
    m = result["metrics"]
    b = result["bnh_metrics"]
    strat_days = result["active_strategy"].value_counts().to_dict()

    print(f"\n{'=' * 54}")
    print(f"  {ticker}  —  Regime-Adaptive Strategy")
    print(f"{'=' * 54}")
    print(f"  {'Metric':<18} {'Adaptive':>12} {'Buy & Hold':>12}")
    print(f"  {'-' * 50}")
    print(f"  {'Total Return (%)':<18} {m['total_return']:>11.2f}% {b['total_return']:>11.2f}%")
    print(f"  {'CAGR (%)':<18} {m['cagr']:>11.2f}% {b['cagr']:>11.2f}%")
    print(f"  {'MDD (%)':<18} {m['mdd']:>11.2f}% {b['mdd']:>11.2f}%")
    print(f"  {'Sharpe Ratio':<18} {m['sharpe']:>12.3f} {b['sharpe']:>12.3f}")
    print(f"{'=' * 54}")
    print("  Strategy allocation:")
    total = sum(strat_days.values())
    for s, n in sorted(strat_days.items()):
        print(f"    {s:<6}  {n:>4} days  ({n / total * 100:.1f}%)")
    print(f"{'=' * 54}")


if __name__ == "__main__":
    from data.collector import load

    df = load("BTC-USD")
    print("Running regime detection...")
    result = run(df)
    print_report(result)
    plot(result)
