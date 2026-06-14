"""
Larry Williams Volatility Breakout Strategy.

Entry  : open[t] + k * (high[t-1] - low[t-1])  — intraday trigger
Exit   : open[t+1]  — hold overnight, exit next open
Signal : 1 if high[t] > entry_price, else 0
"""

import pandas as pd


def signal(df: pd.DataFrame, k: float = 0.5) -> pd.Series:
    prev_range = df["High"].shift(1) - df["Low"].shift(1)
    entry_price = df["Open"] + k * prev_range

    # triggered when intraday high exceeds entry level
    triggered = df["High"] > entry_price

    # return: exit at next open vs entry price
    next_open = df["Open"].shift(-1)
    day_return = (next_open / entry_price - 1).where(triggered, 0)

    return day_return.fillna(0)


def backtest(df: pd.DataFrame, k: float = 0.5) -> dict:
    from backtest.metrics import summary

    ret = signal(df, k)
    equity = (1 + ret).cumprod()
    return {"returns": ret, "equity": equity, "metrics": summary(equity, ret), "label": f"VB(k={k})"}


if __name__ == "__main__":
    from data.collector import load

    df = load("BTC-USD")
    for k in [0.3, 0.5, 0.7]:
        r = backtest(df, k)
        m = r["metrics"]
        print(f"k={k}  CAGR={m['cagr']:>7.2f}%  MDD={m['mdd']:>7.2f}%  Sharpe={m['sharpe']:.3f}")
