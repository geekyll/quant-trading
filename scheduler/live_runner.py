"""
실시간 루프 스케줄러 (단계 17 + 18).

매 주기(기본 30분):
  1. 일봉(레짐/SMA200) + 30분봉(변동) + 현재가 수집
  2. 큰 변동 감지 (단계 14)
  3. 현재 보유 여부로 live_signal 계산 (단계 12)
  4. action(BUY/SELL/HOLD)을 executor로 체결 (단계 16, paper/live 토글)
  5. 체결되면 즉시 Telegram 알림 (단계 18). 매매 없이 큰 변동만 있으면 변동 알림.

BTC는 24/7 이므로 interval 트리거를 쓴다.

Run 1회:    uv run python -m scheduler.live_runner
Run 데몬:   uv run python -m scheduler.live_runner --daemon
"""

from __future__ import annotations

import sys
from datetime import datetime

from apscheduler.schedulers.blocking import BlockingScheduler
from apscheduler.triggers.interval import IntervalTrigger

from broker.executor import TradeExecutor
from data.intraday import current_price, fetch_daily, fetch_intraday
from scheduler.notify import format_spike, format_trade, send_telegram
from strategy.live import live_signal
from strategy.trigger import detect_spike

ASSETS = ["BTC-USD"]  # 우선 BTC로 검증, 이후 NYSE 확장 (단계 23)
INTERVAL_MINUTES = 30


def cycle(executor: TradeExecutor) -> None:
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print(f"\n[{now}] live cycle (mode={'LIVE' if executor.live else 'PAPER'})")

    for ticker in ASSETS:
        try:
            daily = fetch_daily(ticker, count=400)
            intraday = fetch_intraday(ticker, interval="minute30", count=100)
            price = current_price(ticker)
        except Exception as e:
            print(f"  [{ticker}] 데이터 수집 실패: {e}")
            continue

        spike = detect_spike(intraday)
        in_pos = executor.in_position(ticker)
        signal = live_signal(daily, current_price=price, in_position=in_pos)
        print(
            f"  [{ticker}] regime={signal['regime']} strat={signal['strategy']} "
            f"action={signal['action']} price={price:,.0f} spike={spike['triggered']}"
        )

        trade = executor.execute(signal, ticker, price)
        if trade:
            summary = executor.pf.summary({ticker: price})
            msg = format_trade(trade, signal, summary, executor.live)
            print(f"  >> 체결: {trade.get('side')} {ticker}")
            send_telegram(msg)
        elif spike["triggered"]:
            print(f"  >> 큰 변동(매매 없음): {spike['reason']}")
            send_telegram(format_spike(ticker, spike, signal))


def main() -> None:
    executor = TradeExecutor()
    if "--daemon" in sys.argv:
        scheduler = BlockingScheduler(timezone="Asia/Seoul")
        scheduler.add_job(lambda: cycle(executor), IntervalTrigger(minutes=INTERVAL_MINUTES))
        print(f"Live runner started. Every {INTERVAL_MINUTES}min. Ctrl+C to stop.")
        try:
            scheduler.start()
        except KeyboardInterrupt:
            print("Live runner stopped.")
    else:
        cycle(executor)


if __name__ == "__main__":
    main()
