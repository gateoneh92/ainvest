import streamlit as st
import requests
from bs4 import BeautifulSoup
from openai import OpenAI
import json
import yfinance as yf
import plotly.graph_objects as go
import pandas as pd
import numpy as np

# ── 1. App Configuration ──────────────────────────────────────────────────────
st.set_page_config(page_title="HaiInvestor", page_icon="👋", layout="wide")

st.markdown("""
<style>
    #MainMenu {visibility: hidden;}
    header {visibility: hidden;}
    footer {visibility: hidden;}
    .block-container { padding-top: 2rem; padding-bottom: 2rem; }

    .app-header {
        background: linear-gradient(135deg, #0f0c29, #302b63, #24243e);
        border-radius: 16px; padding: 28px 36px; margin-bottom: 28px; text-align: center;
    }
    .app-header h1 { color: #fff; font-size: 2.2rem; margin: 0; letter-spacing: 2px; }
    .app-header p  { color: #aaa; margin: 8px 0 0; font-size: 0.95rem; }

    .price-bar {
        background: #1a1a2e; border-radius: 12px; padding: 18px 24px;
        margin-bottom: 16px; display: flex; gap: 32px; align-items: center; flex-wrap: wrap;
    }
    .price-ticker { color: #fff; font-size: 1.6rem; font-weight: 800; }
    .price-value  { color: #fff; font-size: 1.4rem; font-weight: 700; }
    .price-up     { color: #00e676; font-weight: 600; }
    .price-down   { color: #ff5252; font-weight: 600; }
    .price-meta   { color: #aaa; font-size: 0.8rem; }

    .consensus-box {
        background: #16213e; border-radius: 14px; padding: 20px 24px;
        margin-bottom: 28px; border: 1px solid #0f3460;
    }
    .consensus-title { color: #e0e0e0; font-size: 1rem; font-weight: 700; margin-bottom: 14px; letter-spacing: 1px; }

    .badge { display: inline-block; padding: 4px 12px; border-radius: 20px; font-size: 0.78rem; font-weight: 700; letter-spacing: 1px; }
    .badge-bull { background: #00e67622; color: #00e676; border: 1px solid #00e676; }
    .badge-bear { background: #ff525222; color: #ff5252; border: 1px solid #ff5252; }
    .badge-neut { background: #ffd74022; color: #ffd740; border: 1px solid #ffd740; }

    .agent-card { background: #16213e; border-radius: 14px; padding: 20px 22px; margin-bottom: 16px; border-left: 4px solid #0f3460; }
    .agent-card-bull { border-left-color: #00e676; }
    .agent-card-bear { border-left-color: #ff5252; }
    .agent-card-neut { border-left-color: #ffd740; }
    .agent-name { color: #fff; font-size: 1rem; font-weight: 700; margin-bottom: 6px; }
    .agent-conf { color: #aaa; font-size: 0.8rem; margin-bottom: 10px; }
    .agent-text { color: #ccc; font-size: 0.88rem; line-height: 1.6; }

    .conf-bar-bg { background: #0a0a1a; border-radius: 4px; height: 6px; width: 100%; margin: 8px 0 12px; overflow: hidden; }
    .conf-bar-fill-bull { background: #00e676; height: 100%; border-radius: 4px; }
    .conf-bar-fill-bear { background: #ff5252; height: 100%; border-radius: 4px; }
    .conf-bar-fill-neut { background: #ffd740; height: 100%; border-radius: 4px; }

    .verdict-buy  { background: #00e67611; border: 2px solid #00e676; border-radius: 16px; padding: 24px; text-align: center; }
    .verdict-sell { background: #ff525211; border: 2px solid #ff5252; border-radius: 16px; padding: 24px; text-align: center; }
    .verdict-hold { background: #ffd74011; border: 2px solid #ffd740; border-radius: 16px; padding: 24px; text-align: center; }
    .verdict-label { font-size: 2.2rem; font-weight: 900; letter-spacing: 3px; }
    .verdict-label-buy  { color: #00e676; }
    .verdict-label-sell { color: #ff5252; }
    .verdict-label-hold { color: #ffd740; }
    .verdict-sub  { color: #ccc; font-size: 0.9rem; margin-top: 10px; line-height: 1.6; }
    .verdict-conf { color: #aaa; font-size: 0.8rem; margin-top: 8px; }

    .disclaimer { background: #1a1a2e; border-radius: 10px; padding: 14px 20px; color: #666; font-size: 0.78rem; margin-top: 32px; text-align: center; }
</style>
""", unsafe_allow_html=True)

# ── 2. API Key ────────────────────────────────────────────────────────────────
try:
    OPENAI_API_KEY = st.secrets["OPENAI_API_KEY"]
except Exception:
    st.error("API Key is missing. Please check your .streamlit/secrets.toml file.")
    st.stop()

# ── 3. Header ─────────────────────────────────────────────────────────────────
st.markdown("""
<div class="app-header">
    <h1>👋 HaiInvestor</h1>
    <p>New to investing? Just pick a stock — 6 legendary AI investors will debate it for you.</p>
</div>
""", unsafe_allow_html=True)

# ── 4. Tabs ───────────────────────────────────────────────────────────────────
tab1, tab2, tab3 = st.tabs(["📊 Single Stock", "💼 Portfolio", "📈 Backtest"])

# ═══════════════════════════════════════════════════════════════════════════════
# HELPERS
# ═══════════════════════════════════════════════════════════════════════════════

AGENTS_ORDER = [
    ("Warren",  "👴", "Warren Buffett",  "Value Investor"),
    ("Charlie", "🧠", "Charlie Munger",  "Mental Models"),
    ("Michael", "🐻", "Michael Burry",   "Contrarian Bear"),
    ("Peter",   "🏃", "Peter Lynch",     "GARP Investor"),
    ("Cathie",  "🚀", "Cathie Wood",     "Innovation Bull"),
    ("Bill",    "⚔️", "Bill Ackman",     "Activist Investor"),
]

def signal_badge(sig):
    if sig == "BULLISH": return '<span class="badge badge-bull">▲ BULLISH</span>'
    if sig == "BEARISH": return '<span class="badge badge-bear">▼ BEARISH</span>'
    return '<span class="badge badge-neut">◆ NEUTRAL</span>'

def signal_card_class(sig):
    return {"BULLISH": "agent-card-bull", "BEARISH": "agent-card-bear"}.get(sig, "agent-card-neut")

def signal_bar_class(sig):
    return {"BULLISH": "conf-bar-fill-bull", "BEARISH": "conf-bar-fill-bear"}.get(sig, "conf-bar-fill-neut")

def fmt_val(val, suffix="", multiplier=1, decimals=2):
    if val is None or (isinstance(val, float) and np.isnan(val)):
        return "N/A"
    v = val * multiplier
    if suffix == "" and abs(v) >= 1e12: return f"${v/1e12:.1f}T"
    if suffix == "" and abs(v) >= 1e9:  return f"${v/1e9:.1f}B"
    if suffix == "" and abs(v) >= 1e6:  return f"${v/1e6:.1f}M"
    return f"{v:.{decimals}f}{suffix}"

def fetch_price_and_fundamentals(ticker):
    """Returns (price_dict, fundamentals_dict, tkr) or raises."""
    tkr  = yf.Ticker(ticker)
    hist = tkr.history(period="5d")
    if hist.empty:
        raise ValueError("No price data")
    price = {
        "current":  float(hist["Close"].iloc[-1]),
        "prev":     float(hist["Close"].iloc[-2]) if len(hist) >= 2 else float(hist["Close"].iloc[-1]),
        "high":     float(hist["High"].iloc[-1]),
        "low":      float(hist["Low"].iloc[-1]),
    }
    price["change"]     = price["current"] - price["prev"]
    price["change_pct"] = price["change"] / price["prev"] * 100

    info = tkr.info
    fund = {
        "Market Cap":    fmt_val(info.get("marketCap")),
        "P/E (TTM)":     fmt_val(info.get("trailingPE"),       decimals=1),
        "Forward P/E":   fmt_val(info.get("forwardPE"),        decimals=1),
        "P/B Ratio":     fmt_val(info.get("priceToBook"),      decimals=2),
        "Revenue Growth":fmt_val(info.get("revenueGrowth"),    suffix="%", multiplier=100, decimals=1),
        "Profit Margin": fmt_val(info.get("profitMargins"),    suffix="%", multiplier=100, decimals=1),
        "ROE":           fmt_val(info.get("returnOnEquity"),   suffix="%", multiplier=100, decimals=1),
        "Debt/Equity":   fmt_val(info.get("debtToEquity"),     decimals=2),
    }
    return price, fund, tkr

def fetch_news(ticker):
    url  = f"https://news.google.com/rss/search?q={ticker}+stock&hl=en-US&gl=US&ceid=US:en"
    resp = requests.get(url, timeout=10)
    soup = BeautifulSoup(resp.content, "html.parser")
    items = soup.find_all("item")
    return "\n".join(f"- {it.title.text}" for it in items[:10])

def run_ai_debate(ticker, news_texts, fund):
    fund_text = "Key financial data:\n" + "\n".join(
        f"- {k}: {v}" for k, v in fund.items() if v != "N/A"
    )
    prompt = f"""
You are simulating a live investment committee debate about '{ticker}'.
Latest news headlines:
{news_texts}

{fund_text}

Return ONLY a valid JSON object with this exact structure (no extra text):
{{
  "Warren":  {{"signal": "BULLISH|BEARISH|NEUTRAL", "confidence": <1-100>, "reasoning": "<2-3 sentences from Warren Buffett's value-investing perspective>"}},
  "Charlie": {{"signal": "BULLISH|BEARISH|NEUTRAL", "confidence": <1-100>, "reasoning": "<2-3 sentences from Charlie Munger's mental-models perspective>"}},
  "Michael": {{"signal": "BULLISH|BEARISH|NEUTRAL", "confidence": <1-100>, "reasoning": "<2-3 sentences from Michael Burry's contrarian macro perspective>"}},
  "Peter":   {{"signal": "BULLISH|BEARISH|NEUTRAL", "confidence": <1-100>, "reasoning": "<2-3 sentences from Peter Lynch's GARP perspective>"}},
  "Cathie":  {{"signal": "BULLISH|BEARISH|NEUTRAL", "confidence": <1-100>, "reasoning": "<2-3 sentences from Cathie Wood's disruptive-technology perspective>"}},
  "Bill":    {{"signal": "BULLISH|BEARISH|NEUTRAL", "confidence": <1-100>, "reasoning": "<2-3 sentences from Bill Ackman's activist-investor perspective>"}},
  "Manager": {{"verdict": "BUY|SELL|HOLD", "confidence": <1-100>, "action": "<One concrete actionable sentence>", "rationale": "<2-3 sentences synthesizing the panel's views>"}}
}}
"""
    client = OpenAI(api_key=OPENAI_API_KEY)
    resp   = client.chat.completions.create(
        model="gpt-4o-mini",
        response_format={"type": "json_object"},
        messages=[
            {"role": "system", "content": "You are a multi-agent hedge fund simulator. Output only valid JSON."},
            {"role": "user",   "content": prompt},
        ],
    )
    return json.loads(resp.choices[0].message.content)

def render_price_bar(ticker, price):
    d_class = "price-up" if price["change"] >= 0 else "price-down"
    d_sign  = "▲" if price["change"] >= 0 else "▼"
    st.markdown(f"""
<div class="price-bar">
    <span class="price-ticker">{ticker}</span>
    <span class="price-value">${price['current']:,.2f}</span>
    <span class="{d_class}">{d_sign} {abs(price['change']):.2f} ({abs(price['change_pct']):.2f}%)</span>
    <span class="price-meta">Day: ${price['low']:,.2f} – ${price['high']:,.2f}</span>
</div>""", unsafe_allow_html=True)

def render_fundamentals(fund):
    html = "<div style='display:flex; flex-wrap:wrap; gap:10px; margin-bottom:20px;'>"
    for label, value in fund.items():
        if value == "N/A": continue
        html += f"""<div style='background:#1a1a2e; border-radius:10px; padding:12px 18px; min-width:110px;'>
            <div style='color:#aaa; font-size:0.72rem; margin-bottom:4px;'>{label}</div>
            <div style='color:#fff; font-size:1rem; font-weight:700;'>{value}</div></div>"""
    html += "</div>"
    st.markdown(html, unsafe_allow_html=True)

def render_consensus(ticker, result):
    signals  = [result[k]["signal"] for k, *_ in AGENTS_ORDER if k in result]
    bull_n   = signals.count("BULLISH")
    bear_n   = signals.count("BEARISH")
    neut_n   = signals.count("NEUTRAL")
    total    = len(signals) or 1
    bull_pct = int(bull_n / total * 100)
    bear_pct = int(bear_n / total * 100)
    neut_pct = int(neut_n / total * 100)
    st.markdown(f"""
<div class="consensus-box">
    <div class="consensus-title">⚖️ PANEL CONSENSUS — {ticker}</div>
    <div style="display:flex; gap:24px; margin-bottom:12px;">
        <span>{signal_badge('BULLISH')} &nbsp;<b style="color:#fff">{bull_n}</b><span style="color:#aaa"> / {total}</span></span>
        <span>{signal_badge('BEARISH')} &nbsp;<b style="color:#fff">{bear_n}</b><span style="color:#aaa"> / {total}</span></span>
        <span>{signal_badge('NEUTRAL')} &nbsp;<b style="color:#fff">{neut_n}</b><span style="color:#aaa"> / {total}</span></span>
    </div>
    <div style="display:flex; height:10px; border-radius:6px; overflow:hidden; background:#0a0a1a;">
        <div style="width:{bull_pct}%; background:#00e676;"></div>
        <div style="width:{neut_pct}%; background:#ffd740;"></div>
        <div style="width:{bear_pct}%; background:#ff5252;"></div>
    </div>
    <div style="display:flex; justify-content:space-between; margin-top:4px;">
        <span style="color:#00e676; font-size:0.75rem;">{bull_pct}% Bullish</span>
        <span style="color:#ffd740; font-size:0.75rem;">{neut_pct}% Neutral</span>
        <span style="color:#ff5252; font-size:0.75rem;">{bear_pct}% Bearish</span>
    </div>
</div>""", unsafe_allow_html=True)

def render_agent_cards(result):
    st.markdown("### 🗣️ Investor Perspectives")
    col_l, col_r = st.columns(2)
    for i, (key, icon, name, role) in enumerate(AGENTS_ORDER):
        data = result.get(key, {})
        sig  = data.get("signal", "NEUTRAL")
        conf = data.get("confidence", 50)
        text = data.get("reasoning", "")
        html = f"""<div class="agent-card {signal_card_class(sig)}">
    <div class="agent-name">{icon} {name} <span style="color:#aaa; font-weight:400; font-size:0.8rem;">· {role}</span></div>
    {signal_badge(sig)}
    <div class="conf-bar-bg"><div class="{signal_bar_class(sig)}" style="width:{conf}%;"></div></div>
    <div class="agent-conf">Conviction: {conf}%</div>
    <div class="agent-text">{text}</div>
</div>"""
        (col_l if i % 2 == 0 else col_r).markdown(html, unsafe_allow_html=True)

def render_verdict(result):
    st.markdown("### 🏦 Portfolio Manager's Final Verdict")
    mgr       = result.get("Manager", {})
    verdict   = mgr.get("verdict", "HOLD")
    m_conf    = mgr.get("confidence", 50)
    action    = mgr.get("action", "")
    rationale = mgr.get("rationale", "")
    v_class   = {"BUY": "verdict-buy",       "SELL": "verdict-sell"      }.get(verdict, "verdict-hold")
    l_class   = {"BUY": "verdict-label-buy", "SELL": "verdict-label-sell"}.get(verdict, "verdict-label-hold")
    v_icon    = {"BUY": "📗", "SELL": "📕"}.get(verdict, "📒")
    st.markdown(f"""<div class="{v_class}">
    <div class="verdict-label {l_class}">{v_icon} {verdict}</div>
    <div class="verdict-sub"><b>{action}</b><br><br>{rationale}</div>
    <div class="verdict-conf">Portfolio Manager Conviction: {m_conf}%</div>
</div>""", unsafe_allow_html=True)

# ═══════════════════════════════════════════════════════════════════════════════
# TAB 1 — SINGLE STOCK
# ═══════════════════════════════════════════════════════════════════════════════
with tab1:
    st.markdown("#### 🔥 Popular Stocks")
    c1, c2, c3, c4, c5 = st.columns(5)
    target_ticker = None
    if c1.button("🍎 AAPL", use_container_width=True): target_ticker = "AAPL"
    if c2.button("🟩 NVDA", use_container_width=True): target_ticker = "NVDA"
    if c3.button("🚗 TSLA", use_container_width=True): target_ticker = "TSLA"
    if c4.button("🪟 MSFT", use_container_width=True): target_ticker = "MSFT"
    if c5.button("📦 AMZN", use_container_width=True): target_ticker = "AMZN"

    st.markdown("<br>", unsafe_allow_html=True)
    custom = st.text_input("🔍 Search any ticker (Press Enter)", placeholder="e.g., GOOGL, META, MSTR, BTC-USD", key="single_input")
    if custom:
        target_ticker = custom.upper().strip()

    if target_ticker:
        st.markdown("---")
        with st.spinner(f"Fetching data for {target_ticker}..."):
            try:
                price, fund, tkr = fetch_price_and_fundamentals(target_ticker)
            except Exception as e:
                st.error(f"Could not fetch data: {e}")
                st.stop()

        render_price_bar(target_ticker, price)

        # ── Chart ────────────────────────────────────────────────────────────
        try:
            hist_6m = tkr.history(period="6mo")
            if not hist_6m.empty:
                fig = go.Figure()
                fig.add_trace(go.Candlestick(
                    x=hist_6m.index,
                    open=hist_6m["Open"], high=hist_6m["High"],
                    low=hist_6m["Low"],   close=hist_6m["Close"],
                    increasing_line_color="#00e676", decreasing_line_color="#ff5252",
                    name="Price",
                ))
                fig.update_layout(
                    paper_bgcolor="#16213e", plot_bgcolor="#16213e",
                    font_color="#ccc", height=320,
                    margin=dict(l=10, r=10, t=10, b=10),
                    xaxis=dict(gridcolor="#0f3460", showgrid=True, rangeslider_visible=False),
                    yaxis=dict(gridcolor="#0f3460", showgrid=True),
                    showlegend=False,
                )
                st.plotly_chart(fig, use_container_width=True)
        except Exception:
            pass

        render_fundamentals(fund)

        with st.spinner("Convening the AI Hedge Fund Panel... ⏳"):
            try:
                news   = fetch_news(target_ticker)
                result = run_ai_debate(target_ticker, news, fund)
                render_consensus(target_ticker, result)
                render_agent_cards(result)
                render_verdict(result)
            except Exception as e:
                st.error(f"An error occurred: {e}")

# ═══════════════════════════════════════════════════════════════════════════════
# TAB 2 — PORTFOLIO MODE
# ═══════════════════════════════════════════════════════════════════════════════
with tab2:
    st.markdown("### 💼 Portfolio Analyzer")
    st.caption("Enter multiple tickers to get AI signals for each and suggested portfolio weights.")

    portfolio_input = st.text_input(
        "Enter tickers separated by commas",
        placeholder="e.g., AAPL, NVDA, TSLA, MSFT",
        key="portfolio_input"
    )

    if st.button("🚀 Analyze Portfolio", use_container_width=True, key="portfolio_btn"):
        tickers = [t.strip().upper() for t in portfolio_input.split(",") if t.strip()]
        if not tickers:
            st.warning("Enter at least one ticker.")
        elif len(tickers) > 6:
            st.warning("Maximum 6 tickers at once.")
        else:
            results_list = []
            progress = st.progress(0, text="Analyzing...")

            for i, ticker in enumerate(tickers):
                progress.progress((i) / len(tickers), text=f"Analyzing {ticker}...")
                try:
                    price, fund, _ = fetch_price_and_fundamentals(ticker)
                    news = fetch_news(ticker)
                    # Lightweight single-signal prompt
                    fund_text = "\n".join(f"- {k}: {v}" for k, v in fund.items() if v != "N/A")
                    prompt = f"""
Analyze '{ticker}' as a portfolio manager.
News: {news[:500]}
Financials: {fund_text}
Return JSON: {{"signal": "BULLISH|BEARISH|NEUTRAL", "confidence": <1-100>, "summary": "<1 sentence rationale>", "verdict": "BUY|SELL|HOLD"}}
"""
                    client = OpenAI(api_key=OPENAI_API_KEY)
                    resp   = client.chat.completions.create(
                        model="gpt-4o-mini",
                        response_format={"type": "json_object"},
                        messages=[
                            {"role": "system", "content": "Portfolio analysis. Output only valid JSON."},
                            {"role": "user",   "content": prompt},
                        ],
                    )
                    ai = json.loads(resp.choices[0].message.content)
                    results_list.append({
                        "ticker":     ticker,
                        "price":      price["current"],
                        "change_pct": price["change_pct"],
                        "signal":     ai.get("signal", "NEUTRAL"),
                        "confidence": ai.get("confidence", 50),
                        "verdict":    ai.get("verdict", "HOLD"),
                        "summary":    ai.get("summary", ""),
                        "mktcap":     fund.get("Market Cap", "N/A"),
                        "pe":         fund.get("P/E (TTM)", "N/A"),
                    })
                except Exception as e:
                    results_list.append({
                        "ticker": ticker, "price": 0, "change_pct": 0,
                        "signal": "NEUTRAL", "confidence": 0, "verdict": "HOLD",
                        "summary": f"Error: {e}", "mktcap": "N/A", "pe": "N/A",
                    })
                progress.progress((i + 1) / len(tickers), text=f"Done: {ticker}")

            progress.empty()

            # ── Suggested weights (based on bullish conviction only) ──────────
            bull_stocks = [r for r in results_list if r["signal"] == "BULLISH"]
            total_conf  = sum(r["confidence"] for r in bull_stocks) or 1
            for r in results_list:
                r["weight"] = f"{int(r['confidence'] / total_conf * 100)}%" if r["signal"] == "BULLISH" else "—"

            # ── Display table ────────────────────────────────────────────────
            st.markdown("#### 📋 Portfolio Summary")
            for r in results_list:
                sig   = r["signal"]
                chg   = r["change_pct"]
                chg_c = "#00e676" if chg >= 0 else "#ff5252"
                chg_s = f"▲ {abs(chg):.1f}%" if chg >= 0 else f"▼ {abs(chg):.1f}%"
                v_color = {"BUY": "#00e676", "SELL": "#ff5252"}.get(r["verdict"], "#ffd740")

                st.markdown(f"""
<div style="background:#16213e; border-radius:12px; padding:16px 20px; margin-bottom:12px;
            border-left:4px solid {'#00e676' if sig=='BULLISH' else '#ff5252' if sig=='BEARISH' else '#ffd740'};">
  <div style="display:flex; justify-content:space-between; align-items:center; flex-wrap:wrap; gap:8px;">
    <div>
      <span style="color:#fff; font-size:1.1rem; font-weight:800;">{r['ticker']}</span>
      <span style="color:#aaa; font-size:0.85rem; margin-left:10px;">${r['price']:,.2f}</span>
      <span style="color:{chg_c}; font-size:0.85rem; margin-left:8px;">{chg_s}</span>
    </div>
    <div style="display:flex; gap:12px; align-items:center; flex-wrap:wrap;">
      {signal_badge(sig)}
      <span style="color:{v_color}; font-weight:700; font-size:0.9rem;">{r['verdict']}</span>
      <span style="color:#aaa; font-size:0.8rem;">Conviction: {r['confidence']}%</span>
      <span style="color:#0079C1; font-size:0.85rem; font-weight:700;">Weight: {r['weight']}</span>
    </div>
  </div>
  <div style="color:#aaa; font-size:0.82rem; margin-top:8px;">{r['summary']}</div>
  <div style="color:#666; font-size:0.75rem; margin-top:4px;">Market Cap: {r['mktcap']} &nbsp;|&nbsp; P/E: {r['pe']}</div>
</div>""", unsafe_allow_html=True)

            # ── Pie chart of suggested weights ───────────────────────────────
            bull_for_pie = [r for r in results_list if r["signal"] == "BULLISH"]
            if bull_for_pie:
                st.markdown("#### 🥧 Suggested Allocation (Bullish Only)")
                fig_pie = go.Figure(go.Pie(
                    labels=[r["ticker"] for r in bull_for_pie],
                    values=[r["confidence"] for r in bull_for_pie],
                    hole=0.4,
                    marker_colors=["#00e676", "#0079C1", "#ffd740", "#9c27b0", "#ff9800", "#00bcd4"],
                ))
                fig_pie.update_layout(
                    paper_bgcolor="#16213e", font_color="#ccc",
                    height=300, margin=dict(l=10, r=10, t=10, b=10),
                    showlegend=True,
                )
                st.plotly_chart(fig_pie, use_container_width=True)
            else:
                st.info("No BULLISH signals — consider waiting for a better entry point.")

# ═══════════════════════════════════════════════════════════════════════════════
# TAB 3 — BACKTEST
# ═══════════════════════════════════════════════════════════════════════════════
with tab3:
    st.markdown("### 📈 Strategy Backtest")
    st.caption("Simulates a SMA(20/50) crossover strategy vs. Buy & Hold over the selected period.")

    bt_col1, bt_col2, bt_col3 = st.columns([2, 1, 1])
    with bt_col1:
        bt_ticker = st.text_input("Ticker", value="NVDA", key="bt_ticker").upper().strip()
    with bt_col2:
        bt_period = st.selectbox("Period", ["6mo", "1y", "2y", "5y"], index=1)
    with bt_col3:
        st.markdown("<br>", unsafe_allow_html=True)
        run_bt = st.button("▶ Run Backtest", use_container_width=True)

    if run_bt and bt_ticker:
        with st.spinner("Running backtest..."):
            try:
                tkr_bt = yf.Ticker(bt_ticker)
                df     = tkr_bt.history(period=bt_period)[["Close", "Volume"]].copy()
                if df.empty or len(df) < 60:
                    st.error("Not enough data for backtest.")
                else:
                    df["SMA20"] = df["Close"].rolling(20).mean()
                    df["SMA50"] = df["Close"].rolling(50).mean()
                    df = df.dropna()

                    # Signal: 1 when SMA20 > SMA50, else 0 (shifted by 1 to avoid lookahead)
                    df["signal"]   = (df["SMA20"] > df["SMA50"]).astype(int).shift(1).fillna(0)
                    df["ret"]      = df["Close"].pct_change()
                    df["strat"]    = df["signal"] * df["ret"]

                    df["bah_cum"]   = (1 + df["ret"]).cumprod()
                    df["strat_cum"] = (1 + df["strat"]).cumprod()

                    # ── Stats ────────────────────────────────────────────────
                    bah_ret   = (df["bah_cum"].iloc[-1] - 1) * 100
                    strat_ret = (df["strat_cum"].iloc[-1] - 1) * 100

                    rolling_max  = df["strat_cum"].cummax()
                    drawdown     = (df["strat_cum"] - rolling_max) / rolling_max
                    max_dd       = drawdown.min() * 100

                    win_days = (df["strat"] > 0).sum()
                    tot_days = (df["signal"] == 1).sum()
                    win_rate = win_days / tot_days * 100 if tot_days > 0 else 0

                    # ── Metrics row ──────────────────────────────────────────
                    m1, m2, m3, m4 = st.columns(4)
                    m1.metric("Strategy Return", f"{strat_ret:+.1f}%")
                    m2.metric("Buy & Hold Return", f"{bah_ret:+.1f}%")
                    m3.metric("Max Drawdown", f"{max_dd:.1f}%")
                    m4.metric("Win Rate (in-market)", f"{win_rate:.1f}%")

                    # ── Chart ────────────────────────────────────────────────
                    fig = go.Figure()
                    fig.add_trace(go.Scatter(
                        x=df.index, y=df["bah_cum"],
                        name="Buy & Hold", line=dict(color="#aaa", width=1.5, dash="dot"),
                    ))
                    fig.add_trace(go.Scatter(
                        x=df.index, y=df["strat_cum"],
                        name="SMA Strategy", line=dict(color="#00e676", width=2),
                        fill="tozeroy", fillcolor="rgba(0,230,118,0.05)",
                    ))
                    # SMA lines on secondary
                    fig.add_trace(go.Scatter(
                        x=df.index, y=df["SMA20"] / df["Close"].iloc[0],
                        name="SMA20 (norm)", line=dict(color="#0079C1", width=1), visible="legendonly",
                    ))
                    fig.add_trace(go.Scatter(
                        x=df.index, y=df["SMA50"] / df["Close"].iloc[0],
                        name="SMA50 (norm)", line=dict(color="#ffd740", width=1), visible="legendonly",
                    ))
                    fig.update_layout(
                        paper_bgcolor="#16213e", plot_bgcolor="#16213e",
                        font_color="#ccc", height=380,
                        margin=dict(l=10, r=10, t=30, b=10),
                        xaxis=dict(gridcolor="#0f3460"),
                        yaxis=dict(gridcolor="#0f3460", tickformat=".0%"),
                        legend=dict(bgcolor="#0f0c29", bordercolor="#0f3460", borderwidth=1),
                        title=dict(text=f"{bt_ticker} — Strategy vs Buy & Hold", font_color="#ccc"),
                    )
                    st.plotly_chart(fig, use_container_width=True)

                    st.caption("""
**How it works:** SMA(20/50) crossover — buy when the 20-day moving average crosses above the 50-day, sell when it crosses below.
This is a simple technical proxy, not the actual AI signal. For educational purposes only.
""")
            except Exception as e:
                st.error(f"Backtest error: {e}")

# ── Footer ────────────────────────────────────────────────────────────────────
st.markdown("""
<div class="disclaimer">
    ⚠️ <b>Disclaimer:</b> This AI analysis is a simulation based on public news and financial data.
    Not financial advice. Always do your own research before making investment decisions.
</div>
""", unsafe_allow_html=True)

try:
    r     = requests.get("https://api.counterapi.dev/v1/hainvestor/visits/up", timeout=3)
    count = r.json().get("count", "—")
except Exception:
    count = "—"

st.markdown(f"""
<div style='text-align:center; margin:16px 0 8px; color:#aaa; font-size:0.85rem;'>
    👁️ Total Visitors &nbsp;<span style='color:#fff; font-weight:700; font-size:1rem;'>{count}</span>
</div>
""", unsafe_allow_html=True)

st.markdown("<br>", unsafe_allow_html=True)
col1, col2, col3 = st.columns([1, 1.5, 1])
with col2:
    st.link_button("💸 Pay $1 to Insult Me", "https://www.paypal.com/ncp/payment/A3Q3JEV6WRXSG", use_container_width=True)
