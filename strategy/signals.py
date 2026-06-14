from data.collector import load
from data.universe import UNIVERSE
from strategy.ma import add_sma


def current_signals(sma_period: int = 200) -> list[dict]:
    signals = []
    for asset in UNIVERSE:
        df = load(asset.ticker)
        df = add_sma(df, periods=[sma_period])
        latest = df.iloc[-1]
        col = f"SMA{sma_period}"
        signal = "BUY" if latest["Close"] > latest[col] else "SELL"
        signals.append(
            {
                "ticker": asset.ticker,
                "date": df.index[-1].date().isoformat(),
                "close": round(float(latest["Close"]), 4),
                f"sma{sma_period}": round(float(latest[col]), 4),
                "signal": signal,
            }
        )
    return signals


if __name__ == "__main__":
    for s in current_signals():
        print(
            f"[{s['date']}] {s['ticker']:8s}  Close={s['close']:>10.2f}  SMA200={s['sma200']:>10.2f}  -> {s['signal']}"
        )  # noqa: E501
