"""
Walk-Forward Analysis (WFA) for the regime-adaptive strategy.

Flow per fold:
  1. Optimize parameters on in-sample (train) period → best k, adx_bull
  2. Apply those parameters on out-of-sample (test) period
  3. Stitch OOS equity curves → realistic forward performance
"""

from itertools import product
from pathlib import Path

import matplotlib.pyplot as plt
import pandas as pd

from backtest.metrics import summary
from strategy.switcher import run as switcher_run

REPORT_DIR = Path(__file__).parent.parent / "report"

PARAM_GRID = {
    "k": [0.3, 0.4, 0.5, 0.6, 0.7],
    "adx_bull": [20, 25, 30],
}

SIMPLE_SPLIT_DATE = "2022-01-01"
TRAIN_YEARS = 3
TEST_YEARS = 1


# ------------------------------------------------------------------
# Optimization
# ------------------------------------------------------------------


def optimize(df: pd.DataFrame) -> dict:
    best_sharpe, best_params = -999.0, {}
    for k, adx_bull in product(PARAM_GRID["k"], PARAM_GRID["adx_bull"]):
        try:
            r = switcher_run(df, k=k, adx_bull=adx_bull)
            s = r["metrics"]["sharpe"]
            if s > best_sharpe:
                best_sharpe = s
                best_params = {"k": k, "adx_bull": adx_bull}
        except Exception:
            continue
    return best_params


# ------------------------------------------------------------------
# Simple split
# ------------------------------------------------------------------


def simple_split(df: pd.DataFrame, split_date: str = SIMPLE_SPLIT_DATE) -> dict:
    train = df[df.index < split_date]
    test = df[df.index >= split_date]

    print(f"  Train : {train.index[0].date()} ~ {train.index[-1].date()}  ({len(train)} days)")
    print(f"  Test  : {test.index[0].date()}  ~ {test.index[-1].date()}   ({len(test)} days)")

    print("  Optimizing on train set...")
    best = optimize(train)
    print(f"  Best params → k={best['k']}  adx_bull={best['adx_bull']}")

    train_result = switcher_run(train, **best)
    test_result = switcher_run(test, **best)
    bnh_train = summary((1 + train["Close"].pct_change().fillna(0)).cumprod(), train["Close"].pct_change().fillna(0))
    bnh_test = summary((1 + test["Close"].pct_change().fillna(0)).cumprod(), test["Close"].pct_change().fillna(0))

    return {
        "best_params": best,
        "train": train_result,
        "test": test_result,
        "bnh_train": bnh_train,
        "bnh_test": bnh_test,
        "split_date": split_date,
    }


# ------------------------------------------------------------------
# Walk-Forward
# ------------------------------------------------------------------


def walk_forward(
    df: pd.DataFrame,
    train_years: int = TRAIN_YEARS,
    test_years: int = TEST_YEARS,
) -> list[dict]:
    folds = []
    train_start = df.index[0]

    while True:
        train_end = train_start + pd.DateOffset(years=train_years)
        test_end = train_end + pd.DateOffset(years=test_years)
        if train_end >= df.index[-1]:
            break
        test_end = min(test_end, df.index[-1])

        train_df = df[(df.index >= train_start) & (df.index < train_end)]
        test_df = df[(df.index >= train_end) & (df.index <= test_end)]

        if len(train_df) < 200 or len(test_df) < 30:
            break

        best = optimize(train_df)
        test_result = switcher_run(test_df, **best)

        folds.append(
            {
                "train_start": train_start,
                "train_end": train_end,
                "test_start": train_end,
                "test_end": test_end,
                "best_params": best,
                "metrics": test_result["metrics"],
                "equity": test_result["equity"],
                "returns": test_result["returns"],
                "regime": test_result["regime"],
            }
        )

        print(
            f"  Fold {len(folds):>2}  "
            f"train [{train_start.date()} ~ {train_end.date()}]  "
            f"test [{train_end.date()} ~ {test_end.date()}]  "
            f"params k={best['k']} adx={best['adx_bull']}  "
            f"CAGR={test_result['metrics']['cagr']:.1f}%  "
            f"Sharpe={test_result['metrics']['sharpe']:.2f}"
        )

        train_start += pd.DateOffset(years=test_years)

    return folds


def stitch_oos(folds: list[dict]) -> tuple[pd.Series, pd.Series]:
    """Stitch OOS equity and returns from all folds."""
    all_returns = pd.concat([f["returns"] for f in folds])
    all_equity = (1 + all_returns).cumprod()
    return all_equity, all_returns


# ------------------------------------------------------------------
# Report & Plot
# ------------------------------------------------------------------


def print_simple_report(result: dict) -> None:
    p = result["best_params"]
    print(f"\n{'=' * 60}")
    print(f"  Simple Split  |  k={p['k']}  adx_bull={p['adx_bull']}")
    print(f"{'=' * 60}")
    print(f"  {'Period':<14} {'CAGR':>8} {'MDD':>8} {'Sharpe':>8}")
    print(f"  {'-' * 44}")
    for label, m, b in [
        ("Train (IS)", result["train"]["metrics"], result["bnh_train"]),
        ("Test  (OOS)", result["test"]["metrics"], result["bnh_test"]),
    ]:
        print(f"  {label:<14} {m['cagr']:>7.2f}%  {m['mdd']:>7.2f}%  {m['sharpe']:>7.3f}  (strategy)")
        print(f"  {'B&H ' + label[5:]:<14} {b['cagr']:>7.2f}%  {b['mdd']:>7.2f}%  {b['sharpe']:>7.3f}  (B&H)")
        print(f"  {'-' * 44}")
    print(f"{'=' * 60}")


def print_wfa_report(folds: list[dict], oos_equity: pd.Series, oos_returns: pd.Series) -> None:
    oos_metrics = summary(oos_equity, oos_returns)
    print(f"\n{'=' * 60}")
    print(f"  Walk-Forward Analysis  ({len(folds)} folds)")
    print(f"{'=' * 60}")
    print(f"  {'Fold':<5} {'Test Period':<24} {'Params':<14} {'CAGR':>7} {'MDD':>7} {'Sharpe':>7}")
    print(f"  {'-' * 56}")
    for i, f in enumerate(folds, 1):
        p = f["best_params"]
        period = f"{f['test_start'].date()} ~ {f['test_end'].date()}"
        params = f"k={p['k']} adx={p['adx_bull']}"
        m = f["metrics"]
        print(f"  {i:<5} {period:<24} {params:<14} {m['cagr']:>6.1f}% {m['mdd']:>6.1f}% {m['sharpe']:>7.2f}")
    print(f"  {'─' * 56}")
    print(
        f"  {'OOS Total':<5} {str(folds[0]['test_start'].date()) + ' ~':<24} {'':14} "
        f"{oos_metrics['cagr']:>6.1f}% {oos_metrics['mdd']:>6.1f}% {oos_metrics['sharpe']:>7.2f}"
    )
    print(f"{'=' * 60}")


def plot_wfa(
    df: pd.DataFrame,
    folds: list[dict],
    oos_equity: pd.Series,
    simple_result: dict,
) -> None:
    fig, axes = plt.subplots(2, 1, figsize=(16, 10))

    # --- simple split ---
    ax = axes[0]
    split = pd.Timestamp(simple_result["split_date"])
    train_eq = simple_result["train"]["equity"]
    test_eq = simple_result["test"]["equity"]
    # normalise test to continue from train's last value
    test_eq_scaled = test_eq * train_eq.iloc[-1]

    ax.plot(train_eq.index, train_eq, color="#1f77b4", label="Train (IS)")
    ax.plot(test_eq_scaled.index, test_eq_scaled, color="#ff7f0e", label="Test (OOS)")
    ax.axvline(split, color="black", linestyle="--", linewidth=1, label=f"Split {split.date()}")
    bnh = (1 + df["Close"].pct_change().fillna(0)).cumprod()
    ax.plot(bnh.index, bnh, color="gray", alpha=0.35, linewidth=1, label="Buy & Hold")
    ax.set_title("Simple Train/Test Split")
    ax.set_ylabel("Growth of $1")
    ax.legend(fontsize=9)
    ax.grid(alpha=0.3)

    # --- walk-forward OOS ---
    ax2 = axes[1]
    colors = plt.cm.tab10.colors
    for i, f in enumerate(folds):
        ax2.plot(
            f["equity"].index,
            f["equity"]
            / f["equity"].iloc[0]
            * (1 if i == 0 else oos_equity[oos_equity.index <= f["equity"].index[0]].iloc[-1]),
            color=colors[i % 10],
            linewidth=1.2,
            label=f"Fold {i + 1}",
        )

    ax2.plot(oos_equity.index, oos_equity, color="black", linewidth=2, label="OOS Stitched")
    bnh_oos = (1 + df.loc[oos_equity.index, "Close"].pct_change().fillna(0)).cumprod()
    ax2.plot(bnh_oos.index, bnh_oos, color="gray", alpha=0.4, linewidth=1, label="B&H (OOS period)")
    ax2.set_title("Walk-Forward OOS Equity (stitched)")
    ax2.set_ylabel("Growth of $1")
    ax2.legend(fontsize=8, ncol=3)
    ax2.grid(alpha=0.3)

    fig.tight_layout()
    path = REPORT_DIR / "btc_usd_wfa.png"
    fig.savefig(path, dpi=150)
    plt.close(fig)
    print(f"\nChart saved: {path}")


# ------------------------------------------------------------------
# Main
# ------------------------------------------------------------------

if __name__ == "__main__":
    from data.collector import load

    df = load("BTC-USD")

    print("=" * 60)
    print("  SIMPLE SPLIT")
    print("=" * 60)
    simple = simple_split(df)
    print_simple_report(simple)

    print("\n" + "=" * 60)
    print("  WALK-FORWARD ANALYSIS  (train=3yr, test=1yr)")
    print("=" * 60)
    folds = walk_forward(df)
    oos_eq, oos_ret = stitch_oos(folds)
    print_wfa_report(folds, oos_eq, oos_ret)

    plot_wfa(df, folds, oos_eq, simple)
