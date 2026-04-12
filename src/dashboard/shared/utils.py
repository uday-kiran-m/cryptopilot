"""Shared utilities for dashboard pages."""

import streamlit as st
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional
import random


PRIMARY_GREEN = "#0ecb81"
ACCENT_BLUE = "#3b82f6"
WARNING_YELLOW = "#f59e0b"
DANGER_RED = "#ef4444"
CARD_BG = "#1a1a2e"
SECONDARY_BG = "#16213e"


def set_page_config():
    """Configure page settings."""
    st.set_page_config(
        page_title="CryptoPilot",
        page_icon="🚀",
        layout="wide",
        initial_sidebar_state="expanded",
    )


def inject_custom_css():
    """Inject custom CSS for dark theme styling."""
    st.markdown("""
    <style>
    /* Main theme */
    :root {
        --primary: #0ecb81;
        --secondary: #3b82f6;
        --bg-primary: #0f0f1a;
        --bg-secondary: #1a1a2e;
        --bg-card: #1a1a2e;
        --text-primary: #ffffff;
        --text-secondary: #a0a0b0;
        --border: #2a2a4a;
    }
    
    /* General styling */
    .stApp {
        background-color: var(--bg-primary);
    }
    
    /* Cards */
    .metric-card {
        background: var(--bg-card);
        border: 1px solid var(--border);
        border-radius: 12px;
        padding: 1.5rem;
        margin: 0.5rem 0;
    }
    
    .stCard {
        background: var(--bg-card) !important;
        border: 1px solid var(--border) !important;
        border-radius: 12px !important;
        padding: 1rem !important;
    }
    
    /* Buttons */
    .stButton > button {
        background: linear-gradient(135deg, #0ecb81 0%, #00b368 100%);
        color: white;
        border: none;
        border-radius: 8px;
        padding: 0.5rem 1.5rem;
        font-weight: 600;
    }
    
    .stButton > button:hover {
        background: linear-gradient(135deg, #00d68f 0%, #0ecb81 100%);
    }
    
    /* Badges */
    .badge {
        display: inline-block;
        padding: 0.25rem 0.75rem;
        border-radius: 9999px;
        font-size: 0.75rem;
        font-weight: 600;
        text-transform: uppercase;
    }
    
    .badge-buy { background: #0ecb81; color: #000; }
    .badge-sell { background: #ef4444; color: #fff; }
    .badge-hold { background: #f59e0b; color: #000; }
    .badge-bullish { background: #22c55e; color: #000; }
    .badge-bearish { background: #ef4444; color: #fff; }
    .badge-neutral { background: #6b7280; color: #fff; }
    
    /* Sidebar */
    .css-1d391kg {
        background: var(--bg-secondary);
    }
    
    /* Headers */
    h1, h2, h3 {
        color: var(--text-primary) !important;
    }
    
    /* Metrics */
    [data-testid="stMetricValue"] {
        color: var(--primary) !important;
    }
    
    /* Tabs */
    .stTabs [data-baseweb="tab-list"] {
        gap: 1rem;
    }
    
    .stTabs [data-baseweb="tab"] {
        background: var(--bg-secondary);
        border-radius: 8px 8px 0 0;
    }
    
    .stTabs [aria-selected="true"] {
        background: var(--primary) !important;
        color: #000 !important;
    }
    
    /* Expander */
    .streamlit-expanderHeader {
        background: var(--bg-card);
        border-radius: 8px;
    }
    
    /* Charts */
    .js-plotly-plot .plotly .modebar {
        background: transparent;
    }
    </style>
    """, unsafe_allow_html=True)


def render_sidebar():
    """Render the sidebar navigation."""
    with st.sidebar:
        st.markdown("### 🚀 CryptoPilot")
        st.divider()
        
        # Symbol selector
        symbol = st.selectbox(
            "Select Symbol",
            options=["BTCUSDT", "ETHUSDT", "SOLUSDT"],
            index=0
        )
        
        st.divider()
        
        # Settings
        st.markdown("#### Settings")
        use_stubs = st.checkbox("Use AI Stubs", value=True)
        
        st.divider()
        
        # Stats
        st.markdown("#### System Status")
        st.markdown("🟢 All Systems Operational")
        
        return symbol, use_stubs


def metric_card(label: str, value: str, delta: str = None, color: str = PRIMARY_GREEN):
    """Render a metric card."""
    st.metric(label=label, value=value, delta=delta)


def action_badge(action: str) -> str:
    """Generate HTML for action badge."""
    action_lower = action.lower()
    if action_lower == "buy":
        return '<span class="badge badge-buy">BUY</span>'
    elif action_lower == "sell":
        return '<span class="badge badge-sell">SELL</span>'
    else:
        return '<span class="badge badge-hold">HOLD</span>'


def sentiment_badge(sentiment: str) -> str:
    """Generate HTML for sentiment badge."""
    sentiment_lower = sentiment.lower()
    if "bullish" in sentiment_lower:
        return '<span class="badge badge-bullish">{}</span>'.format(sentiment.upper())
    elif "bearish" in sentiment_lower:
        return '<span class="badge badge-bearish">{}</span>'.format(sentiment.upper())
    else:
        return '<span class="badge badge-neutral">{}</span>'.format(sentiment.upper())


def render_confidence_bar(confidence: float, width: int = 300):
    """Render a confidence level bar."""
    percentage = int(confidence * 100)
    color = PRIMARY_GREEN if confidence > 0.6 else WARNING_YELLOW if confidence > 0.4 else DANGER_RED
    
    html = f"""
    <div style="width: {width}px; background: #2a2a4a; border-radius: 4px; overflow: hidden;">
        <div style="width: {percentage}%; background: {color}; padding: 4px 0; text-align: center; color: {'#000' if confidence > 0.5 else '#fff'}; font-size: 12px;">
            {percentage}%
        </div>
    </div>
    """
    return html


def format_timestamp(ts: datetime) -> str:
    """Format timestamp for display."""
    if isinstance(ts, str):
        ts = datetime.fromisoformat(ts)
    return ts.strftime("%Y-%m-%d %H:%M")


def time_ago(ts: datetime) -> str:
    """Get human-readable time difference."""
    if isinstance(ts, str):
        ts = datetime.fromisoformat(ts)
    
    diff = datetime.now() - ts
    
    if diff.days > 0:
        return f"{diff.days}d ago"
    elif diff.seconds >= 3600:
        return f"{diff.seconds // 3600}h ago"
    elif diff.seconds >= 60:
        return f"{diff.seconds // 60}m ago"
    else:
        return "Just now"
