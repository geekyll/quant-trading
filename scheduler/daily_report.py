"""
매일 08:30 결과 보고서 (단계 19).

페이퍼 포트폴리오 현황(당일/누적 손익·TOTAL)과 현재 레짐/신호를 모아
Claude Code(headless)로 간략한 한국어 보고서를 생성해 Telegram으로 보낸다.

보고서 포함:
  - 당일/누적 거래·손익·TOTAL 요약
  - 장이 안 좋거나 적합 전략이 없었다면 왜 부적합했는지
  - 오버피팅되지 않는 선에서 개선 가능한지
  - 현재 전략 유지 vs 변경 판단

09:00 코드점검(daily_review.py)과 별개 잡. 08:30 launchd/cron 트리거 의도.

Run:  uv run python -m scheduler.daily_report
"""

from __future__ import annotations

from datetime import date

from data.intraday import current_price, fetch_daily
from paper.portfolio import PaperPortfolio
from scheduler.daily_review import run_claude
from scheduler.notify import send_telegram
from strategy.live import live_signal

ASSETS = ["BTC-USD"]
CHAR_LIMIT = 900

REPORT_PROMPT = (
    "아래는 오늘자 BTC 페이퍼 트레이딩 현황이야. 이걸 근거로 간략한 결과 보고서를 작성해.\n"
    "반드시 포함: 1) 당일/누적 손익·TOTAL 요약, "
    "2) 장이 안 좋거나 적합 전략이 없었다면 왜 부적합했는지, "
    "3) 오버피팅되지 않는 선에서 개선 가능한지, "
    "4) 현재 전략을 유지하는 게 나은지 변경이 나은지 판단.\n"
    "텔레그램으로 보낼 한국어 메시지 하나로, 다른 말 없이 본문만. 700자 이내.\n\n"
    "=== 현황 데이터 ===\n"
)


def build_context() -> str:
    pf = PaperPortfolio()
    trades = PaperPortfolio.load_trades()
    today = date.today().isoformat()

    lines = [f"날짜: {today}"]
    for ticker in ASSETS:
        try:
            daily = fetch_daily(ticker, count=400)
            price = current_price(ticker)
        except Exception as e:
            lines.append(f"{ticker}: 데이터 수집 실패 ({e})")
            continue
        in_pos = ticker in pf.state["positions"]
        sig = live_signal(daily, current_price=price, in_position=in_pos)
        lines.append(
            f"{ticker}: price={price:,.0f} regime={sig['regime']} "
            f"strategy={sig['strategy']} action={sig['action']} reason={sig['reason']}"
        )
        prices = {ticker: price}

    summary = pf.summary(prices if ASSETS else {})
    lines.append(
        f"TOTAL={summary['total_value']:,.0f} KRW ({summary['total_return_pct']:+.2f}%), "
        f"현금={summary['cash']:,.0f}, 평가={summary['holdings_value']:,.0f}, "
        f"실현손익={summary['realized_pnl']:,.0f}, 평가손익={summary['unrealized_pnl']:,.0f}"
    )
    if summary["by_category"]:
        lines.append(f"분류별: {summary['by_category']}")

    if not trades.empty:
        today_trades = trades[trades["timestamp"].str.startswith(today)]
        lines.append(f"당일 거래 {len(today_trades)}건 / 누적 {len(trades)}건")
        for _, t in today_trades.tail(10).iterrows():
            lines.append(
                f"  {t['timestamp']} {t['side']} {t['ticker']} "
                f"qty={t['qty']} price={t['price']:,.0f} pnl={t['pnl']:,.0f}"
            )
    else:
        lines.append("거래 내역 없음 (관망 중)")

    return "\n".join(lines)


def main() -> None:
    context = build_context()
    print("=== context ===")
    print(context)
    result = run_claude(REPORT_PROMPT + context)
    if len(result) > CHAR_LIMIT:
        result = result[: CHAR_LIMIT - 1].rstrip() + "…"
    print("\n=== report ===")
    print(result)
    send_telegram(result)


if __name__ == "__main__":
    main()
