from pathlib import Path

import pandas as pd
import yfinance as yf

REPORT_DIR = Path(__file__).parent.parent / "report"
LOOKBACK_MONTHS = {"3m": 63, "6m": 126, "12m": 252}
TOP_N = 10


def get_nasdaq100_tickers() -> list[str]:
    url = "https://en.wikipedia.org/wiki/Nasdaq-100"
    tables = pd.read_html(url)
    # the constituents table has a 'Ticker' column
    for t in tables:
        if "Ticker" in t.columns:
            return t["Ticker"].tolist()
    raise ValueError("Could not parse NASDAQ-100 tickers from Wikipedia")


def fetch_returns(tickers: list[str], period_days: int) -> pd.Series:
    raw = yf.download(tickers, period=f"{period_days + 10}d", auto_adjust=True, progress=False)["Close"]
    ret = raw.iloc[-1] / raw.iloc[0] - 1
    return ret.dropna()


def momentum_score(tickers: list[str]) -> pd.DataFrame:
    scores = {}
    for label, days in LOOKBACK_MONTHS.items():
        scores[label] = fetch_returns(tickers, days)
    df = pd.DataFrame(scores)
    df["score"] = df.mean(axis=1)
    return df.sort_values("score", ascending=False)


def top_picks(n: int = TOP_N) -> pd.DataFrame:
    print("Fetching NASDAQ-100 tickers...")
    tickers = get_nasdaq100_tickers()
    print(f"Computing momentum for {len(tickers)} stocks...")
    df = momentum_score(tickers)
    return df.head(n)


if __name__ == "__main__":
    picks = top_picks()
    print(f"\nTop {TOP_N} NASDAQ-100 by momentum score:\n")
    print(picks.to_string(float_format=lambda x: f"{x:.2%}"))
    path = REPORT_DIR / "momentum_top10.csv"
    picks.to_csv(path)
    print(f"\nSaved: {path}")
