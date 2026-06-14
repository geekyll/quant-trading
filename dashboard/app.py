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

st.set_page_config(page_title="Quant Trading Dashboard", layout="wide")
st.title("Quant Trading Dashboard")

TICKERS = [a.ticker for a in UNIVERSE]
REGIME_COLOR = {
    "Regime.BULL": "#2ca02c",
    "Regime.SIDEWAYS_UP": "#1f77b4",
    "Regime.BEAR": "#d62728",
    "Regime.SIDEWAYS_DOWN": "#ff7f0e",
}

tab1, tab2, tab3, tab4 = st.tabs(["Signals & Portfolio", "Regime Backtest", "Walk-Forward", "Data"])


# ──────────────────────────────────────────────
# Tab 1 : Signals & Portfolio
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
# Tab 2 : Regime-Adaptive Backtest
# ──────────────────────────────────────────────
with tab2:
    st.subheader("Regime-Adaptive Strategy Backtest")

    col_l, col_r = st.columns([1, 3])

    with col_l:
        ticker = st.selectbox("Ticker", TICKERS, key="bt_ticker")
        start_date = st.date_input("Start date", value=pd.Timestamp("2025-01-01"))
        end_date = st.date_input("End date", value=pd.Timestamp.today())
        st.markdown("**Parameters**")
        k = st.slider("k (VB strength)", 0.3, 0.7, 0.5, 0.1)
        adx_bull = st.slider("adx_bull", 15, 40, 25, 5)
        adx_side = st.slider("adx_side", 10, 35, 20, 5)
        run_btn = st.button("Run Backtest", type="primary")

    with col_r:
        if run_btn:
            with st.spinner("Running..."):
                df = load(ticker)
                df = df[(df.index >= pd.Timestamp(start_date)) & (df.index <= pd.Timestamp(end_date))]

                if len(df) < 30:
                    st.error("Not enough data. Adjust the date range.")
                else:
                    result = switcher_run(df, k=k, adx_bull=adx_bull, adx_side=adx_side)
                    m = result["metrics"]
                    b = result["bnh_metrics"]

                    # metrics
                    c1, c2, c3, c4 = st.columns(4)
                    c1.metric("Strategy CAGR", f"{m['cagr']:.2f}%", f"{m['cagr'] - b['cagr']:.2f}% vs B&H")
                    c2.metric("Strategy MDD", f"{m['mdd']:.2f}%", f"{m['mdd'] - b['mdd']:.2f}% vs B&H")
                    c3.metric("Sharpe Ratio", f"{m['sharpe']:.3f}", f"{m['sharpe'] - b['sharpe']:.3f} vs B&H")
                    c4.metric("Total Return", f"{m['total_return']:.2f}%")

                    # equity chart
                    eq_df = pd.DataFrame(
                        {
                            "Strategy": result["equity"],
                            "Buy & Hold": result["bnh_equity"],
                        }
                    )
                    st.line_chart(eq_df, use_container_width=True)

                    # regime & strategy allocation
                    rc1, rc2 = st.columns(2)

                    with rc1:
                        st.markdown("**Regime Distribution**")
                        counts = result["regime"].value_counts().reset_index()
                        counts.columns = ["Regime", "Days"]
                        counts["Regime"] = counts["Regime"].astype(str)
                        counts["%"] = (counts["Days"] / counts["Days"].sum() * 100).round(1)
                        st.dataframe(counts, use_container_width=True, hide_index=True)

                    with rc2:
                        st.markdown("**Strategy Allocation**")
                        alloc = result["active_strategy"].value_counts().reset_index()
                        alloc.columns = ["Strategy", "Days"]
                        alloc["%"] = (alloc["Days"] / alloc["Days"].sum() * 100).round(1)
                        st.dataframe(alloc, use_container_width=True, hide_index=True)

                    # current regime
                    latest_regime = result["regime"].dropna().iloc[-1]
                    st.info(f"**Current Regime ({df.index[-1].date()}):** {str(latest_regime).split('.')[-1]}")
        else:
            st.info("Set parameters on the left and click **Run Backtest**.")


# ──────────────────────────────────────────────
# Tab 3 : Walk-Forward Analysis
# ──────────────────────────────────────────────
with tab3:
    st.subheader("Walk-Forward Analysis")

    col_l, col_r = st.columns([1, 3])

    with col_l:
        wfa_ticker = st.selectbox("Ticker", TICKERS, key="wfa_ticker")
        wfa_start = st.date_input("Start date", value=pd.Timestamp("2018-01-01"), key="wfa_start")
        wfa_end = st.date_input("End date", value=pd.Timestamp.today(), key="wfa_end")
        train_years = st.slider("Train years", 1, 5, 3)
        test_years = st.slider("Test years", 1, 2, 1)
        split_date_str = st.date_input("Simple split date", value=pd.Timestamp("2024-01-01"))
        wfa_btn = st.button("Run WFA", type="primary")

    with col_r:
        if wfa_btn:
            with st.spinner("Optimizing folds... this may take a minute."):
                df = load(wfa_ticker)
                df = df[(df.index >= pd.Timestamp(wfa_start)) & (df.index <= pd.Timestamp(wfa_end))]

                if len(df) < 200:
                    st.error("Not enough data.")
                else:
                    # simple split
                    split_date = str(split_date_str)
                    train_df = df[df.index < split_date]
                    test_df = df[df.index >= split_date]

                    if len(train_df) > 50 and len(test_df) > 10:
                        best = optimize(train_df)
                        train_r = switcher_run(train_df, **best)
                        test_r = switcher_run(test_df, **best)
                        bnh_test = summary(
                            (1 + test_df["Close"].pct_change().fillna(0)).cumprod(),
                            test_df["Close"].pct_change().fillna(0),
                        )

                        st.markdown(f"**Simple Split** — best params: k={best['k']}, adx_bull={best['adx_bull']}")
                        sc1, sc2, sc3 = st.columns(3)
                        sc1.metric("Train CAGR", f"{train_r['metrics']['cagr']:.2f}%")
                        sc2.metric("Test CAGR", f"{test_r['metrics']['cagr']:.2f}%", f"B&H {bnh_test['cagr']:.2f}%")
                        sc3.metric("Test Sharpe", f"{test_r['metrics']['sharpe']:.3f}", f"B&H {bnh_test['sharpe']:.3f}")

                        split_eq = pd.DataFrame(
                            {
                                "Train (IS)": train_r["equity"],
                                "Test (OOS)": test_r["equity"] * train_r["equity"].iloc[-1],
                                "B&H": (1 + df["Close"].pct_change().fillna(0)).cumprod(),
                            }
                        )
                        st.line_chart(split_eq, use_container_width=True)

                    st.divider()

                    # walk-forward
                    folds = walk_forward(df, train_years=train_years, test_years=test_years)
                    if not folds:
                        st.warning("Not enough data for rolling WFA with these settings.")
                    else:
                        oos_eq, oos_ret = stitch_oos(folds)
                        oos_m = summary(oos_eq, oos_ret)

                        st.markdown(f"**Walk-Forward OOS ({len(folds)} folds)**")
                        wc1, wc2, wc3 = st.columns(3)
                        wc1.metric("OOS CAGR", f"{oos_m['cagr']:.2f}%")
                        wc2.metric("OOS MDD", f"{oos_m['mdd']:.2f}%")
                        wc3.metric("OOS Sharpe", f"{oos_m['sharpe']:.3f}")

                        fold_rows = []
                        for i, f in enumerate(folds, 1):
                            fold_rows.append(
                                {
                                    "Fold": i,
                                    "Test Period": f"{f['test_start'].date()} ~ {f['test_end'].date()}",
                                    "k": f["best_params"]["k"],
                                    "adx_bull": f["best_params"]["adx_bull"],
                                    "CAGR (%)": round(f["metrics"]["cagr"], 1),
                                    "MDD (%)": round(f["metrics"]["mdd"], 1),
                                    "Sharpe": round(f["metrics"]["sharpe"], 2),
                                }
                            )
                        st.dataframe(pd.DataFrame(fold_rows), use_container_width=True, hide_index=True)

                        oos_chart = pd.DataFrame({"OOS Stitched": oos_eq})
                        st.line_chart(oos_chart, use_container_width=True)
        else:
            st.info("Set parameters on the left and click **Run WFA**.")


# ──────────────────────────────────────────────
# Tab 4 : Data
# ──────────────────────────────────────────────
with tab4:
    st.subheader("Data Management")

    if st.button("Refresh All Data (fetch latest)", type="primary"):
        with st.spinner("Downloading..."):
            fetch_all()
        st.success("Done.")

    st.markdown("**Available data files**")
    raw_dir = Path(__file__).parent.parent / "data" / "raw"
    files = sorted(raw_dir.glob("*.csv"))
    if files:
        rows = []
        for f in files:
            df = pd.read_csv(f, index_col=0, parse_dates=True)
            rows.append(
                {
                    "Ticker": f.stem,
                    "Rows": len(df),
                    "Start": df.index.min().date(),
                    "End": df.index.max().date(),
                    "File": f.name,
                }
            )
        st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)
    else:
        st.warning("No data files found. Click Refresh above.")
