# dashboard.py
import streamlit as st
import vectorbtpro as vbt
import plotly.graph_objects as go
import pandas as pd

# -------------------------------
# CryptoGraph styling (purple)
# -------------------------------
st.markdown("""
<style>
[data-testid="stAppViewContainer"] {
  background-color: #0d0b1e;
  background-image: linear-gradient(180deg, #0d0b1e 0%, #1b153a 100%);
  color: #EDEBFF;
}
[data-testid="stSidebar"] { background-color: #141129; color: #EDEBFF; }
[data-testid="stSidebar"] h2 { color: #7B61FF !important; }
h1, h2, h3, h4, h5 { color: #B8A4FF; font-weight: 600; }
[data-testid="stMetricValue"] { color: #7B61FF; }
[data-testid="stMetricLabel"] { color: #C8C8D8; }
hr { border: none; border-top: 1px solid #2f295f; margin: 1.2rem 0; }
[data-testid="stDataFrame"] { background-color: #181532; color: #EEE; }
footer, .css-164nlkn { color: #7B61FF; }
</style>
""", unsafe_allow_html=True)

# -------------------------------
# Page config
# -------------------------------
st.set_page_config(page_title="CryptoGraph Trading Systems", layout="wide")
st.title("Trading Systems Dashboard")

# -------------------------------
# Sidebar
# -------------------------------
st.sidebar.header("Select Strategy")
strategies = ["SAF1", "SAF2", "SAF3"]
selected = st.sidebar.radio("", strategies)

@st.cache_resource
def load_portfolio(name: str):
    path = f"data/{name.lower()}_backtest.pkl"
    return vbt.load(path)

pf = load_portfolio(selected)

# -------------------------------
# Base data
# -------------------------------
trades = pf.trades.records_readable
value = pf.value
returns = value / value.iloc[0] - 1

# Try to get OHLC data
if all(hasattr(pf, attr) for attr in ["open", "high", "low", "close"]):
    ohlc = pd.DataFrame({
        "Open": pf.open,
        "High": pf.high,
        "Low": pf.low,
        "Close": pf.close
    })
elif hasattr(pf, "close"):
    ohlc = pd.DataFrame({"Close": pf.close})
else:
    ohlc = pd.DataFrame({"Close": pf.value})

# -------------------------------
# Tabs
# -------------------------------
tab1, tab2 = st.tabs(["Trading Graphs", "Metrics & Statistics"])

# -------------------------------
# Layout helper
# -------------------------------
def apply_layout(fig, height=340):
    fig.update_layout(
        height=height,
        margin=dict(l=0, r=0, t=40, b=0),
        template="plotly_dark",
        xaxis_rangeslider_visible=False,
        hovermode="x unified",
        uirevision="keep",
        paper_bgcolor="#0d0b1e",
        plot_bgcolor="#0d0b1e",
        font=dict(color="#EDEBFF"),
        legend=dict(bgcolor="rgba(0,0,0,0)")
    )
    fig.update_yaxes(showgrid=True, gridcolor="rgba(255,255,255,0.12)")
    fig.update_xaxes(showgrid=False)
    return fig

# -------------------------------
# TAB 1: Trading Graphs
# -------------------------------
with tab1:
    st.markdown("### Trade Signals")

    fig_price = go.Figure()

    # --- Price as OHLC candles if data available ---
    if set(["Open", "High", "Low", "Close"]).issubset(ohlc.columns):
        fig_price.add_trace(go.Candlestick(
            x=ohlc.index,
            open=ohlc["Open"],
            high=ohlc["High"],
            low=ohlc["Low"],
            close=ohlc["Close"],
            name="Price",
            increasing_line_color="#7B61FF",
            decreasing_line_color="#FF4C4C",
            showlegend=True
        ))
    else:
        fig_price.add_trace(go.Scatter(
            x=ohlc.index,
            y=ohlc["Close"],
            mode="lines",
            name="Close",
            line=dict(width=1.6, color="#7B61FF")
        ))

    # --- Trade markers (GPU accelerated) ---
    has_entry = {"Entry Index", "Avg Entry Price"}.issubset(trades.columns)
    has_exit  = {"Exit Index",  "Avg Exit Price" }.issubset(trades.columns)

    if has_entry or has_exit:
        n = len(trades)
        step = max(1, n // 1200)
        tsub = trades.iloc[::step] if step > 1 else trades

    if has_entry:
        fig_price.add_trace(go.Scattergl(
            x=tsub["Entry Index"],
            y=tsub["Avg Entry Price"],
            mode="markers",
            name="Entry",
            marker=dict(symbol="triangle-up", color="rgba(0,255,0,0.6)", size=6, line=dict(width=0)),
            hovertemplate="Entry<br>%{x}<br>Price: %{y:.2f}<extra></extra>"
        ))

    if has_exit:
        fig_price.add_trace(go.Scattergl(
            x=tsub["Exit Index"],
            y=tsub["Avg Exit Price"],
            mode="markers",
            name="Exit",
            marker=dict(symbol="triangle-down", color="rgba(255,0,0,0.65)", size=6, line=dict(width=0)),
            hovertemplate="Exit<br>%{x}<br>Price: %{y:.2f}<extra></extra>"
        ))

    apply_layout(fig_price, height=360)
    st.plotly_chart(fig_price, use_container_width=True)

    # --- Cumulative Returns ---
    st.divider()
    st.markdown("### Cumulative Returns vs Benchmark")
    fig_returns = pf.plot_cumulative_returns()
    apply_layout(fig_returns, height=340)
    st.plotly_chart(fig_returns, use_container_width=True)

    # --- Drawdowns ---
    st.divider()
    st.markdown("### Drawdowns")
    fig_dd = pf.plot_drawdowns()
    apply_layout(fig_dd, height=340)
    st.plotly_chart(fig_dd, use_container_width=True)

# -------------------------------
# TAB 2: Metrics & Statistics
# -------------------------------
with tab2:
    st.markdown(f"### {selected} Performance Metrics")

    col1, col2, col3 = st.columns(3)
    col1.metric("Total Return", f"{pf.total_return * 100:.2f}%")
    col2.metric("Sharpe Ratio", f"{pf.sharpe_ratio:.2f}")
    col3.metric("Max Drawdown", f"{pf.max_drawdown * 100:.2f}%")

    st.divider()
    st.markdown("#### Full Statistics")
    stats = pf.stats(settings=dict(risk_free_rate=0.0, freq="1D"))
    st.dataframe(stats.T, use_container_width=True)

# -------------------------------
# Footer
# -------------------------------
st.caption("© 2025 CryptoGraph — powered by Vectorbt Pro & Streamlit")
