"""
Intraday data pipeline — Upbit OHLCV 수집 (단계 13).

실시간 루프에서 쓸 봉 데이터를 가져온다. 레짐/SMA200 판단은 일봉(day),
큰 변동 감지·돌파 판정은 30분봉(minute30)을 사용한다.
반환 DataFrame은 일봉 collector(load)와 동일하게
Open/High/Low/Close/Volume, DatetimeIndex(name="Date") 형식으로 맞춘다.

Run:  uv run python -m data.intraday
"""

from __future__ import annotations

import pandas as pd
import pyupbit

# Upbit 시장 코드. 내부 티커("BTC-USD") → Upbit 마켓("KRW-BTC") 매핑.
MARKET_MAP = {
    "BTC-USD": "KRW-BTC",
    "BTC": "KRW-BTC",
    "KRW-BTC": "KRW-BTC",
}


def to_market(ticker: str) -> str:
    return MARKET_MAP.get(ticker, ticker)


def _normalize(df: pd.DataFrame) -> pd.DataFrame:
    """pyupbit OHLCV → 프로젝트 표준 형식(Open/High/Low/Close/Volume, index=Date)."""
    if df is None or df.empty:
        raise RuntimeError("Upbit OHLCV 응답이 비어 있습니다 (요청 과다/네트워크 확인).")
    out = df.rename(
        columns={
            "open": "Open",
            "high": "High",
            "low": "Low",
            "close": "Close",
            "volume": "Volume",
        }
    )[["Open", "High", "Low", "Close", "Volume"]].copy()
    out.index.name = "Date"
    return out


def fetch_ohlcv(ticker: str = "BTC-USD", interval: str = "minute30", count: int = 200) -> pd.DataFrame:
    """Upbit OHLCV 조회.

    interval: "day", "minute1", "minute3", "minute5", "minute15", "minute30",
              "minute60", "minute240", "week", "month".
    count: 가져올 봉 개수 (레짐/SMA200 판단용 일봉은 최소 200+ 권장).
    """
    market = to_market(ticker)
    df = pyupbit.get_ohlcv(market, interval=interval, count=count)
    return _normalize(df)


def fetch_daily(ticker: str = "BTC-USD", count: int = 400) -> pd.DataFrame:
    """레짐/SMA200 판단용 일봉. SMA200 + 여유분 확보를 위해 기본 400봉."""
    return fetch_ohlcv(ticker, interval="day", count=count)


def fetch_intraday(ticker: str = "BTC-USD", interval: str = "minute30", count: int = 200) -> pd.DataFrame:
    """변동 감지/돌파 판정용 인트라데이 봉."""
    return fetch_ohlcv(ticker, interval=interval, count=count)


def current_price(ticker: str = "BTC-USD") -> float:
    return float(pyupbit.get_current_price(to_market(ticker)))


if __name__ == "__main__":
    print("=== Upbit 일봉 (최근 3봉) ===")
    daily = fetch_daily("BTC-USD", count=400)
    print(daily.tail(3))
    print(f"\n총 {len(daily)}봉, 기간 {daily.index[0].date()} ~ {daily.index[-1].date()}")

    print("\n=== Upbit 30분봉 (최근 3봉) ===")
    intr = fetch_intraday("BTC-USD", interval="minute30", count=200)
    print(intr.tail(3))

    print(f"\n현재가: {current_price('BTC-USD'):,.0f} KRW")
