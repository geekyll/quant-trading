import sys
from pathlib import Path

import pandas as pd
import streamlit as st

sys.path.insert(0, str(Path(__file__).parent.parent))

from backtest.metrics import summary
from backtest.paper_trade import _load_portfolio, get_portfolio_value, load_trades
from backtest.wfa import optimize, stitch_oos, walk_forward
from data.collector import fetch_all, load
from data.universe import UNIVERSE
from paper.portfolio import PaperPortfolio
from strategy.signals import current_signals
from strategy.switcher import run as switcher_run


def _live_prices(positions: dict) -> dict:
    """보유 종목 현재가. BTC는 Upbit, 주식은 일봉 종가, 실패 시 평단으로 폴백."""
    prices = {}
    for ticker, pos in positions.items():
        try:
            if pos["category"] == "BTC":
                from data.intraday import current_price

                prices[ticker] = current_price(ticker)
            else:
                prices[ticker] = float(load(ticker)["Close"].iloc[-1])
        except Exception:
            prices[ticker] = pos["avg_price"]
    return prices

st.set_page_config(page_title="Quant Trading Dashboard", page_icon="📈", layout="wide")

TICKERS = [a.ticker for a in UNIVERSE]
TODAY = pd.Timestamp.today().normalize()

PERIOD_OPTIONS = [
    "Past 1 Month",
    "Past 3 Months",
    "Past 6 Months",
    "Past 1 Year",
    "Past 2 Years",
    "Past 3 Years",
    "Custom range",
]
PERIOD_MONTHS = {
    "Past 1 Month": 1,
    "Past 3 Months": 3,
    "Past 6 Months": 6,
    "Past 1 Year": 12,
    "Past 2 Years": 24,
    "Past 3 Years": 36,
}


# ──────────────────────────────────────────────
# Header
# ──────────────────────────────────────────────
col_title, col_stock, col_period = st.columns([3, 1, 1])

with col_title:
    st.markdown("## Quant Trading Dashboard")

with col_stock:
    ticker = st.selectbox("종목 (Stock)", TICKERS)

with col_period:
    period = st.selectbox("기간 (Period)", PERIOD_OPTIONS, index=3)

# 기간 계산
if period == "Custom range":
    date_range = st.date_input(
        "날짜 선택 (시작일 → 종료일)",
        value=(TODAY - pd.DateOffset(months=12)).date(),
        help="시작일을 먼저 클릭하고, 종료일을 클릭하세요.",
    )
    if isinstance(date_range, (list, tuple)) and len(date_range) == 2:
        start_date, end_date = date_range[0], date_range[1]
    else:
        start_date = date_range if not isinstance(date_range, (list, tuple)) else date_range[0]
        end_date = TODAY.date()
else:
    start_date = (TODAY - pd.DateOffset(months=PERIOD_MONTHS[period])).date()
    end_date = TODAY.date()

total_days = max((pd.Timestamp(end_date) - pd.Timestamp(start_date)).days, 1)

st.divider()


# ──────────────────────────────────────────────
# Tabs
# ──────────────────────────────────────────────
tab1, tab2, tab3, tab4, tab5 = st.tabs(
    [
        "Signals & Portfolio",
        "Regime Backtest",
        "Walk-Forward",
        "Data",
        "Paper Portfolio (Live)",
    ]
)


# ──────────────────────────────────────────────
# Tab 1 · Signals & Portfolio
# ──────────────────────────────────────────────
with tab1:
    st.caption(
        "SMA 기반 매수/매도 신호와 페이퍼 트레이딩 포트폴리오 현황을 확인합니다. "
        "신호는 매일 장 마감 후 자동으로 갱신됩니다."
    )
    st.divider()

    st.subheader("Current Signals")
    sma_period = st.selectbox("SMA Period", [20, 50, 100, 200], index=3)
    signals = current_signals(sma_period)
    sig_df = pd.DataFrame(signals)
    sig_df["signal"] = sig_df["signal"].map(lambda x: "BUY" if x == "BUY" else "SELL")
    st.dataframe(sig_df, use_container_width=True, hide_index=True)

    st.divider()
    st.subheader("Paper Portfolio")
    p = _load_portfolio()
    c1, c2, c3 = st.columns(3)
    c1.metric("Total Value", f"${get_portfolio_value(p):,.2f}")
    c2.metric("Cash", f"${p['cash']:,.2f}")
    c3.metric("Open Positions", len(p["positions"]))

    trades_df = load_trades()
    if not trades_df.empty:
        st.subheader("Trade Log")
        st.dataframe(trades_df.tail(20), use_container_width=True, hide_index=True)


# ──────────────────────────────────────────────
# Tab 2 · Regime Backtest
# ──────────────────────────────────────────────
with tab2:
    st.caption(
        f"ADX + SMA200으로 시장 레짐(BULL / SIDEWAYS / BEAR)을 자동 감지하고, "
        f"레짐별 전략을 적용한 백테스트 결과를 보여줍니다.  "
        f"대상: {ticker}  /  기간: {start_date} ~ {end_date}"
    )
    st.divider()

    col_l, col_r = st.columns([1, 3])

    with col_l:
        with st.container(border=True):
            st.markdown("**Strategy Parameters**")
            k = st.slider("k  (Volatility Breakout)", 0.3, 0.7, 0.5, 0.1)
            adx_bull = st.slider("ADX Bull threshold", 15, 40, 25, 5)
            adx_side = st.slider("ADX Side threshold", 10, 35, 20, 5)
            st.caption(f"BULL: ADX > {adx_bull}  /  SIDEWAYS: ADX < {adx_side}")
        run_btn = st.button("Run Backtest", type="primary", use_container_width=True)

    with col_r:
        if run_btn:
            with st.spinner("Running…"):
                df = load(ticker)
                df = df[(df.index >= pd.Timestamp(start_date)) & (df.index <= pd.Timestamp(end_date))]

            if len(df) < 30:
                st.error("데이터가 부족합니다. 기간을 늘려주세요.")
            else:
                result = switcher_run(df, k=k, adx_bull=adx_bull, adx_side=adx_side)
                m, b = result["metrics"], result["bnh_metrics"]

                c1, c2, c3, c4 = st.columns(4)
                c1.metric("CAGR", f"{m['cagr']:.2f}%", f"{m['cagr'] - b['cagr']:.2f}% vs B&H")
                c2.metric("MDD", f"{m['mdd']:.2f}%", f"{m['mdd'] - b['mdd']:.2f}% vs B&H")
                c3.metric("Sharpe", f"{m['sharpe']:.3f}", f"{m['sharpe'] - b['sharpe']:.3f} vs B&H")
                c4.metric("Total Return", f"{m['total_return']:.2f}%")

                st.line_chart(
                    pd.DataFrame({"Strategy": result["equity"], "Buy & Hold": result["bnh_equity"]}),
                    use_container_width=True,
                )

                rc1, rc2 = st.columns(2)
                with rc1:
                    st.markdown("**Regime Distribution**")
                    counts = result["regime"].value_counts().reset_index()
                    counts.columns = ["Regime", "Days"]
                    counts["Regime"] = counts["Regime"].astype(str).str.split(".").str[-1]
                    counts["%"] = (counts["Days"] / counts["Days"].sum() * 100).round(1)
                    st.dataframe(counts, use_container_width=True, hide_index=True)

                with rc2:
                    st.markdown("**Strategy Allocation**")
                    alloc = result["active_strategy"].value_counts().reset_index()
                    alloc.columns = ["Strategy", "Days"]
                    alloc["%"] = (alloc["Days"] / alloc["Days"].sum() * 100).round(1)
                    st.dataframe(alloc, use_container_width=True, hide_index=True)

                latest = result["regime"].dropna().iloc[-1]
                st.info(f"Today's Regime ({df.index[-1].date()}): {str(latest).split('.')[-1]}")
        else:
            st.info("파라미터를 설정하고 Run Backtest를 클릭하세요.")


# ──────────────────────────────────────────────
# Tab 3 · Walk-Forward
# ──────────────────────────────────────────────
with tab3:
    st.caption(
        f"선택 기간을 Train / Test로 나누어 파라미터를 최적화하고, "
        f"미래 데이터에서 실제 성과를 검증합니다.  "
        f"대상: {ticker}  /  기간: {start_date} ~ {end_date}"
    )
    st.divider()

    col_l, col_r = st.columns([1, 3])

    with col_l:
        with st.container(border=True):
            st.markdown("**Train / Test Split**")
            train_pct = st.slider("Train %", 10, 90, 80, 5)
            test_pct = 100 - train_pct

            split_days = int(total_days * train_pct / 100)
            split_date = (pd.Timestamp(start_date) + pd.Timedelta(days=split_days)).date()
            train_days = (pd.Timestamp(split_date) - pd.Timestamp(start_date)).days
            test_days = (pd.Timestamp(end_date) - pd.Timestamp(split_date)).days

            st.caption(
                f"Train {train_pct}%  {start_date} ~ {split_date}  ({train_days}d)\n\n"
                f"Test  {test_pct}%   {split_date} ~ {end_date}  ({test_days}d)"
            )

            st.markdown("**Rolling WFA**")
            fold_test_pct = st.slider("Fold test %", 5, 40, 20, 5)
            fold_test_days = max(int(total_days * fold_test_pct / 100), 30)
            fold_train_days = max(int(total_days * (100 - fold_test_pct) / 100), 60)
            st.caption(f"Fold — train {fold_train_days}d / test {fold_test_days}d")

        wfa_btn = st.button("Run WFA", type="primary", use_container_width=True)

    with col_r:
        if wfa_btn:
            with st.spinner("Optimizing — this may take a minute…"):
                df = load(ticker)
                df = df[(df.index >= pd.Timestamp(start_date)) & (df.index <= pd.Timestamp(end_date))]

            if len(df) < 60:
                st.error("데이터가 부족합니다. 기간을 늘려주세요.")
            else:
                train_df = df[df.index < pd.Timestamp(split_date)]
                test_df = df[df.index >= pd.Timestamp(split_date)]

                if len(train_df) > 30 and len(test_df) > 10:
                    best = optimize(train_df)
                    train_r = switcher_run(train_df, **best)
                    test_r = switcher_run(test_df, **best)
                    bnh_test = summary(
                        (1 + test_df["Close"].pct_change().fillna(0)).cumprod(),
                        test_df["Close"].pct_change().fillna(0),
                    )

                    st.markdown(f"**Single Split** — k={best['k']}  /  adx_bull={best['adx_bull']}")
                    sc1, sc2, sc3, sc4 = st.columns(4)
                    sc1.metric("Train CAGR", f"{train_r['metrics']['cagr']:.2f}%")
                    sc2.metric("Train Sharpe", f"{train_r['metrics']['sharpe']:.3f}")
                    sc3.metric("Test CAGR", f"{test_r['metrics']['cagr']:.2f}%", f"B&H {bnh_test['cagr']:.2f}%")
                    sc4.metric("Test Sharpe", f"{test_r['metrics']['sharpe']:.3f}", f"B&H {bnh_test['sharpe']:.3f}")

                    st.line_chart(
                        pd.DataFrame(
                            {
                                "Train (IS)": train_r["equity"],
                                "Test (OOS)": test_r["equity"] * train_r["equity"].iloc[-1],
                                "B&H": (1 + df["Close"].pct_change().fillna(0)).cumprod(),
                            }
                        ),
                        use_container_width=True,
                    )

                st.divider()

                folds = walk_forward(
                    df,
                    train_years=max(int(fold_train_days / 365), 1),
                    test_years=max(int(fold_test_days / 365), 1),
                )

                if not folds:
                    st.warning("기간이 짧아 롤링 WFA를 실행할 수 없습니다. 기간을 늘려주세요.")
                else:
                    oos_eq, oos_ret = stitch_oos(folds)
                    oos_m = summary(oos_eq, oos_ret)

                    st.markdown(f"**Rolling Walk-Forward — {len(folds)} folds**")
                    wc1, wc2, wc3 = st.columns(3)
                    wc1.metric("OOS CAGR", f"{oos_m['cagr']:.2f}%")
                    wc2.metric("OOS MDD", f"{oos_m['mdd']:.2f}%")
                    wc3.metric("OOS Sharpe", f"{oos_m['sharpe']:.3f}")

                    fold_rows = [
                        {
                            "Fold": i,
                            "Test Period": f"{f['test_start'].date()} ~ {f['test_end'].date()}",
                            "k": f["best_params"]["k"],
                            "adx_bull": f["best_params"]["adx_bull"],
                            "CAGR (%)": round(f["metrics"]["cagr"], 1),
                            "MDD (%)": round(f["metrics"]["mdd"], 1),
                            "Sharpe": round(f["metrics"]["sharpe"], 2),
                        }
                        for i, f in enumerate(folds, 1)
                    ]
                    st.dataframe(pd.DataFrame(fold_rows), use_container_width=True, hide_index=True)
                    st.line_chart(
                        pd.DataFrame({"OOS Stitched": oos_eq}),
                        use_container_width=True,
                    )
        else:
            st.info("Train % 슬라이더로 분할 비율을 설정하고 Run WFA를 클릭하세요.")


# ──────────────────────────────────────────────
# Tab 4 · Data
# ──────────────────────────────────────────────
with tab4:
    st.caption("종목별 가격 데이터 캐시 현황을 확인하고 최신 데이터로 갱신합니다.")
    st.divider()

    if st.button("Refresh All Data", type="primary"):
        with st.spinner("Downloading latest prices…"):
            fetch_all()
        st.success("All tickers updated.")

    raw_dir = Path(__file__).parent.parent / "data" / "raw"
    files = sorted(raw_dir.glob("*.csv"))
    if files:
        rows = []
        for f in files:
            df_info = pd.read_csv(f, index_col=0, parse_dates=True)
            rows.append(
                {
                    "Ticker": f.stem,
                    "Rows": len(df_info),
                    "Start": str(df_info.index.min().date()),
                    "End": str(df_info.index.max().date()),
                }
            )
        st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)
    else:
        st.warning("데이터 파일이 없습니다. Refresh를 클릭하세요.")


# ──────────────────────────────────────────────
# Tab 5 · Paper Portfolio (Live) — 단계 21
# ──────────────────────────────────────────────
with tab5:
    st.caption(
        "실시간 레짐/전략 페이퍼 트레이딩 현황. 착수금 1,000만원, BTC/NYSE 분류, "
        "예상 수수료·건별/누적 손익 포함. 거래내역은 100개씩 페이지네이션."
    )
    st.divider()

    pf = PaperPortfolio()
    prices = _live_prices(pf.state["positions"])
    s = pf.summary(prices)

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("TOTAL", f"{s['total_value']:,.0f} KRW", f"{s['total_return_pct']:+.2f}%")
    c2.metric("현금 (Cash)", f"{s['cash']:,.0f}")
    c3.metric("평가액 (Holdings)", f"{s['holdings_value']:,.0f}")
    c4.metric("실현/평가 손익", f"{s['realized_pnl']:,.0f} / {s['unrealized_pnl']:,.0f}")

    st.markdown("**분류별 (BTC / NYSE)**")
    if s["by_category"]:
        cat_rows = [
            {
                "분류": cat,
                "평가액": round(v["holdings_value"], 0),
                "평가손익": round(v["unrealized_pnl"], 0),
            }
            for cat, v in s["by_category"].items()
        ]
        st.dataframe(pd.DataFrame(cat_rows), use_container_width=True, hide_index=True)
    else:
        st.info("보유 포지션 없음 (관망 중).")

    st.divider()
    st.subheader("거래내역 (Trade History)")
    all_trades = PaperPortfolio.load_trades()
    if all_trades.empty:
        st.info("거래 내역이 없습니다.")
    else:
        total = len(all_trades)
        total_pages = max(1, (total + 99) // 100)
        page = 1
        if total_pages > 1:
            page = st.number_input(
                f"페이지 (전체 {total}건 / {total_pages}페이지, 100건씩)",
                min_value=1,
                max_value=total_pages,
                value=1,
                step=1,
            )
        result = PaperPortfolio.trades_page(page=int(page), page_size=100)
        st.dataframe(pd.DataFrame(result["trades"]), use_container_width=True, hide_index=True)
