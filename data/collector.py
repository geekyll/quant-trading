from pathlib import Path

import pandas as pd
import yfinance as yf

from data.universe import UNIVERSE, Asset

RAW_DIR = Path(__file__).parent / "raw"
RAW_DIR.mkdir(exist_ok=True)


def fetch(asset: Asset, end: str | None = None) -> pd.DataFrame:
    ticker = yf.Ticker(asset.ticker)
    df = ticker.history(start=asset.start, end=end, auto_adjust=True)
    df.index = df.index.tz_localize(None)
    df.index.name = "Date"
    return df[["Open", "High", "Low", "Close", "Volume"]]


def validate(df: pd.DataFrame) -> dict:
    return {
        "trading_days": len(df),
        "missing": df.isnull().sum().to_dict(),
        "zero_or_negative_close": int((df["Close"] <= 0).sum()),
        "duplicate_dates": int(df.index.duplicated().sum()),
    }


def clean(df: pd.DataFrame) -> pd.DataFrame:
    df = df[df["Close"] > 0]
    df = df[~df.index.duplicated(keep="last")]
    df = df.dropna(subset=["Close"])
    return df.sort_index()


def save(df: pd.DataFrame, ticker: str) -> Path:
    path = RAW_DIR / f"{ticker.lower().replace('-', '_')}.csv"
    df.to_csv(path)
    return path


def load(ticker: str) -> pd.DataFrame:
    path = RAW_DIR / f"{ticker.lower().replace('-', '_')}.csv"
    return pd.read_csv(path, index_col="Date", parse_dates=True)


def fetch_all(end: str | None = None) -> dict[str, pd.DataFrame]:
    results = {}
    for asset in UNIVERSE:
        print(f"[{asset.ticker}] Fetching {asset.name}...")
        raw = fetch(asset, end=end)
        report = validate(raw)
        df = clean(raw)
        path = save(df, asset.ticker)
        print(f"  Period : {df.index[0].date()} ~ {df.index[-1].date()}")
        print(f"  Trading days : {report['trading_days']:,}")
        print(f"  Saved  : {path}")
        results[asset.ticker] = df
    return results


if __name__ == "__main__":
    print("=== Fetching all assets in universe ===\n")
    fetch_all()
    print("\nDone.")
