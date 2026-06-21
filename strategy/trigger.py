"""
큰 변동 감지 (단계 14).

인트라데이 봉으로 최근 30분/1시간/24시간 수익률과 변동성(ATR 대비)을 보고
임계치를 넘으면 "즉시 점검" 트리거를 발생시킨다. 실시간 루프는 정규 주기 외에
이 트리거로도 신호를 재계산할 수 있다.

Run:  uv run python -m strategy.trigger
"""

from __future__ import annotations

import pandas as pd

# 30분봉 기준 lookback (봉 개수). 30m=1봉, 1h=2봉, 24h=48봉.
WINDOWS = {"30m": 1, "1h": 2, "24h": 48}
PCT_THRESHOLD = 5.0   # 어느 한 윈도우라도 ±5% 초과 시 트리거
ATR_MULT = 2.0        # 최근 봉 변동폭이 ATR의 N배 초과 시 트리거


def _atr(df: pd.DataFrame, period: int = 14) -> float:
    high, low, close = df["High"], df["Low"], df["Close"]
    prev_close = close.shift(1)
    tr = pd.concat(
        [high - low, (high - prev_close).abs(), (low - prev_close).abs()], axis=1
    ).max(axis=1)
    return float(tr.rolling(period).mean().iloc[-1])


def detect_spike(
    df: pd.DataFrame,
    pct_threshold: float = PCT_THRESHOLD,
    atr_mult: float = ATR_MULT,
) -> dict:
    """df: 인트라데이 OHLCV (30분봉 권장). 트리거 여부와 근거를 반환."""
    close = df["Close"]
    price = float(close.iloc[-1])

    changes: dict[str, float] = {}
    pct_hit = False
    for label, bars in WINDOWS.items():
        if len(close) > bars:
            past = float(close.iloc[-1 - bars])
            pct = (price / past - 1) * 100
            changes[label] = round(pct, 2)
            if abs(pct) >= pct_threshold:
                pct_hit = True

    atr = _atr(df)
    last_range = float(df["High"].iloc[-1] - df["Low"].iloc[-1])
    atr_hit = atr > 0 and last_range > atr_mult * atr

    triggered = pct_hit or atr_hit
    reasons = []
    if pct_hit:
        big = max(changes.items(), key=lambda kv: abs(kv[1]))
        reasons.append(f"{big[0]} 변동 {big[1]:+.2f}% (임계 ±{pct_threshold}%)")
    if atr_hit:
        reasons.append(f"최근 봉 변동폭 {last_range:,.0f} > ATR×{atr_mult} ({atr * atr_mult:,.0f})")

    return {
        "triggered": triggered,
        "price": round(price, 4),
        "changes_pct": changes,
        "atr": round(atr, 4),
        "reason": " / ".join(reasons) if reasons else "정상 범위",
    }


if __name__ == "__main__":
    from data.intraday import fetch_intraday

    df = fetch_intraday("BTC-USD", interval="minute30", count=100)
    result = detect_spike(df)
    for k, v in result.items():
        print(f"  {k}: {v}")
