"""
Live signal — 현재 시점의 매매 신호 추출 (단계 12).

backtest용 switcher.py/grid.py/volatility_breakout.py 는 "전체 시계열의 수익률"을
계산하지만, 실시간 매매에는 "지금 이 순간 사야/팔아야/유지해야 하는가"가 필요하다.
이 모듈은 같은 레짐 → 전략 매핑을 쓰되, 마지막 봉(또는 실시간 현재가) 기준으로
target position(0/1)과 action(BUY/SELL/HOLD)을 반환한다.

레짐 → 전략
  BULL          Volatility Breakout (k=0.5)
  SIDEWAYS_UP   Grid / Mean-Reversion (Bollinger Band)
  BEAR          Cash
  SIDEWAYS_DOWN Cash

Run:  uv run python -m strategy.live
"""

from __future__ import annotations

import pandas as pd

from strategy.regime import Regime, detect


def _vb_target(df: pd.DataFrame, price: float, k: float) -> tuple[int, float]:
    """Volatility Breakout: 당일 고가(또는 현재가)가 돌파선을 넘으면 진입(1)."""
    prev_range = float(df["High"].iloc[-2] - df["Low"].iloc[-2])
    entry_level = float(df["Open"].iloc[-1]) + k * prev_range
    high = max(float(df["High"].iloc[-1]), price)
    target = 1 if high >= entry_level else 0
    return target, entry_level


def _grid_target(
    df: pd.DataFrame, price: float, window: int, std_mult: float, in_position: bool
) -> tuple[int, tuple[float, float, float]]:
    """Grid/Mean-Reversion: 하단 밴드 이탈 시 진입, 상단 밴드 돌파 시 청산 (상태 의존)."""
    close = df["Close"]
    mid = float(close.rolling(window).mean().iloc[-1])
    std = float(close.rolling(window).std().iloc[-1])
    upper = mid + std_mult * std
    lower = mid - std_mult * std

    if not in_position and price < lower:
        target = 1  # 과매도 → 매수
    elif in_position and price > upper:
        target = 0  # 과매수 → 매도
    else:
        target = 1 if in_position else 0  # 유지
    return target, (lower, mid, upper)


def _action(in_position: bool, target: int) -> str:
    if target == 1 and not in_position:
        return "BUY"
    if target == 0 and in_position:
        return "SELL"
    return "HOLD"


def live_signal(
    df: pd.DataFrame,
    *,
    current_price: float | None = None,
    in_position: bool = False,
    k: float = 0.5,
    adx_bull: float = 25,
    adx_side: float = 20,
    grid_window: int = 20,
    grid_std: float = 1.5,
) -> dict:
    """현재 시점의 매매 신호를 반환한다.

    Args:
        df: OHLCV DataFrame (레짐/SMA200 판단을 위해 일봉 권장).
        current_price: 실시간 현재가. 없으면 마지막 봉 종가 사용.
        in_position: 현재 해당 자산을 보유 중인지 (action 판정에 사용).

    Returns:
        dict — date, regime, strategy, target_position, action, reason, price, detail
    """
    regime = detect(df, adx_bull=adx_bull, adx_side=adx_side).iloc[-1]
    regime_name = regime.value if isinstance(regime, Regime) else str(regime)
    price = float(current_price) if current_price is not None else float(df["Close"].iloc[-1])

    detail: dict = {}
    if regime == Regime.BULL:
        strategy = "VB"
        target, entry_level = _vb_target(df, price, k)
        detail["entry_level"] = round(entry_level, 4)
        state = "돌파" if target else "미돌파"
        reason = f"BULL → Volatility Breakout (entry={entry_level:,.2f}, price={price:,.2f}, {state})"
    elif regime == Regime.SIDEWAYS_UP:
        strategy = "GRID"
        target, (lower, mid, upper) = _grid_target(df, price, grid_window, grid_std, in_position)
        detail.update(lower=round(lower, 4), mid=round(mid, 4), upper=round(upper, 4))
        reason = f"SIDEWAYS_UP → Grid (lower={lower:,.2f}, upper={upper:,.2f}, price={price:,.2f})"
    else:  # BEAR, SIDEWAYS_DOWN, None
        strategy = "CASH"
        target = 0
        reason = f"{regime_name} → 현금 보유 (no position)"

    action = _action(in_position, target)
    return {
        "date": df.index[-1].date().isoformat(),
        "regime": regime_name,
        "strategy": strategy,
        "target_position": target,
        "action": action,
        "price": round(price, 4),
        "in_position": in_position,
        "reason": reason,
        "detail": detail,
    }


if __name__ == "__main__":
    from data.collector import load

    df = load("BTC-USD")
    print("=== BTC-USD live signal (현재 보유 없음 가정) ===")
    sig = live_signal(df, in_position=False)
    for key, val in sig.items():
        print(f"  {key:16s}: {val}")
