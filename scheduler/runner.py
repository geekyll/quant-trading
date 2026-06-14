"""
Daily scheduler — runs after US market close (21:30 KST).
Steps:
  1. Fetch latest data for all universe tickers
  2. Generate signals
  3. Execute paper trades
  4. Send notifications

Run manually:   python -m scheduler.runner
Run as daemon:  python -m scheduler.runner --daemon
"""

import sys
from datetime import datetime

from apscheduler.schedulers.blocking import BlockingScheduler
from apscheduler.triggers.cron import CronTrigger

from data.collector import fetch_all
from scheduler.notify import format_signals, send
from strategy.signals import current_signals


def job() -> None:
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print(f"\n[{now}] Starting daily job...")

    # 1. refresh data
    print("Fetching latest data...")
    fetch_all()

    # 2. generate signals
    signals = current_signals()
    print("Signals:")
    for s in signals:
        print(f"  {s['ticker']:8s}  {s['signal']}  close={s['close']:.2f}  sma200={s['sma200']:.2f}")

    # 3. paper trade
    from backtest.paper_trade import run_once

    print("\nExecuting paper trades...")
    run_once()

    # 4. notify
    message = format_signals(signals)
    send(message)

    print(f"[{now}] Job complete.\n")


def main() -> None:
    if "--daemon" in sys.argv:
        scheduler = BlockingScheduler(timezone="Asia/Seoul")
        # 21:30 KST = after NASDAQ close (16:00 ET)
        scheduler.add_job(job, CronTrigger(hour=21, minute=30, timezone="Asia/Seoul"))
        print("Scheduler started. Daily job at 21:30 KST. Press Ctrl+C to stop.")
        try:
            scheduler.start()
        except KeyboardInterrupt:
            print("Scheduler stopped.")
    else:
        job()


if __name__ == "__main__":
    main()
