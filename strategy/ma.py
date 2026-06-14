from pathlib import Path

import matplotlib.pyplot as plt
import pandas as pd

PERIODS = [20, 50, 100, 200]
REPORT_DIR = Path(__file__).parent.parent / "report"
REPORT_DIR.mkdir(exist_ok=True)


def add_sma(df: pd.DataFrame, periods: list[int] = PERIODS) -> pd.DataFrame:
    result = df.copy()
    for p in periods:
        result[f"SMA{p}"] = result["Close"].rolling(p).mean()
    return result


def plot(df: pd.DataFrame, ticker: str, periods: list[int] = PERIODS, save: bool = True) -> None:
    fig, ax = plt.subplots(figsize=(16, 6))
    ax.plot(df.index, df["Close"], label="Close", linewidth=1, color="black")
    colors = {20: "#1f77b4", 50: "#ff7f0e", 100: "#2ca02c", 200: "#d62728"}
    for p in periods:
        col = f"SMA{p}"
        if col in df.columns:
            ax.plot(df.index, df[col], label=col, linewidth=1, color=colors.get(p))
    ax.set_title(f"{ticker} — Close vs SMA")
    ax.set_xlabel("Date")
    ax.set_ylabel("Price (USD)")
    ax.legend()
    ax.grid(alpha=0.3)
    fig.tight_layout()
    if save:
        path = REPORT_DIR / f"{ticker.lower().replace('-', '_')}_sma.png"
        fig.savefig(path, dpi=150)
        print(f"Saved: {path}")
    plt.close(fig)


if __name__ == "__main__":
    from data.collector import load
    from data.universe import TICKERS

    for ticker in TICKERS:
        print(f"[{ticker}] Computing SMA...")
        df = load(ticker)
        df = add_sma(df)
        print(df[[c for c in df.columns if "SMA" in c]].tail(3).to_string())
        plot(df, ticker)
        print()
