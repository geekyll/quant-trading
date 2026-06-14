from enum import Enum

import pandas as pd


class Regime(str, Enum):
    BULL = "BULL"  # ADX > threshold, price > SMA200
    SIDEWAYS_UP = "SIDEWAYS_UP"  # ADX < threshold, price > SMA200
    BEAR = "BEAR"  # ADX > threshold, price < SMA200
    SIDEWAYS_DOWN = "SIDEWAYS_DOWN"  # ADX < threshold, price < SMA200


def _calc_adx(df: pd.DataFrame, period: int = 14) -> pd.Series:
    high, low, close = df["High"], df["Low"], df["Close"]
    prev_close = close.shift(1)
    prev_high = high.shift(1)
    prev_low = low.shift(1)

    tr = pd.concat(
        [high - low, (high - prev_close).abs(), (low - prev_close).abs()],
        axis=1,
    ).max(axis=1)

    plus_dm = (high - prev_high).clip(lower=0).where((high - prev_high) > (prev_low - low), 0)
    minus_dm = (prev_low - low).clip(lower=0).where((prev_low - low) > (high - prev_high), 0)

    def wilder_sum(s: pd.Series, n: int) -> pd.Series:
        """Wilder smoothed sum — used for TR and DM (seed = sum of first n)."""
        result = s.copy().astype(float)
        result.iloc[:n] = float("nan")
        result.iloc[n] = s.iloc[1 : n + 1].sum()
        for i in range(n + 1, len(s)):
            result.iloc[i] = result.iloc[i - 1] - result.iloc[i - 1] / n + s.iloc[i]
        return result

    def wilder_avg(s: pd.Series, n: int) -> pd.Series:
        """Wilder smoothed average — used for ADX (seed = mean of first n DX values)."""
        result = s.copy().astype(float)
        result.iloc[:n] = float("nan")
        result.iloc[n] = s.iloc[1 : n + 1].mean()
        for i in range(n + 1, len(s)):
            result.iloc[i] = result.iloc[i - 1] * (n - 1) / n + s.iloc[i] / n
        return result

    atr = wilder_sum(tr, period)
    plus_di = 100 * wilder_sum(plus_dm, period) / atr
    minus_di = 100 * wilder_sum(minus_dm, period) / atr
    dx = 100 * (plus_di - minus_di).abs() / (plus_di + minus_di)
    adx = wilder_avg(dx, period)
    return adx


def detect(
    df: pd.DataFrame,
    adx_period: int = 14,
    sma_period: int = 200,
    adx_bull: float = 25,
    adx_side: float = 20,
    confirm_days: int = 3,
) -> pd.Series:
    """
    Returns a Series of Regime values aligned to df.index.
    confirm_days: regime must persist N days before switching (avoids whipsaw).
    """
    adx = _calc_adx(df, adx_period)
    sma = df["Close"].rolling(sma_period).mean()
    above_sma = df["Close"] > sma

    raw = pd.Series(index=df.index, dtype=object)
    for i in range(len(df)):
        if pd.isna(adx.iloc[i]):
            raw.iloc[i] = None
            continue
        trending = adx.iloc[i] > adx_bull
        ranging = adx.iloc[i] < adx_side
        up = above_sma.iloc[i]

        if trending and up:
            raw.iloc[i] = Regime.BULL
        elif ranging and up:
            raw.iloc[i] = Regime.SIDEWAYS_UP
        elif trending and not up:
            raw.iloc[i] = Regime.BEAR
        else:
            raw.iloc[i] = Regime.SIDEWAYS_DOWN

    # apply confirmation: only switch after confirm_days of same regime
    confirmed = raw.copy()
    current = None
    streak = 0
    pending = None
    pending_count = 0

    for i in range(len(raw)):
        v = raw.iloc[i]
        if v is None:
            confirmed.iloc[i] = current
            continue
        if v == current:
            streak += 1
            pending = None
            pending_count = 0
        else:
            if v == pending:
                pending_count += 1
                if pending_count >= confirm_days:
                    current = pending
                    pending = None
                    pending_count = 0
            else:
                pending = v
                pending_count = 1
        confirmed.iloc[i] = current

    return confirmed


if __name__ == "__main__":
    from data.collector import load

    df = load("BTC-USD")
    regime = detect(df)
    latest = regime.dropna().iloc[-5:]
    counts = regime.value_counts()

    print("=== Last 5 days ===")
    for date, r in latest.items():
        print(f"  {date.date()}  {r}")

    print("\n=== Regime distribution ===")
    total = counts.sum()
    for r, n in counts.items():
        print(f"  {str(r):<20}  {n:>4} days  ({n / total * 100:.1f}%)")
