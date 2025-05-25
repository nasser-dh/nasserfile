import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt

st.set_page_config(page_title="Stock & Crypto Analyzer", layout="centered")

st.title("📈 US Stock & Crypto Analyzer with Risk/Return Profile")

symbol = st.text_input("Enter a US stock or crypto symbol (e.g. AAPL, MSFT, TSLA, BTC-USD, ETH-USD):", "")

def analyze_symbol(symbol):
    data = yf.Ticker(symbol).history(period='6mo', interval='1d')
    if data.empty:
        st.warning("No data found for this symbol.")
        return

    # Calculate moving averages
    data["SMA_10"] = data["Close"].rolling(window=10).mean()
    data["SMA_30"] = data["Close"].rolling(window=30).mean()
    data["Vol_SMA_10"] = data["Volume"].rolling(window=10).mean()
    data["Vol_SMA_30"] = data["Volume"].rolling(window=30).mean()

    # Trend analysis
    if data["SMA_10"].iloc[-1] > data["SMA_30"].iloc[-1]:
        trend = "Uptrend"
    elif data["SMA_10"].iloc[-1] < data["SMA_30"].iloc[-1]:
        trend = "Downtrend"
    else:
        trend = "Sideways"

    # Volume analysis
    if data["Vol_SMA_10"].iloc[-1] > data["Vol_SMA_30"].iloc[-1]:
        vol_trend = "Rising Volume"
    else:
        vol_trend = "Declining/Stable Volume"

    # Volatility / Risk Analysis
    data['Returns'] = data['Close'].pct_change()
    vol = data['Returns'].std() * np.sqrt(252)  # Annualized volatility
    # Typical guide: low <0.2, medium 0.2-0.4, high >0.4
    if vol < 0.2:
        risk_level = "🟢 Low Risk"
        profile = "Historic price swings are small. Typically, this asset is considered stable; potential gains and losses are moderate."
    elif vol < 0.4:
        risk_level = "🟡 Medium Risk"
        profile = "Some volatility—price changes can be moderate to large. Moderate potential return, with possibility of some losses."
    else:
        risk_level = "🔴 High Risk"
        profile = "Highly volatile: price moves are often large, both up and down. Potential for high profit and high loss. Suitable for aggressive risk-takers."

    expected_return = data['Returns'].mean() * 252  # Annualized expected return

    # Summaries
    st.write(f"**Trend:** {trend}")
    st.write(f"**Volume Trend:** {vol_trend}")
    st.write(f"**Risk/Return Profile:** {risk_level}")
    st.write(profile)
    st.write(f"**Historical annualized volatility:** {vol:.2f}")
    st.write(f"**Historical annualized expected return:** {100*expected_return:.2f}%")

    # Plots
    st.subheader("Charts")
    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(8,8), sharex=True)
    data[["Close", "SMA_10", "SMA_30"]].plot(ax=ax1)
    ax1.set_ylabel("Price")
    ax1.set_title("Price & Moving Averages")
    data[["Volume", "Vol_SMA_10", "Vol_SMA_30"]].plot(ax=ax2)
    ax2.set_ylabel("Volume")
    ax2.set_title("Volume & Volume Moving Averages")
    plt.tight_layout()
    st.pyplot(fig)

if symbol:
    analyze_symbol(symbol)
