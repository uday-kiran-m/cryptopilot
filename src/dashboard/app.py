"""CryptoPilot Dashboard - Modular Streamlit Application."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

import asyncio
import json
import random
from datetime import datetime, timedelta

import streamlit as st
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots

from src.dashboard.shared.utils import set_page_config, inject_custom_css, action_badge, render_confidence_bar
from src.dashboard.shared.state import SessionState, CacheManager
from src.dashboard.shared.database import Database
from src.dashboard.pages import news, xai, chat, audit


st.set_page_config(
    page_title="CryptoPilot",
    page_icon="",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap');
    
    * {
        font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif;
    }
    
    .stApp {
        background: #0b0e11;
    }
    
    .main-header {
        background: linear-gradient(135deg, #1a1f25 0%, #0b0e11 100%);
        padding: 1.5rem 2rem;
        border-radius: 12px;
        margin-bottom: 1.5rem;
        border: 1px solid #1e2328;
    }
    
    .header-title {
        font-size: 2.8rem;
        font-weight: 700;
        color: #fff;
        letter-spacing: -1px;
    }
    
    .header-title span {
        background: linear-gradient(135deg, #0ecb81, #0eb88a);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        background-clip: text;
    }
    
    .header-subtitle {
        color: #848e9c;
        font-size: 0.9rem;
    }
    
    .coin-card {
        background: #161b22;
        border: 1px solid #1e2328;
        border-radius: 12px;
        padding: 1.5rem;
        margin-bottom: 1rem;
        transition: all 0.3s ease;
    }
    
    .coin-card:hover {
        border-color: #2a3038;
        box-shadow: 0 4px 20px rgba(0,0,0,0.3);
    }
    
    .coin-name {
        font-size: 1.4rem;
        font-weight: 600;
        color: #fff;
    }
    
    .coin-symbol {
        color: #848e9c;
        font-size: 0.85rem;
        margin-left: 8px;
    }
    
    .price-text {
        font-size: 1.8rem;
        font-weight: 700;
        color: #fff;
    }
    
    .positive { color: #0ecb81; }
    .negative { color: #f6465d; }
    
    .signal-badge {
        display: inline-block;
        padding: 6px 16px;
        border-radius: 20px;
        font-weight: 600;
        font-size: 0.9rem;
    }
    
    .signal-buy {
        background: rgba(14, 203, 129, 0.15);
        color: #0ecb81;
        border: 1px solid #0ecb81;
    }
    
    .signal-sell {
        background: rgba(246, 70, 93, 0.15);
        color: #f6465d;
        border: 1px solid #f6465d;
    }
    
    .signal-hold {
        background: rgba(255, 213, 0, 0.15);
        color: #ffd500;
        border: 1px solid #ffd500;
    }
    
    .metric-box {
        background: #161b22;
        border: 1px solid #1e2328;
        border-radius: 8px;
        padding: 1rem;
        text-align: center;
    }
    
    .metric-label {
        color: #848e9c;
        font-size: 0.75rem;
        text-transform: uppercase;
        letter-spacing: 0.5px;
        margin-bottom: 4px;
    }
    
    .metric-value {
        color: #fff;
        font-size: 1.2rem;
        font-weight: 600;
    }
    
    /* Sidebar styling */
    [data-testid="stSidebar"] {
        background: #161b22;
        border-right: 1px solid #1e2328;
    }
    
    /* Tab styling */
    .stTabs [data-baseweb="tab-list"] {
        gap: 8px;
    }
    
    .stTabs [data-baseweb="tab"] {
        background: #161b22;
        border-radius: 8px 8px 0 0;
        padding: 12px 24px;
        color: #848e9c;
    }
    
    .stTabs [data-baseweb="tab"]:hover {
        background: #1e2328;
    }
    
    .stTabs [aria-selected="true"] {
        background: #0ecb81 !important;
        color: #000 !important;
    }
    
    /* Button styling */
    .stButton > button {
        background: linear-gradient(135deg, #0ecb81 0%, #00b368 100%);
        color: white;
        border: none;
        border-radius: 8px;
        padding: 0.5rem 1.5rem;
        font-weight: 600;
        transition: all 0.2s ease;
    }
    
    .stButton > button:hover {
        background: linear-gradient(135deg, #00d68f 0%, #0ecb81 100%);
        transform: translateY(-1px);
    }
    
    /* Expander styling */
    .streamlit-expanderHeader {
        background: #161b22;
        border-radius: 8px;
        border: 1px solid #1e2328;
    }
    
    /* Hide default Streamlit elements */
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    
    /* Custom scrollbar */
    ::-webkit-scrollbar {
        width: 8px;
    }
    
    ::-webkit-scrollbar-track {
        background: #0b0e11;
    }
    
    ::-webkit-scrollbar-thumb {
        background: #2a3038;
        border-radius: 4px;
    }
</style>
""", unsafe_allow_html=True)

SessionState.init()


PAGES = {
    "📊 Markets": "markets",
    "🎯 Signals": "signals",
    "💼 Portfolio": "portfolio",
    "📰 News": "news",
    "🤖 Explainable AI": "xai",
    "💬 Chat": "chat",
    "📋 Audit": "audit",
}


def render_sidebar():
    """Render the sidebar navigation."""
    with st.sidebar:
        st.markdown("""
        <div class="main-header" style="text-align: center; margin-bottom: 1rem;">
            <div style="font-size: 1.5rem; margin-bottom: 0.5rem;">🚀</div>
            <div style="font-size: 1.5rem; font-weight: 700; color: #fff;">
                Crypto<span style="color: #0ecb81;">Pilot</span>
            </div>
        </div>
        """, unsafe_allow_html=True)
        
        st.divider()
        
        selected_page = st.radio(
            "Navigation",
            options=list(PAGES.keys()),
            index=0,
            label_visibility="collapsed"
        )
        
        st.divider()
        
        st.markdown("### Settings")
        
        use_stubs = st.checkbox("Use AI Stubs", value=True, help="Use mock AI responses for development")
        
        symbol = st.selectbox(
            "Primary Symbol",
            options=["BTCUSDT", "ETHUSDT", "SOLUSDT"],
            index=0
        )
        
        st.divider()
        
        st.markdown("### System Status")
        st.markdown("🟢 All Systems Operational")
        
        with st.expander("Debug Info"):
            st.write(f"Session: {st.session_state.get('chat_thread_id', 'N/A')[:8]}...")
            st.write(f"Cache size: {len(CacheManager._cache)}")
    
    return selected_page, symbol, use_stubs


def render_markets_page(symbol: str, use_stubs: bool):
    """Render the markets overview page."""
    st.markdown("""
    <div class="main-header">
        <div class="header-title">Market <span>Overview</span></div>
        <div class="header-subtitle">Real-time cryptocurrency prices and market data</div>
    </div>
    """, unsafe_allow_html=True)
    
    coins_data = {
        "BTCUSDT": {"name": "Bitcoin", "price": 52453.82, "change_24h": 2.34, "high_24h": 53100, "low_24h": 51200, "volume": "28.5B"},
        "ETHUSDT": {"name": "Ethereum", "price": 2934.51, "change_24h": 1.87, "high_24h": 2980, "low_24h": 2870, "volume": "15.2B"},
        "SOLUSDT": {"name": "Solana", "price": 98.42, "change_24h": -0.54, "high_24h": 101, "low_24h": 96.5, "volume": "3.1B"},
    }
    
    if use_stubs:
        for sym in coins_data:
            coins_data[sym]["price"] = coins_data[sym]["price"] * random.uniform(0.98, 1.02)
            coins_data[sym]["change_24h"] = random.uniform(-3, 4)
    
    col1, col2, col3 = st.columns(3)
    
    for i, (symbol, data) in enumerate(coins_data.items()):
        with [col1, col2, col3][i]:
            change_class = "positive" if data["change_24h"] >= 0 else "negative"
            change_sign = "+" if data["change_24h"] >= 0 else ""
            
            st.markdown(f"""
            <div class="coin-card">
                <div style="display: flex; justify-content: space-between; align-items: center;">
                    <div>
                        <span class="coin-name">{data['name']}</span>
                        <span class="coin-symbol">{symbol}</span>
                    </div>
                    <div class="signal-badge {'signal-buy' if data['change_24h'] >= 0 else 'signal-sell'}">
                        {change_sign}{data['change_24h']:.2f}%
                    </div>
                </div>
                <div class="price-text" style="margin: 1rem 0;">
                    ${data['price']:,.2f}
                </div>
                <div style="display: flex; justify-content: space-between; color: #848e9c; font-size: 0.85rem;">
                    <div>High: <span class="positive">${data['high_24h']:,.2f}</span></div>
                    <div>Low: <span class="negative">${data['low_24h']:,.2f}</span></div>
                    <div>Vol: ${data['volume']}</div>
                </div>
            </div>
            """, unsafe_allow_html=True)
    
    st.divider()
    
    if st.button("📊 Generate Stub Price Chart", use_container_width=True):
        pass
    
    df = generate_stub_ohlcv(100)
    
    fig = make_subplots(
        rows=2, cols=1,
        shared_xaxes=True,
        vertical_spacing=0.03,
        row_heights=[0.7, 0.3],
        subplot_titles=(f'{symbol} Price', 'Volume')
    )
    
    fig.add_trace(
        go.Candlestick(
            x=df['timestamp'],
            open=df['open'],
            high=df['high'],
            low=df['low'],
            close=df['close'],
            name='OHLC',
            increasing_line_color='#0ecb81',
            decreasing_line_color='#f6465d',
        ),
        row=1, col=1
    )
    
    colors = ['#0ecb81' if df.iloc[i]['close'] >= df.iloc[i]['open'] else '#f6465d' 
              for i in range(len(df))]
    
    fig.add_trace(
        go.Bar(x=df['timestamp'], y=df['volume'], name='Volume', marker_color=colors, opacity=0.7),
        row=2, col=1
    )
    
    fig.update_layout(
        height=500,
        showlegend=False,
        xaxis_rangeslider_visible=False,
        template='plotly_dark',
        paper_bgcolor='#0b0e11',
        plot_bgcolor='#0b0e11',
    )
    
    st.plotly_chart(fig, use_container_width=True)


def generate_stub_ohlcv(rows: int = 100):
    """Generate stub OHLCV data."""
    import pandas as pd
    
    base_price = 52000
    data = []
    timestamp = datetime.now() - timedelta(hours=rows)
    
    for _ in range(rows):
        open_price = base_price
        close_price = base_price * random.uniform(0.98, 1.02)
        high_price = max(open_price, close_price) * random.uniform(1.0, 1.02)
        low_price = min(open_price, close_price) * random.uniform(0.98, 1.0)
        volume = random.uniform(500, 2000)
        
        data.append({
            'timestamp': timestamp,
            'open': open_price,
            'high': high_price,
            'low': low_price,
            'close': close_price,
            'volume': volume,
        })
        
        base_price = close_price
        timestamp += timedelta(hours=1)
    
    return pd.DataFrame(data)


def render_signals_page(symbol: str, use_stubs: bool):
    """Render the trading signals page."""
    st.markdown("""
    <div class="main-header">
        <div class="header-title">Trading <span>Signals</span></div>
        <div class="header-subtitle">AI-powered trading recommendations</div>
    </div>
    """, unsafe_allow_html=True)
    
    col1, col2 = st.columns([3, 1])
    
    with col2:
        if st.button("🎯 Run Analysis", use_container_width=True, type="primary"):
            with st.spinner("Running multi-agent analysis..."):
                st.session_state.last_analysis = datetime.now()
                st.success("Analysis complete!")
    
    if st.button("🔄 Generate Stub Signal", use_container_width=True):
        st.session_state.last_analysis = datetime.now()
    
    if st.session_state.get('last_analysis'):
        st.caption(f"Last analysis: {st.session_state.last_analysis.strftime('%Y-%m-%d %H:%M:%S')}")
    
    st.divider()
    
    actions = ["BUY", "SELL", "HOLD"]
    action = random.choice(actions)
    confidence = random.uniform(0.55, 0.92)
    price = 52453.82 * random.uniform(0.98, 1.02)
    
    col1, col2 = st.columns([2, 1])
    
    with col1:
        st.markdown(f"### {symbol} Signal")
        
        badge_class = "signal-buy" if action == "BUY" else "signal-sell" if action == "SELL" else "signal-hold"
        st.markdown(f'<span class="signal-badge {badge_class}" style="font-size: 1.2rem; padding: 8px 24px;">{action}</span>', unsafe_allow_html=True)
        
        st.markdown(f"### ${price:,.2f}")
        
        st.markdown(f"**Confidence:** {confidence:.0%}")
        st.progress(confidence, text=f"{confidence:.0%} confidence")
    
    with col2:
        factors = {
            'Technical': random.uniform(0.3, 0.9),
            'Sentiment': random.uniform(0.3, 0.9),
            'Risk': random.uniform(0.3, 0.9),
        }
        
        st.markdown("### Factor Weights")
        for factor, weight in factors.items():
            st.markdown(f"**{factor}:** {weight:.0%}")
            st.progress(weight)
    
    st.divider()
    
    explanations = {
        "BUY": "Strong bullish momentum detected. RSI showing oversold conditions with MACD crossover confirmation. Volume spike of 2.3x average confirms the move. Risk-reward ratio of 1:2.5 makes this an attractive entry point.",
        "SELL": "Overbought conditions detected. RSI at 72 indicates potential pullback. Major resistance at $54,000 limiting upside potential. Taking profits at 12% gain.",
        "HOLD": "Mixed signals across indicators. No clear directional bias. Current volatility at 4.2% exceeds threshold. Recommend staying flat until clearer setup.",
    }
    
    st.markdown("### AI Explanation")
    st.info(explanations[action])
    
    st.divider()
    
    if action == "BUY":
        col1, col2 = st.columns(2)
        with col1:
            st.metric("Entry Price", f"${price:,.2f}")
        with col2:
            st.metric("Stop Loss", f"${price * 0.97:,.2f}", delta="-3.0%")
        
        col1, col2 = st.columns(2)
        with col1:
            st.metric("Take Profit 1", f"${price * 1.05:,.2f}", delta="+5.0%")
        with col2:
            st.metric("Take Profit 2", f"${price * 1.10:,.2f}", delta="+10.0%")


def render_portfolio_page(symbol: str, use_stubs: bool):
    """Render the portfolio page."""
    st.markdown("""
    <div class="main-header">
        <div class="header-title">Portfolio</span></div>
        <div class="header-subtitle">Your trading portfolio and positions</div>
    </div>
    """, unsafe_allow_html=True)
    
    total_value = 12453.82
    initial_balance = 10000.00
    pnl = total_value - initial_balance
    pnl_pct = (pnl / initial_balance) * 100
    
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric("Total Value", f"${total_value:,.2f}")
    with col2:
        st.metric("Available Balance", f"${3245.50:,.2f}")
    with col3:
        st.metric("P&L", f"${pnl:,.2f}", delta=f"{pnl_pct:+.1f}%")
    with col4:
        st.metric("Return", f"{pnl_pct:+.2f}%", delta="since inception")
    
    st.divider()
    
    positions = [
        {"symbol": "BTC", "amount": 0.15, "entry": 48500, "current": 52453.82},
        {"symbol": "ETH", "amount": 1.5, "entry": 2650, "current": 2934.51},
        {"symbol": "SOL", "amount": 25, "entry": 92, "current": 98.42},
    ]
    
    if use_stubs:
        for pos in positions:
            pos["current"] = pos["current"] * random.uniform(0.98, 1.02)
    
    st.markdown("### Holdings")
    
    cols = st.columns([1, 2, 2, 2, 2, 1])
    headers = ["Asset", "Amount", "Entry Price", "Current Price", "P&L", "Action"]
    for col, header in zip(cols, headers):
        with col:
            st.markdown(f"**{header}**")
    
    st.divider()
    
    for pos in positions:
        amount_usd = pos["amount"] * pos["current"]
        pnl_pos = (pos["current"] - pos["entry"]) * pos["amount"]
        pnl_pct_pos = ((pos["current"] - pos["entry"]) / pos["entry"]) * 100
        
        with st.container():
            cols = st.columns([1, 2, 2, 2, 2, 1])
            
            with cols[0]:
                st.markdown(f"**{pos['symbol']}**")
            with cols[1]:
                st.markdown(f"{pos['amount']:.4f}")
            with cols[2]:
                st.markdown(f"${pos['entry']:,.2f}")
            with cols[3]:
                st.markdown(f"${pos['current']:,.2f}")
            with cols[4]:
                color = "green" if pnl_pos >= 0 else "red"
                st.markdown(f":{color}[${pnl_pos:+,.2f} ({pnl_pct_pos:+.1f}%)]")
            with cols[5]:
                if st.button("Trade", key=f"trade_{pos['symbol']}"):
                    pass
    
    st.divider()
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("### Allocation")
        
        alloc_data = {
            'BTC': 0.15 * 52453.82,
            'ETH': 1.5 * 2934.51,
            'SOL': 25 * 98.42,
            'USDT': 3245.50,
        }
        
        fig = px.pie(
            values=list(alloc_data.values()),
            names=list(alloc_data.keys()),
            hole=0.4,
            color_discrete_sequence=['#0ecb81', '#3b82f6', '#f59e0b', '#848e9c'],
        )
        
        fig.update_layout(
            template='plotly_dark',
            paper_bgcolor='#0b0e11',
            height=300,
        )
        
        st.plotly_chart(fig, use_container_width=True)
    
    with col2:
        st.markdown("### Recent Trades")
        
        trades = [
            {"time": "2h ago", "symbol": "BTC", "action": "BUY", "amount": 0.05, "price": 51800},
            {"time": "6h ago", "symbol": "ETH", "action": "SELL", "amount": 0.5, "price": 2850},
            {"time": "1d ago", "symbol": "SOL", "action": "BUY", "amount": 10, "price": 95.50},
        ]
        
        for trade in trades:
            badge_class = "signal-buy" if trade['action'] == "BUY" else "signal-sell"
            st.markdown(f"""
            <div style="background: #161b22; padding: 0.75rem; border-radius: 8px; margin-bottom: 0.5rem;">
                <div style="display: flex; justify-content: space-between;">
                    <span>{trade['time']} - <strong>{trade['symbol']}</strong></span>
                    <span class="signal-badge {badge_class}" style="font-size: 0.7rem;">{trade['action']}</span>
                </div>
                <div style="color: #848e9c; font-size: 0.85rem;">
                    {trade['amount']} @ ${trade['price']:,.2f}
                </div>
            </div>
            """, unsafe_allow_html=True)


def main():
    """Main application entry point."""
    selected_page, symbol, use_stubs = render_sidebar()
    
    if selected_page == "📊 Markets":
        render_markets_page(symbol, use_stubs)
    elif selected_page == "🎯 Signals":
        render_signals_page(symbol, use_stubs)
    elif selected_page == "💼 Portfolio":
        render_portfolio_page(symbol, use_stubs)
    elif selected_page == "📰 News":
        news.render_news_page(symbol, use_stubs)
    elif selected_page == "🤖 Explainable AI":
        xai.render_xai_page(symbol, use_stubs)
    elif selected_page == "💬 Chat":
        chat.render_chat_page(symbol, use_stubs)
    elif selected_page == "📋 Audit":
        audit.render_audit_page(symbol, use_stubs)


if __name__ == "__main__":
    main()
