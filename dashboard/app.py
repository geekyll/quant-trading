import sys
from pathlib import Path

import pandas as pd
import streamlit as st

sys.path.insert(0, str(Path(__file__).parent.parent))

from backtest.engine import run as backtest_run
from backtest.paper_trade import _load_portfolio, get_portfolio_value, load_trades
from data.collector import load
from data.universe import UNIVERSE
from strategy.signals import current_signals

st.set_page_config(page_title="Quant Trading Dashboard", layout="wide")
st.title("Quant Trading Dashboard")

# --- sidebar ---
st.sidebar.header("Settings")
selected_ticker = st.sidebar.selectbox("Ticker", [a.ticker for a in UNIVERSE])
sma_period = st.sidebar.selectbox("SMA Period", [20, 50, 100, 200], index=3)

# --- signals ---
st.header("Current Signals")
signals = current_signals(sma_period)
sig_df = pd.DataFrame(signals)
sig_df["signal"] = sig_df["signal"].map(lambda x: f"🟢 {x}" if x == "BUY" else f"🔴 {x}")
st.dataframe(sig_df, use_container_width=True, hide_index=True)

# --- portfolio ---
st.header("Paper Portfolio")
p = _load_portfolio()
col1, col2, col3 = st.columns(3)
col1.metric("Total Value", f"${get_portfolio_value(p):,.2f}")
col2.metric("Cash", f"${p['cash']:,.2f}")
col3.metric("Open Positions", len(p["positions"]))

trades_df = load_trades()
if not trades_df.empty:
    st.subheader("Trade Log")
    st.dataframe(trades_df.tail(20), use_container_width=True, hide_index=True)

# --- backtest ---
st.header(f"Backtest — {selected_ticker}  SMA{sma_period}")
df = load(selected_ticker)
result = backtest_run(df, sma_period)

s, b = result["strategy"], result["buy_and_hold"]
c1, c2, c3, c4 = st.columns(4)
c1.metric("Strategy CAGR", f"{s['cagr']}%", f"{s['cagr'] - b['cagr']:.2f}% vs B&H")
c2.metric("Strategy MDD", f"{s['mdd']}%", f"{s['mdd'] - b['mdd']:.2f}% vs B&H")
c3.metric("Sharpe Ratio", s["sharpe"])
c4.metric("Total Return", f"{s['total_return']}%")

equity_df = pd.DataFrame({"Strategy": result["strat_equity"], "Buy & Hold": result["bnh_equity"]})
st.line_chart(equity_df)

# --- drawdown ---
st.subheader("Drawdown")
strat_eq = result["strat_equity"]
drawdown = (strat_eq - strat_eq.cummax()) / strat_eq.cummax() * 100
st.area_chart(drawdown.rename("Drawdown (%)"))
