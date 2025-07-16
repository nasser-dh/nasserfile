import streamlit as st
import yfinance as yf
import plotly.graph_objs as go
import requests
import openai
import numpy as np

# ---------- CONFIG ----------
st.set_page_config(page_title="N9 AI Stock & News Analyzer", layout="centered")

# N9 Custom Header
st.markdown("""
<div style='text-align:center; font-size:2.3em; color:#08f26e; font-weight:bold; letter-spacing:2px; margin-bottom: 0.2em;'>
    🚀 Welcome, <span style='color:#FAE90A;'>N9</span>!
</div>
<div style='text-align:center; font-size:1.25em; color:#2682d3; margin-bottom:2em;'>
    Advanced AI-Powered Financial Analyzer & News Reader
</div>
""", unsafe_allow_html=True)

# --- OpenAI API Key (Optional for advanced analysis) ---
openai_api_key = st.text_input("🔐 OpenAI API key (optional, for AI news analysis):", type="password")
if openai_api_key:
    openai.api_key = openai_api_key

# --- User Inputs ---
symbol = st.text_input("💡 Symbol (e.g. AAPL, MSFT, TSLA, BTC-USD):")
if not symbol:
    st.stop()

risk_mode = st.selectbox("🎚️ Select Risk Level", ["Low", "Medium", "High"])
strategy = st.radio(
    "🕒 Choose Trading Strategy",
    ["⚡ Very Fast Trade (<1h)", "⏰ Fast Trade (today)", "📅 Long-Term Hold"]
)
months = None
if strategy.endswith("Long-Term Hold"):
    months = st.slider("📆 Hold Period (months)", min_value=6, max_value=120, value=12)

# ---------- 1. Chart Data & Advanced Patterns ----------
@st.cache_data(show_spinner=False)
def load_price_data(symbol, strategy, months):
    if strategy.startswith("⚡"):
        return yf.Ticker(symbol).history(period="1d", interval="5m")
    elif strategy.startswith("⏰"):
        return yf.Ticker(symbol).history(period="10d", interval="15m")
    else:
        return yf.Ticker(symbol).history(period=f"{months}mo", interval="1d") if months else yf.Ticker(symbol).history(period="6mo", interval="1d")
df = load_price_data(symbol, strategy, months)

if df.empty:
    st.error("No price data found.")
    st.stop()

def compute_rsi(series, window=14):
    delta = series.diff()
    gain = delta.clip(lower=0)
    loss = -delta.clip(upper=0)
    avg_gain = gain.rolling(window).mean()
    avg_loss = loss.rolling(window).mean()
    rs = avg_gain / avg_loss
    return 100 - (100 / (1 + rs))

# ----- Advanced Pattern Scan -----
def advanced_pattern_scan(df):
    pattern_days, pattern_names = [], []
    for i in range(1, len(df)):
        last, curr = df.iloc[i-1], df.iloc[i]
        patts = []
        # Bullish Engulfing
        if (last.Close < last.Open and
            curr.Close > curr.Open and
            curr.Close > last.Open and
            curr.Open < last.Close):
            patts.append("Bullish Engulfing")
        # Bearish Engulfing
        if (last.Close > last.Open and
            curr.Close < curr.Open and
            curr.Close < last.Open and
            curr.Open > last.Close):
            patts.append("Bearish Engulfing")
        # Hammer
        if (curr.Close > curr.Open and
            curr.Low < curr.Open - (curr.High - curr.Low) * 0.6):
            patts.append("Hammer")
        # Doji
        if abs(curr.Open - curr.Close) < (curr.High - curr.Low) * 0.1:
            patts.append("Doji")
        # Shooting Star
        if (curr.Close < curr.Open and
            curr.High > curr.Open + (curr.High - curr.Low) * 0.6):
            patts.append("Shooting Star")
        if patts:
            pattern_days.append(df.index[i])
            pattern_names.append(", ".join(patts))
    return pattern_days, pattern_names

df["MA_10"] = df.Close.rolling(10).mean()
df["MA_30"] = df.Close.rolling(30).mean()
df['H-L']   = df.High - df.Low
df['ATR']   = df['H-L'].rolling(14).mean()
df['RSI_14']= compute_rsi(df.Close)
pattern_days, pattern_names = advanced_pattern_scan(df)

# ---------- 2. Fetch News Headlines ----------
def fetch_yahoo_news(symbol):
    url = f"https://query1.finance.yahoo.com/v1/finance/search?q={symbol}&newsCount=10"
    r = requests.get(url)
    try:
        news = r.json().get("news", [])
    except Exception:
        news = []
    headlines = []
    for n in news:
        title = n.get("title")
        link = n.get("link")
        if title:
            headlines.append(f"{title} ({link})" if link else title)
    return headlines

with st.spinner("🗞️ Fetching latest news..."):
    news_headlines = fetch_yahoo_news(symbol)

# ---------- 3. AI News/Sentiment/Forecast (if API key given) ----------
def ai_news_analysis(headlines, symbol):
    prompt = (
        f"You are a financial AI assistant. Here are recent news headlines for {symbol}:\n\n"
        + "\n".join(f"- {h}" for h in headlines[:7])
        + "\n\n"
        "Based on these headlines ONLY, do the following:\n"
        "1. Summarize the overall news sentiment (Positive, Negative, Neutral).\n"
        "2. List any major events (earnings, lawsuits, leadership, new products, etc).\n"
        "3. If possible, detect any hidden risks, manipulation, or non-obvious opportunities 'between the lines.'\n"
        "4. Estimate the probability (%) that the price of this asset will go UP in the next 7 days, and probability it will go DOWN. Be concise.\n"
        "5. Give your overall short-term forecast as one sentence (e.g. 'Cautiously Bullish', 'High Risk', 'Volatile')."
    )
    resp = openai.ChatCompletion.create(
        model="gpt-4o",
        messages=[{"role": "user", "content": prompt}],
        temperature=0.4,
        max_tokens=450,
    )
    return resp.choices[0].message.content.strip()

# ---------- 4. Trading Suggestion Based on Patterns & Tech ---------
close   = df.Close.iloc[-1]
atr     = df.ATR.iloc[-1]
rsi     = df.RSI_14.iloc[-1]
mult    = {"Low":1.2,"Medium":1.7,"High":2.4}[risk_mode]
trend   = (
    "Uptrend"   if df.MA_10.iloc[-1] > df.MA_30.iloc[-1]
    else "Downtrend" if df.MA_10.iloc[-1] < df.MA_30.iloc[-1]
    else "Sideways"
)
patterns = []
if len(df) >= 2:
    last, curr = df.iloc[-2], df.iloc[-1]
    if (last.Close < last.Open and curr.Close > curr.Open and curr.Close > last.Open and curr.Open < last.Close):
        patterns.append("Bullish Engulfing")
    if (last.Close > last.Open and curr.Close < curr.Open and curr.Close < last.Open and curr.Open > last.Close):
        patterns.append("Bearish Engulfing")
    if (curr.Close > curr.Open and curr.Low < curr.Open - (curr.High - curr.Low) * 0.6):
        patterns.append("Hammer")
    if abs(curr.Open - curr.Close) < (curr.High - curr.Low) * 0.1:
        patterns.append("Doji")

bullish = any(p in patterns for p in ["Bullish Engulfing","Hammer"])
bearish = any(p in patterns for p in ["Bearish Engulfing"])
if strategy.startswith("⚡"):
    risk_dist = mult * atr
elif strategy.startswith("⏰"):
    risk_dist = mult * atr * np.sqrt(1)
else:
    days = (months or 12) * 21
    risk_dist = mult * atr * np.sqrt(days)

if (trend=="Uptrend" or bullish) and not bearish:
    action = "🟩 Buy / Go Long"
    stop_loss    = close - risk_dist
    target_price = close + risk_dist
elif (trend=="Downtrend" or bearish) and not bullish:
    action = "🟥 Sell / Go Short"
    stop_loss    = close + risk_dist
    target_price = close - risk_dist
else:
    action = "🟨 Neutral / Wait"
    stop_loss    = close - 0.9*risk_dist
    target_price = close + 0.9*risk_dist

rr_ratio = abs((target_price - close) / (close - stop_loss))

# ---------- 5. Show Chart with Pattern Markers ----------
st.markdown("<hr style='border:1.5px solid #fae90a'>", unsafe_allow_html=True)
st.subheader("📊 N9 Advanced Price Chart")
fig = go.Figure(data=[go.Candlestick(
    x=df.index, open=df.Open, high=df.High, low=df.Low, close=df.Close, name="Price",
    increasing_line_color="#08f26e", decreasing_line_color="#2682d3"
)])
fig.add_hline(y=target_price, line_color="#08f26e", annotation_text="Target", annotation_font_color="#08f26e")
fig.add_hline(y=stop_loss,    line_color="#FAE90A",   annotation_text="Stop", annotation_font_color="#FAE90A")
fig.add_trace(go.Scatter(
    x=df.index, y=df.RSI_14, yaxis="y2", name="RSI(14)", line=dict(color="#2682d3", width=2, dash="dash")
))
if pattern_days:
    fig.add_trace(go.Scatter(
        x=pattern_days,
        y=[df.loc[d].Close for d in pattern_days],
        mode="markers+text",
        marker=dict(size=12, color="#FAE90A", symbol="star"),
        text=pattern_names,
        textposition="top center",
        name="Patterns"
    ))
fig.update_layout(
    title=f"{symbol} | {trend} | {strategy}",
    yaxis2=dict(overlaying="y", side="right", range=[0,100], title="RSI"),
    xaxis_rangeslider_visible=False,
    height=650,
    plot_bgcolor="#15171a"
)
st.plotly_chart(fig, use_container_width=True)

# ---------- 6. Show Advanced Technical/Pattern Analysis ----------
st.markdown("<hr style='border:1.5px solid #2682d3'>", unsafe_allow_html=True)
st.subheader("🔎 N9 Technical & Pattern Insights")
st.markdown(f"""
**Strategy:** <span style='color:#FAE90A'>{strategy}</span>  
{f"**Hold Period:** <span style='color:#08f26e'>{months} months</span>  " if strategy.endswith("Long-Term Hold") else ""}  
**Trend:** <span style='color:#2682d3'>{trend}</span>  
**Recent Patterns:** <span style='color:#fae90a'>{', '.join(patterns) or 'None'}</span>  
**Action:** <span style='color:#08f26e'>{action}</span>  
**Entry:** <span style='color:#2682d3'>{close:.2f}</span>  
**Target:** <span style='color:#08f26e'>{target_price:.2f}</span>  
**Stop Loss:** <span style='color:#FAE90A'>{stop_loss:.2f}</span>  
**R/R Ratio:** <span style='color:#fae90a'>{rr_ratio:.2f}</span>  
**RSI(14):** <span style='color:#2682d3'>{rsi:.1f}</span>  
**ATR:** <span style='color:#fae90a'>{atr:.2f}</span>  
""", unsafe_allow_html=True)

# ---------- 7. News Analysis (with or without AI) ----------
st.markdown("<hr style='border:1.5px solid #08f26e'>", unsafe_allow_html=True)
st.subheader("📰 N9 Latest News")
if news_headlines:
    for h in news_headlines:
        st.markdown("- " + h)
    if openai_api_key:
        with st.spinner("🤖 AI analyzing news..."):
            ai_summary = ai_news_analysis(news_headlines, symbol)
        st.subheader("💡 N9 AI News & Sentiment Forecast")
        st.markdown(f"<div style='background:#e9fbe9; border-radius:8px; padding:18px; color:#222;'>{ai_summary}</div>", unsafe_allow_html=True)
    else:
        st.info("Enter your OpenAI API key above to enable advanced AI news analysis and probability forecast.")
else:
    st.info("No news found. Try another symbol or check spelling.")
