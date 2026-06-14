"""
Grid / Mean-Reversion Strategy (sideways regime).

Uses Bollinger Bands as grid boundaries:
  Buy  : close crosses below lower band  (oversold)
  Sell : close crosses above upper band  (overbought)
  Hold : otherwise maintain position
"""

import pandas as pd


def signal(df: pd.DataFrame, window: int = 20, std_mult: float = 1.5) -> pd.Series:
    mid = df["Close"].rolling(window).mean()
    std = df["Close"].rolling(window).std()
    upper = mid + std_mult * std
    lower = mid - std_mult * std

    position = pd.Series(0, index=df.index, dtype=float)
    pos = 0

    for i in range(window, len(df)):
        close = df["Close"].iloc[i]
        if pos == 0 and close < lower.iloc[i]:
            pos = 1  # buy
        elif pos == 1 and close > upper.iloc[i]:
            pos = 0  # sell
        position.iloc[i] = pos

    return position.shift(1).fillna(0)


def backtest(df: pd.DataFrame, window: int = 20, std_mult: float = 1.5) -> dict:
    from backtest.metrics import summary

    pos = signal(df, window, std_mult)
    daily_ret = df["Close"].pct_change().fillna(0)
    ret = pos * daily_ret
    equity = (1 + ret).cumprod()
    return {
        "returns": ret,
        "equity": equity,
        "metrics": summary(equity, ret),
        "label": f"Grid(BB {window},{std_mult})",
    }


if __name__ == "__main__":
    from data.collector import load

    df = load("BTC-USD")
    r = backtest(df)
    m = r["metrics"]
    print(f"Grid  CAGR={m['cagr']:>7.2f}%  MDD={m['mdd']:>7.2f}%  Sharpe={m['sharpe']:.3f}")
