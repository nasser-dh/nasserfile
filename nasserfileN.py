import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
import plotly.graph_objs as go

st.set_page_config(page_title="Advanced Stock & Crypto Analyzer", layout="centered")
st.title("📈 Advanced Trend & Risk Analyzer with Targets")

symbol = st.text_input("Enter symbol (US stock/crypto, e.g. AAPL, MSFT, TSLA, BTC-USD):")
risk_mode = st.selectbox("Select Risk Level", ["Low", "Medium", "High"])

def detect_pattern(df):
    patterns = []
    last = df.iloc[-2]
    curr = df.iloc[-1]
    # Bullish Engulfing
    if (last['Close'] < last['Open']) and (curr['Close'] > curr['Open']) and (curr['Close'] > last['Open']) and (curr['Open'] < last['Close']):
        patterns.append("Bullish Engulfing")
    # Bearish Engulfing
    if (last['Close'] > last['Open']) and (curr['Close'] < curr['Open']) and (curr['Close'] < last['Open']) and (curr['Open'] > last['Close']):
        patterns.append("Bearish Engulfing")
    # Hammer
    if (curr['Close'] > curr['Open']) and ((curr['Low'] < curr['Open'] - (curr['High'] - curr['Low']) * 0.6)):
        patterns.append("Hammer")
    # Doji
    if (abs(curr['Open'] - curr['Close']) < (curr['High'] - curr['Low']) * 0.1):
        patterns.append("Doji")
    return patterns

def analyze_symbol(symbol, risk_mode):
    try:
        df = yf.Ticker(symbol).history(period='6mo', interval='1d')
        if df.empty:
            st.warning("No data found for this symbol. Double-check the symbol (like AAPL, TSLA, BTC-USD) and try again.")
            return
    except Exception as e:
        st.error(f"⚠️ Could not fetch data for '{symbol}'.\nPossible reasons:\n- Symbol typo or wrong\n- Network/Yahoo block or busy\n- Try a different symbol or wait a little then retry.\n\nTechnical details: {e}")
        return

    df.dropna(inplace=True)

    # Moving averages for trend
    df["MA_10"] = df["Close"].rolling(window=10).mean()
    df["MA_30"] = df["Close"].rolling(window=30).mean()
    
    # Trend direction
    if df["MA_10"].iloc[-1] > df["MA_30"].iloc[-1]:
        trend = "Uptrend"
    elif df["MA_10"].iloc[-1] < df["MA_30"].iloc[-1]:
        trend = "Downtrend"
    else:
        trend = "Sideways"

    # ATR for dynamic stop/target
    df['H-L'] = df['High'] - df['Low']
    df['ATR'] = df['H-L'].rolling(window=14).mean()

    # Risk factor and labels
    mult = {'Low': 1.2, 'Medium': 1.7, 'High': 2.4}[risk_mode]

    # Last price/candle
    close = df["Close"].iloc[-1]
    atr = df["ATR"].iloc[-1]
    support = df["Low"].rolling(window=20).min().iloc[-1]
    resistance = df["High"].rolling(window=20).max().iloc[-1]
    
    # Patterns
    patterns = detect_pattern(df)
    pattern_text = ", ".join(patterns) if patterns else "None detected"
    bullish = any(p in pattern_text for p in ['Hammer', 'Bullish Engulfing'])
    bearish = any(p in pattern_text for p in ['Bearish Engulfing'])
        
    # Target/stop logic (bullish by default or if uptrend)
    if trend == "Uptrend" or bullish:
        stop_loss = close - mult * atr
        target_price = close + mult * atr
        action = "Buy/Go Long"
    elif trend == "Downtrend" or bearish:
        stop_loss = close + mult * atr
        target_price = close - mult * atr
        action = "Sell/Go Short"
    else:
        stop_loss = close - 0.9 * mult * atr
        target_price = close + 0.9 * mult * atr
        action = "Sideway/Wait"

    rr_ratio = abs((target_price - close) / (close - stop_loss)) if stop_loss != close else np.nan
    
    # Plotly candlestick chart with overlays
    fig = go.Figure(data=[go.Candlestick(
        x=df.index,
        open=df['Open'],
        high=df['High'],
        low=df['Low'],
        close=df['Close'],
        name='Candlestick'
    )])
    # Add stop and target lines
    fig.add_hline(y=target_price, line_color="green", annotation_text="Target", annotation_position="top left")
    fig.add_hline(y=stop_loss, line_color="red", annotation_text="Stop Loss", annotation_position="bottom left")
    fig.add_hline(y=close, line_color="blue", annotation_text="Entry", annotation_position="right")
    fig.update_layout(
        title=f"{symbol} | {trend} | Risk: {risk_mode}",
        xaxis_title='Date',
        yaxis_title='Price',
        xaxis_rangeslider_visible=False,
        height=600
    )

    # Results
    st.subheader("Candlestick Chart")
    st.plotly_chart(fig, use_container_width=True)
    st.info(f"**Trend:** {trend}")
    st.info(f"**Pattern(s):** {pattern_text}")
    st.info(f"**Suggested Action:** {action}")
    st.success(f"**Target Price:** {target_price:.2f}")
    st.error(f"**Stop Loss:** {stop_loss:.2f}")
    st.write(f"**Risk/Reward Ratio:** {rr_ratio:.2f}" if not np.isnan(rr_ratio) else "**Risk/Reward Ratio:** N/A")
    st.write(f"**Nearest Support:** {support:.2f}, **Nearest Resistance:** {resistance:.2f}")
    st.write(f"**ATR (volatility):** {atr:.2f}")
    st.write(f"**Last Close:** {close:.2f}")

    # --------- Only one most confident trade direction section ---------
    trade_direction = None
    trade_msg = ""
    if (trend == "Uptrend" or bullish) and not bearish:
        trade_direction = "CALL"
        trade_msg = "📈 The advanced analysis indicates a HIGH CONFIDENCE **CALL (Buy/Long)** opportunity!"
        entry = close
        target = target_price
        stop = stop_loss
        rr = (target - entry) / max(1e-6, (entry - stop))
    elif (trend == "Downtrend" or bearish) and not bullish:
        trade_direction = "PUT"
        trade_msg = "📉 The advanced analysis indicates a HIGH CONFIDENCE **PUT (Sell/Short)** opportunity!"
        entry = close
        target = close - abs(target_price - close)
        stop = close + abs(close - stop_loss)
        rr = (entry - target) / max(1e-6, (stop - entry))
    else:
        trade_direction = "NEUTRAL"

    if trade_direction == "CALL":
        st.success(trade_msg)
        st.write(f"Entry (Buy): {entry:.2f}")
        st.write(f"Target (Sell to take profit): {target:.2f}")
        st.write(f"Stop Loss: {stop:.2f}")
        st.write(f"Risk/Reward ratio: {rr:.2f}")
    elif trade_direction == "PUT":
        st.error(trade_msg)
        st.write(f"Entry (Sell): {entry:.2f}")
        st.write(f"Target (Buy to cover profit): {target:.2f}")
        st.write(f"Stop Loss: {stop:.2f}")
        st.write(f"Risk/Reward ratio: {rr:.2f}")
    else:
        st.info("🤔 No strong trend or clear signal based on advanced analysis (neutral/sideways). No action recommended.")
    # -----------------------------------------------------------------------

    st.markdown("""
    ---  
    _Targets and stops are auto-calculated using ATR, risk setting, and simple chart pattern logic.
    Option-like suggestion: Only the most confident direction is shown based on combined logic.  
    Always check your own analysis before trading!_
    """)

if symbol:
    analyze_symbol(symbol, risk_mode)
