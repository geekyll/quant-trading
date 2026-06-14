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
from strategy.signals import current_signals
from strategy.switcher import run as switcher_run

st.set_page_config(page_title="Quant Trading Dashboard", page_icon="📈", layout="wide")

TICKERS = [a.ticker for a in UNIVERSE]
TODAY = pd.Timestamp.today().normalize()

PRESETS = [
    ("1M", 1, "Past 1 Month"),
    ("3M", 3, "Past 3 Months"),
    ("6M", 6, "Past 6 Months"),
    ("1Y", 12, "Past 1 Year"),
    ("2Y", 24, "Past 2 Years"),
    ("3Y", 36, "Past 3 Years"),
]

if "start_date" not in st.session_state:
    st.session_state["start_date"] = (TODAY - pd.DateOffset(months=12)).date()
if "end_date" not in st.session_state:
    st.session_state["end_date"] = TODAY.date()
if "range_label" not in st.session_state:
    st.session_state["range_label"] = "Past 1 Year"
if "show_custom" not in st.session_state:
    st.session_state["show_custom"] = False


# ──────────────────────────────────────────────
# Top bar — title / ticker / time picker
# ──────────────────────────────────────────────
col_title, col_ticker, col_range = st.columns([2, 1, 2])

with col_title:
    st.markdown("### 📈 Quant Trading Dashboard")

with col_ticker:
    ticker = st.selectbox("ticker", TICKERS, label_visibility="collapsed")

with col_range:
    s = st.session_state["start_date"]
    e = st.session_state["end_date"]
    lbl = st.session_state["range_label"]

    with st.popover(f"📅  {lbl}  ·  {s} ~ {e}", use_container_width=True):
        # preset list
        active = st.session_state["range_label"]
        for key, months, desc in PRESETS:
            is_active = active == desc
            label_str = f"**{key}** &nbsp; {desc}" if is_active else f"{key} &nbsp; {desc}"
            if st.button(label_str, key=f"preset_{key}", use_container_width=True):
                st.session_state["start_date"] = (TODAY - pd.DateOffset(months=months)).date()
                st.session_state["end_date"] = TODAY.date()
                st.session_state["range_label"] = desc
                st.session_state["show_custom"] = False
                st.rerun()

        st.divider()

        # custom range toggle
        if st.button("📅  Custom range…", use_container_width=True, key="btn_custom"):
            st.session_state["show_custom"] = not st.session_state["show_custom"]

        if st.session_state["show_custom"]:
            c_s = st.date_input("Start", value=st.session_state["start_date"], key="cs")
            c_e = st.date_input("End", value=st.session_state["end_date"], key="ce")
            if st.button("Apply", type="primary", use_container_width=True, key="apply_custom"):
                st.session_state["start_date"] = c_s
                st.session_state["end_date"] = c_e
                st.session_state["range_label"] = f"{c_s} ~ {c_e}"
                st.session_state["show_custom"] = False
                st.rerun()

start_date = st.session_state["start_date"]
end_date = st.session_state["end_date"]
total_days = max((pd.Timestamp(end_date) - pd.Timestamp(start_date)).days, 1)

st.divider()


# ──────────────────────────────────────────────
# Tabs
# ──────────────────────────────────────────────
tab1, tab2, tab3, tab4 = st.tabs(
    [
        "📊  Signals & Portfolio",
        "🔄  Regime Backtest",
        "📈  Walk-Forward",
        "🗄️  Data",
    ]
)


# ──────────────────────────────────────────────
# Tab 1 · Signals & Portfolio
# ──────────────────────────────────────────────
with tab1:
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
        st.subheader("Trade Log (last 20)")
        st.dataframe(trades_df.tail(20), use_container_width=True, hide_index=True)


# ──────────────────────────────────────────────
# Tab 2 · Regime-Adaptive Backtest
# ──────────────────────────────────────────────
with tab2:
    st.subheader(f"Regime-Adaptive Backtest  ·  {ticker}  ·  {start_date} ~ {end_date}")
    st.caption("BULL → Volatility Breakout  /  SIDEWAYS_UP → Grid  /  BEAR & SIDEWAYS_DOWN → Cash")
    st.divider()

    col_l, col_r = st.columns([1, 3], gap="large")

    with col_l:
        with st.container(border=True):
            st.markdown("**Strategy Parameters**")
            k = st.slider("k  (Volatility Breakout)", 0.3, 0.7, 0.5, 0.1)
            adx_bull = st.slider("ADX Bull threshold", 15, 40, 25, 5)
            adx_side = st.slider("ADX Side threshold", 10, 35, 20, 5)
            st.caption(f"BULL if ADX > {adx_bull}  ·  SIDEWAYS if ADX < {adx_side}")
        run_btn = st.button("▶  Run Backtest", type="primary", use_container_width=True)

    with col_r:
        if run_btn:
            with st.spinner("Running…"):
                df = load(ticker)
                df = df[(df.index >= pd.Timestamp(start_date)) & (df.index <= pd.Timestamp(end_date))]

            if len(df) < 30:
                st.error("Not enough data — adjust the time range.")
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

                rc1, rc2 = st.columns(2, gap="medium")
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
                st.info(f"**Today's Regime ({df.index[-1].date()}):** {str(latest).split('.')[-1]}")
        else:
            st.info("Set parameters on the left and click **▶ Run Backtest**.")


# ──────────────────────────────────────────────
# Tab 3 · Walk-Forward Analysis
# ──────────────────────────────────────────────
with tab3:
    st.subheader(f"Walk-Forward Analysis  ·  {ticker}  ·  {start_date} ~ {end_date}")
    st.caption("Optimize parameters on train set → validate on unseen test set, rolling across time")
    st.divider()

    col_l, col_r = st.columns([1, 3], gap="large")

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
                f"Train {train_pct}%  →  {start_date} ~ {split_date}  ({train_days}d)\n\n"
                f"Test  {test_pct}%  →  {split_date} ~ {end_date}  ({test_days}d)"
            )

            st.markdown("**Rolling WFA window**")
            fold_test_pct = st.slider("Fold test window %", 5, 40, 20, 5)
            fold_train_pct = 100 - fold_test_pct
            fold_test_days = max(int(total_days * fold_test_pct / 100), 30)
            fold_train_days = max(int(total_days * fold_train_pct / 100), 60)
            st.caption(f"Each fold — train {fold_train_days}d / test {fold_test_days}d")

        wfa_btn = st.button("▶  Run WFA", type="primary", use_container_width=True)

    with col_r:
        if wfa_btn:
            with st.spinner("Optimizing folds — this may take a minute…"):
                df = load(ticker)
                df = df[(df.index >= pd.Timestamp(start_date)) & (df.index <= pd.Timestamp(end_date))]

            if len(df) < 60:
                st.error("Not enough data — use a longer time range.")
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

                    st.markdown(f"**Single Split** — best params: k = {best['k']}  ·  adx_bull = {best['adx_bull']}")
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

                # rolling WFA in calendar days
                train_yrs = max(round(fold_train_days / 365, 1), 0.5)
                test_yrs = max(round(fold_test_days / 365, 1), 0.25)
                folds = walk_forward(
                    df,
                    train_years=int(max(train_yrs, 1)),
                    test_years=int(max(test_yrs, 1)),
                )

                if not folds:
                    st.warning("Not enough data for rolling WFA — try a longer time range or smaller fold windows.")
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
                    st.line_chart(pd.DataFrame({"OOS Stitched": oos_eq}), use_container_width=True)
        else:
            st.info("Set the train/test split on the left and click **▶ Run WFA**.")


# ──────────────────────────────────────────────
# Tab 4 · Data
# ──────────────────────────────────────────────
with tab4:
    st.subheader("Data Management")

    if st.button("🔄  Refresh All Data", type="primary"):
        with st.spinner("Downloading latest prices…"):
            fetch_all()
        st.success("All tickers updated.")

    st.divider()
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
        st.warning("No data files found. Click Refresh above.")
