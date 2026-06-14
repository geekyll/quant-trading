import yfinance as yf
import pandas as pd
from pathlib import Path

DATA_DIR = Path(__file__).parent
START_DATE = "2005-01-01"


def fetch_qqq(start: str = START_DATE, end: str | None = None) -> pd.DataFrame:
    ticker = yf.Ticker("QQQ")
    df = ticker.history(start=start, end=end, auto_adjust=True)
    df.index = df.index.tz_localize(None)
    df.index.name = "Date"
    return df[["Open", "High", "Low", "Close", "Volume"]]


def validate(df: pd.DataFrame) -> dict:
    missing = df.isnull().sum().to_dict()
    zero_close = (df["Close"] <= 0).sum()
    duplicates = df.index.duplicated().sum()
    trading_days = len(df)
    return {
        "trading_days": trading_days,
        "missing": missing,
        "zero_or_negative_close": int(zero_close),
        "duplicate_dates": int(duplicates),
    }


def clean(df: pd.DataFrame) -> pd.DataFrame:
    df = df[df["Close"] > 0]
    df = df[~df.index.duplicated(keep="last")]
    df = df.dropna(subset=["Close"])
    df = df.sort_index()
    return df


def save(df: pd.DataFrame, filename: str = "qqq.csv") -> Path:
    path = DATA_DIR / filename
    df.to_csv(path)
    return path


def load(filename: str = "qqq.csv") -> pd.DataFrame:
    path = DATA_DIR / filename
    df = pd.read_csv(path, index_col="Date", parse_dates=True)
    return df


if __name__ == "__main__":
    print("Fetching QQQ data...")
    raw = fetch_qqq()

    report = validate(raw)
    print(f"Period : {raw.index[0].date()} ~ {raw.index[-1].date()}")
    print(f"Trading days    : {report['trading_days']:,}")
    print(f"Missing values  : {report['missing']}")
    print(f"Bad close price : {report['zero_or_negative_close']}")
    print(f"Duplicate dates : {report['duplicate_dates']}")

    df = clean(raw)
    path = save(df)
    print(f"\nSaved to: {path}")
    print(df.tail())
