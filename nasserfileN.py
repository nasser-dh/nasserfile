import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
import math
import plotly.graph_objs as go

st.set_page_config(page_title="Advanced Stock & Crypto Analyzer", layout="centered")
st.title("📈 Advanced Trend & Risk Analyzer with Targets")

symbol = st.text_input(
    "Enter symbol (US stock/crypto, e.g. AAPL, MSFT, TSLA, BTC-USD):"
)
risk_mode = st.selectbox("Select Risk Level", ["Low", "Medium", "High"])

# —— NEW: strategy picker ——
strategy = st.radio(
    "Choose Strategy",
    ["Very Fast Trade (<1h)", "Fast Trade (today)", "Long-Term Hold"]
)

# If long term, let user pick months ≥6
months = None
if strategy == "Long-Term Hold":
    months = st.slider(
        "Hold Period (months)", min_value=6, max_value=120, value=12,
        help="Choose how many months you plan to hold"
    )

def detect_pattern(df):
    patterns = []
    last, curr = df.iloc[-2], df.iloc[-1]
    # Bullish Engulfing
    if (last.Close < last.Open and
        curr.Close > curr.Open and
        curr.Close > last.Open and
        curr.Open < last.Close):
        patterns.append("Bullish Engulfing")
    # Bearish Engulfing
    if (last.Close > last.Open and
        curr.Close < curr.Open and
        curr.Close < last.Open and
        curr.Open > last.Close):
        patterns.append("Bearish Engulfing")
    # Hammer
    if (curr.Close > curr.Open and
        curr.Low < curr.Open - (curr.High - curr.Low) * 0.6):
        patterns.append("Hammer")
    # Doji
    if abs(curr.Open - curr.Close) < (curr.High - curr.Low) * 0.1:
        patterns.append("Doji")
    return patterns

def compute_rsi(series, window=14):
    delta = series.diff()
    gain = delta.clip(lower=0)
    loss = -delta.clip(upper=0)
    avg_gain = gain.rolling(window).mean()
    avg_loss = loss.rolling(window).mean()
    rs = avg_gain / avg_loss
    return 100 - (100 / (1 + rs))

def analyze_symbol(symbol, risk_mode, strategy, months=None):
    # —— fetch data depending on strategy ——
    if strategy == "Very Fast Trade (<1h)":
        # sub-hour intraday data (5-min bars)
        df = yf.Ticker(symbol).history(period='1d', interval='5m')
    else:
        # daily for both Fast Trade and Long-Term
        df = yf.Ticker(symbol).history(period='6mo', interval='1d')

    if df.empty:
        st.warning("No data found for this symbol.")
        return
    df.dropna(inplace=True)

    # common calculations
    df["MA_10"] = df.Close.rolling(10).mean()
    df["MA_30"] = df.Close.rolling(30).mean()
    df['H-L']   = df.High - df.Low
    df['ATR']   = df['H-L'].rolling(14).mean()
    df['RSI_14']= compute_rsi(df.Close)

    close   = df.Close.iloc[-1]
    atr     = df.ATR.iloc[-1]
    rsi     = df.RSI_14.iloc[-1]
    mult    = {"Low":1.2,"Medium":1.7,"High":2.4}[risk_mode]
    trend   = (
        "Uptrend"   if df.MA_10.iloc[-1] > df.MA_30.iloc[-1]
        else "Downtrend" if df.MA_10.iloc[-1] < df.MA_30.iloc[-1]
        else "Sideways"
    )
    patterns= detect_pattern(df)
    bullish = any(p in patterns for p in ["Bullish Engulfing","Hammer"])
    bearish = any(p in patterns for p in ["Bearish Engulfing"])

    # —— risk-distance scaling —— 
    if strategy == "Very Fast Trade (<1h)":
        # one 5-min bar horizon
        risk_dist = mult * atr
    elif strategy == "Fast Trade (today)":
        # daily ATR → 1 trading day
        risk_dist = mult * atr * math.sqrt(1)
    else:  # Long-Term Hold
        days = months * 21  # approx trading days
        risk_dist = mult * atr * math.sqrt(days)

    # decide action & stops/targets
    if (trend=="Uptrend" or bullish) and not bearish:
        action = "Buy / Go Long"
        stop_loss    = close - risk_dist
        target_price = close + risk_dist
    elif (trend=="Downtrend" or bearish) and not bullish:
        action = "Sell / Go Short"
        stop_loss    = close + risk_dist
        target_price = close - risk_dist
    else:
        action = "Neutral / Wait"
        stop_loss    = close - 0.9*risk_dist
        target_price = close + 0.9*risk_dist

    rr_ratio = abs((target_price - close) / (close - stop_loss))

    # —— build chart —— 
    fig = go.Figure(data=[go.Candlestick(
        x=df.index, open=df.Open, high=df.High, low=df.Low, close=df.Close
    )])
    fig.add_hline(y=target_price, line_color="green", annotation_text="Target")
    fig.add_hline(y=stop_loss,    line_color="red",   annotation_text="Stop")
    fig.add_trace(go.Scatter(
        x=df.index, y=df.RSI_14, yaxis="y2", name="RSI(14)"
    ))
    fig.update_layout(
        title=(
            f"{symbol} | {trend} | {strategy}"
            + (f" ({months} mo)" if strategy=="Long-Term Hold" else "")
        ),
        yaxis2=dict(overlaying="y", side="right", range=[0,100], title="RSI"),
        xaxis_rangeslider_visible=False,
        height=650
    )

    st.subheader("Candlestick + RSI Chart")
    st.plotly_chart(fig, use_container_width=True)

    st.markdown(f"""
    **Strategy:** {strategy}  
    {f"**Hold Period:** {months} months  " if strategy=="Long-Term Hold" else ""}  
    **Trend:** {trend}  
    **Patterns:** {', '.join(patterns) or 'None'}  
    **Action:** {action}  
    **Entry:** {close:.2f}  
    **Target:** {target_price:.2f}  
    **Stop Loss:** {stop_loss:.2f}  
    **R/R Ratio:** {rr_ratio:.2f}  
    **RSI(14):** {rsi:.1f}  
    **ATR:** {atr:.2f}  
    _Risk mult: {mult}, time-scale factor: {"1 bar" if strategy.startswith("Very Fast") else ("1 day" if strategy=="Fast Trade (today)" else f"{days} days (√)")}_
    """)

if symbol:
    analyze_symbol(symbol, risk_mode, strategy, months)
