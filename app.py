import streamlit as st
import requests
from bs4 import BeautifulSoup
from openai import OpenAI
import json
import yfinance as yf

# ── 1. App Configuration ──────────────────────────────────────────────────────
st.set_page_config(page_title="HaiInvestor", page_icon="👋", layout="wide")

st.markdown("""
<style>
    #MainMenu {visibility: hidden;}
    header {visibility: hidden;}
    footer {visibility: hidden;}

    /* Base */
    .block-container { padding-top: 2rem; padding-bottom: 2rem; }

    /* Header */
    .app-header {
        background: linear-gradient(135deg, #0f0c29, #302b63, #24243e);
        border-radius: 16px;
        padding: 28px 36px;
        margin-bottom: 28px;
        text-align: center;
    }
    .app-header h1 { color: #fff; font-size: 2.2rem; margin: 0; letter-spacing: 2px; }
    .app-header p  { color: #aaa; margin: 8px 0 0; font-size: 0.95rem; }

    /* Stock price bar */
    .price-bar {
        background: #1a1a2e;
        border-radius: 12px;
        padding: 18px 24px;
        margin-bottom: 24px;
        display: flex;
        gap: 32px;
        align-items: center;
    }
    .price-ticker { color: #fff; font-size: 1.6rem; font-weight: 800; }
    .price-value  { color: #fff; font-size: 1.4rem; font-weight: 700; }
    .price-up     { color: #00e676; font-weight: 600; }
    .price-down   { color: #ff5252; font-weight: 600; }
    .price-meta   { color: #aaa; font-size: 0.8rem; }

    /* Consensus bar */
    .consensus-box {
        background: #16213e;
        border-radius: 14px;
        padding: 20px 24px;
        margin-bottom: 28px;
        border: 1px solid #0f3460;
    }
    .consensus-title { color: #e0e0e0; font-size: 1rem; font-weight: 700; margin-bottom: 14px; letter-spacing: 1px; }

    /* Signal badges */
    .badge {
        display: inline-block;
        padding: 4px 12px;
        border-radius: 20px;
        font-size: 0.78rem;
        font-weight: 700;
        letter-spacing: 1px;
    }
    .badge-bull  { background: #00e67622; color: #00e676; border: 1px solid #00e676; }
    .badge-bear  { background: #ff525222; color: #ff5252; border: 1px solid #ff5252; }
    .badge-neut  { background: #ffd74022; color: #ffd740; border: 1px solid #ffd740; }

    /* Investor card */
    .agent-card {
        background: #16213e;
        border-radius: 14px;
        padding: 20px 22px;
        margin-bottom: 16px;
        border-left: 4px solid #0f3460;
        transition: 0.2s;
    }
    .agent-card-bull { border-left-color: #00e676; }
    .agent-card-bear { border-left-color: #ff5252; }
    .agent-card-neut { border-left-color: #ffd740; }
    .agent-name  { color: #fff; font-size: 1rem; font-weight: 700; margin-bottom: 6px; }
    .agent-conf  { color: #aaa; font-size: 0.8rem; margin-bottom: 10px; }
    .agent-text  { color: #ccc; font-size: 0.88rem; line-height: 1.6; }

    /* Confidence bar */
    .conf-bar-bg {
        background: #0a0a1a;
        border-radius: 4px;
        height: 6px;
        width: 100%;
        margin: 8px 0 12px;
        overflow: hidden;
    }
    .conf-bar-fill-bull { background: #00e676; height: 100%; border-radius: 4px; }
    .conf-bar-fill-bear { background: #ff5252; height: 100%; border-radius: 4px; }
    .conf-bar-fill-neut { background: #ffd740; height: 100%; border-radius: 4px; }

    /* Verdict box */
    .verdict-buy  { background: #00e67611; border: 2px solid #00e676; border-radius: 16px; padding: 24px; text-align: center; }
    .verdict-sell { background: #ff525211; border: 2px solid #ff5252; border-radius: 16px; padding: 24px; text-align: center; }
    .verdict-hold { background: #ffd74011; border: 2px solid #ffd740; border-radius: 16px; padding: 24px; text-align: center; }
    .verdict-label { font-size: 2.2rem; font-weight: 900; letter-spacing: 3px; }
    .verdict-label-buy  { color: #00e676; }
    .verdict-label-sell { color: #ff5252; }
    .verdict-label-hold { color: #ffd740; }
    .verdict-sub   { color: #ccc; font-size: 0.9rem; margin-top: 10px; line-height: 1.6; }
    .verdict-conf  { color: #aaa; font-size: 0.8rem; margin-top: 8px; }

    /* Disclaimer */
    .disclaimer {
        background: #1a1a2e;
        border-radius: 10px;
        padding: 14px 20px;
        color: #666;
        font-size: 0.78rem;
        margin-top: 32px;
        text-align: center;
    }
</style>
""", unsafe_allow_html=True)

# ── 2. Load OpenAI API Key ────────────────────────────────────────────────────
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

# ── 4. Quick Buttons ──────────────────────────────────────────────────────────
st.markdown("#### 🔥 Popular Stocks")
col1, col2, col3, col4, col5 = st.columns(5)

target_ticker = None
if col1.button("🍎 AAPL", use_container_width=True): target_ticker = "AAPL"
if col2.button("🟩 NVDA", use_container_width=True): target_ticker = "NVDA"
if col3.button("🚗 TSLA", use_container_width=True): target_ticker = "TSLA"
if col4.button("🪟 MSFT", use_container_width=True): target_ticker = "MSFT"
if col5.button("📦 AMZN", use_container_width=True): target_ticker = "AMZN"

st.markdown("<br>", unsafe_allow_html=True)
custom_ticker = st.text_input("🔍 Search any ticker (Press Enter)", placeholder="e.g., GOOGL, META, MSTR, BTC-USD")
if custom_ticker:
    target_ticker = custom_ticker.upper().strip()

# ── 5. Analysis ───────────────────────────────────────────────────────────────
if target_ticker:
    st.markdown("---")

    # ── 5a. Live Price Data ──────────────────────────────────────────────────
    price_html = ""
    try:
        tkr = yf.Ticker(target_ticker)
        info = tkr.fast_info
        current_price = info.last_price
        prev_close    = info.previous_close
        change        = current_price - prev_close
        change_pct    = (change / prev_close) * 100
        day_high      = info.day_high
        day_low       = info.day_low
        year_high     = info.year_high
        year_low      = info.year_low

        direction_class = "price-up" if change >= 0 else "price-down"
        direction_sign  = "▲" if change >= 0 else "▼"

        price_html = f"""
        <div class="price-bar">
            <span class="price-ticker">{target_ticker}</span>
            <span class="price-value">${current_price:,.2f}</span>
            <span class="{direction_class}">{direction_sign} {abs(change):.2f} ({abs(change_pct):.2f}%)</span>
            <span class="price-meta">Day: ${day_low:,.2f} – ${day_high:,.2f} &nbsp;|&nbsp; 52W: ${year_low:,.2f} – ${year_high:,.2f}</span>
        </div>
        """
    except Exception:
        price_html = f'<div class="price-bar"><span class="price-ticker">{target_ticker}</span><span class="price-meta" style="color:#aaa">Price data unavailable</span></div>'

    st.markdown(price_html, unsafe_allow_html=True)

    # ── 5b. AI Debate ────────────────────────────────────────────────────────
    with st.spinner("Convening the AI Hedge Fund Panel... ⏳"):
        try:
            # Fetch news
            url = f"https://news.google.com/rss/search?q={target_ticker}+stock&hl=en-US&gl=US&ceid=US:en"
            resp = requests.get(url, timeout=10)
            soup = BeautifulSoup(resp.content, "html.parser")
            items = soup.find_all("item")

            if not items:
                st.warning("Not enough recent news found for this ticker.")
                st.stop()

            news_texts = "\n".join(f"- {it.title.text}" for it in items[:10])

            prompt = f"""
You are simulating a live investment committee debate about '{target_ticker}'.
Latest news headlines:
{news_texts}

Return ONLY a valid JSON object with this exact structure (no extra text):
{{
  "Warren":  {{"signal": "BULLISH|BEARISH|NEUTRAL", "confidence": <1-100>, "reasoning": "<2-3 sentences from Warren Buffett's value-investing perspective>"}},
  "Charlie": {{"signal": "BULLISH|BEARISH|NEUTRAL", "confidence": <1-100>, "reasoning": "<2-3 sentences from Charlie Munger's mental-models perspective>"}},
  "Michael": {{"signal": "BULLISH|BEARISH|NEUTRAL", "confidence": <1-100>, "reasoning": "<2-3 sentences from Michael Burry's contrarian macro perspective>"}},
  "Peter":   {{"signal": "BULLISH|BEARISH|NEUTRAL", "confidence": <1-100>, "reasoning": "<2-3 sentences from Peter Lynch's growth-at-reasonable-price perspective>"}},
  "Cathie":  {{"signal": "BULLISH|BEARISH|NEUTRAL", "confidence": <1-100>, "reasoning": "<2-3 sentences from Cathie Wood's disruptive-technology perspective>"}},
  "Bill":    {{"signal": "BULLISH|BEARISH|NEUTRAL", "confidence": <1-100>, "reasoning": "<2-3 sentences from Bill Ackman's activist-investor perspective>"}},
  "Manager": {{"verdict": "BUY|SELL|HOLD", "confidence": <1-100>, "action": "<One concrete actionable sentence>", "rationale": "<2-3 sentences synthesizing the panel's views>"}}
}}
"""

            client   = OpenAI(api_key=OPENAI_API_KEY)
            response = client.chat.completions.create(
                model="gpt-4o-mini",
                response_format={"type": "json_object"},
                messages=[
                    {"role": "system", "content": "You are a multi-agent hedge fund simulator. Output only valid JSON."},
                    {"role": "user",   "content": prompt},
                ],
            )
            result = json.loads(response.choices[0].message.content)

            # ── 5c. Consensus Summary ────────────────────────────────────────
            agents_order = [
                ("Warren",  "👴", "Warren Buffett",    "Value Investor"),
                ("Charlie", "🧠", "Charlie Munger",    "Mental Models"),
                ("Michael", "🐻", "Michael Burry",     "Contrarian Bear"),
                ("Peter",   "🏃", "Peter Lynch",       "GARP Investor"),
                ("Cathie",  "🚀", "Cathie Wood",       "Innovation Bull"),
                ("Bill",    "⚔️", "Bill Ackman",       "Activist Investor"),
            ]

            signals = [result[k]["signal"] for k, *_ in agents_order if k in result]
            bull_n  = signals.count("BULLISH")
            bear_n  = signals.count("BEARISH")
            neut_n  = signals.count("NEUTRAL")
            total   = len(signals) or 1

            bull_pct = int(bull_n / total * 100)
            bear_pct = int(bear_n / total * 100)
            neut_pct = int(neut_n / total * 100)

            st.markdown(f"""
<div class="consensus-box">
    <div class="consensus-title">⚖️ PANEL CONSENSUS — {target_ticker}</div>
    <div style="display:flex; gap:24px; margin-bottom:12px;">
        <span><span class="badge badge-bull">BULLISH</span> &nbsp; <b style="color:#fff">{bull_n}</b> <span style="color:#aaa">/ {total}</span></span>
        <span><span class="badge badge-bear">BEARISH</span> &nbsp; <b style="color:#fff">{bear_n}</b> <span style="color:#aaa">/ {total}</span></span>
        <span><span class="badge badge-neut">NEUTRAL</span> &nbsp; <b style="color:#fff">{neut_n}</b> <span style="color:#aaa">/ {total}</span></span>
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
</div>
""", unsafe_allow_html=True)

            # ── 5d. Investor Cards ───────────────────────────────────────────
            st.markdown("### 🗣️ Investor Perspectives")
            col_left, col_right = st.columns(2)

            def signal_to_badge(sig):
                if sig == "BULLISH": return '<span class="badge badge-bull">▲ BULLISH</span>'
                if sig == "BEARISH": return '<span class="badge badge-bear">▼ BEARISH</span>'
                return '<span class="badge badge-neut">◆ NEUTRAL</span>'

            def signal_to_class(sig):
                if sig == "BULLISH": return "agent-card-bull"
                if sig == "BEARISH": return "agent-card-bear"
                return "agent-card-neut"

            def signal_to_bar_class(sig):
                if sig == "BULLISH": return "conf-bar-fill-bull"
                if sig == "BEARISH": return "conf-bar-fill-bear"
                return "conf-bar-fill-neut"

            for i, (key, icon, name, role) in enumerate(agents_order):
                data = result.get(key, {})
                sig  = data.get("signal", "NEUTRAL")
                conf = data.get("confidence", 50)
                text = data.get("reasoning", "")

                card_html = f"""
<div class="agent-card {signal_to_class(sig)}">
    <div class="agent-name">{icon} {name} <span style="color:#aaa; font-weight:400; font-size:0.8rem;">· {role}</span></div>
    {signal_to_badge(sig)}
    <div class="conf-bar-bg"><div class="{signal_to_bar_class(sig)}" style="width:{conf}%;"></div></div>
    <div class="agent-conf">Conviction: {conf}%</div>
    <div class="agent-text">{text}</div>
</div>
"""
                (col_left if i % 2 == 0 else col_right).markdown(card_html, unsafe_allow_html=True)

            # ── 5e. Final Verdict ────────────────────────────────────────────
            st.markdown("### 🏦 Portfolio Manager's Final Verdict")
            mgr     = result.get("Manager", {})
            verdict = mgr.get("verdict", "HOLD")
            m_conf  = mgr.get("confidence", 50)
            action  = mgr.get("action", "")
            rationale = mgr.get("rationale", "")

            v_class = {"BUY": "verdict-buy", "SELL": "verdict-sell"}.get(verdict, "verdict-hold")
            l_class = {"BUY": "verdict-label-buy", "SELL": "verdict-label-sell"}.get(verdict, "verdict-label-hold")
            v_icon  = {"BUY": "📗", "SELL": "📕"}.get(verdict, "📒")

            st.markdown(f"""
<div class="{v_class}">
    <div class="verdict-label {l_class}">{v_icon} {verdict}</div>
    <div class="verdict-sub"><b>{action}</b><br><br>{rationale}</div>
    <div class="verdict-conf">Portfolio Manager Conviction: {m_conf}%</div>
</div>
""", unsafe_allow_html=True)

        except Exception as e:
            st.error(f"An error occurred: {e}")

# ── 6. Footer ─────────────────────────────────────────────────────────────────
st.markdown("""
<div class="disclaimer">
    ⚠️ <b>Disclaimer:</b> This AI analysis is a simulation based on public news headlines only.
    Not financial advice. Always do your own research before making investment decisions.
</div>
""", unsafe_allow_html=True)

st.markdown("""
<div style='text-align:center; margin-top:20px;'>
    <img src="https://hits.seeyoufarm.com/api/count/incr/badge.svg?url=https%3A%2F%2Fainvest-jnpzmtom62rulztvu24d6c.streamlit.app&count_bg=%230079C1&title_bg=%23303030&icon=eye.svg&icon_color=%23FFFFFF&title=Today&edge_flat=true" alt="visitor count"/>
</div>
""", unsafe_allow_html=True)

st.markdown("<br>", unsafe_allow_html=True)
col1, col2, col3 = st.columns([1, 1.5, 1])
with col2:
    st.link_button("💸 Pay $1 to Insult Me", "https://www.paypal.com/ncp/payment/A3Q3JEV6WRXSG", use_container_width=True)
