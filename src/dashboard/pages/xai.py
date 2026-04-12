"""Explainable AI page with decision explanations and factor attribution."""

import streamlit as st
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional
import random

from src.dashboard.components.cards import SignalCard
from src.dashboard.components.charts import FactorChart, PriceChart
from src.dashboard.shared.utils import action_badge, render_confidence_bar, format_timestamp
from src.core.stubs import get_stub_signal, get_stub_explanation
from src.core.models import TradeAction, TradeSignal


def generate_stub_explanations(symbol: str) -> List[Dict[str, Any]]:
    """Generate realistic decision explanations."""
    decisions = []
    
    for i in range(5):
        action = random.choice(list(TradeAction))
        price = random.uniform(45000, 65000) if 'BTC' in symbol else random.uniform(2500, 3500)
        confidence = random.uniform(0.55, 0.92)
        
        factors = {
            'technical': random.uniform(0.3, 0.85),
            'sentiment': random.uniform(0.25, 0.80),
            'risk': random.uniform(0.30, 0.75),
        }
        
        explanation = get_stub_explanation(action, price=price)
        
        decisions.append({
            'id': 1000 - i,
            'symbol': symbol,
            'action': action,
            'confidence': confidence,
            'price': price,
            'factors': factors,
            'explanation': explanation,
            'timestamp': datetime.now() - timedelta(hours=i * 4),
        })
    
    return decisions


def render_xai_page(symbol: str = "BTCUSDT", use_stubs: bool = True):
    """Render the Explainable AI page."""
    st.header("🤖 Explainable AI")
    st.markdown("Understand how AI makes trading decisions")
    
    decisions = generate_stub_explanations(symbol)
    latest = decisions[0] if decisions else None
    
    col1, col2 = st.columns([1, 3])
    
    with col1:
        symbol_filter = st.selectbox("Symbol", ["BTCUSDT", "ETHUSDT", "SOLUSDT"])
        timeframe = st.selectbox("Timeframe", ["1h", "4h", "1d"])
        
        st.markdown("### About XAI")
        st.info("""
        **How it works:**
        - **Technical Analysis (30%)**: RSI, MACD, Bollinger Bands, moving averages
        - **Sentiment Analysis (35%)**: News sentiment, social media trends
        - **Risk Assessment (35%)**: Portfolio risk, position sizing, volatility
        """)
    
    with col2:
        if latest:
            st.markdown(f"### Latest Decision: {latest['symbol']}")
            
            cols = st.columns([1, 1, 1, 1])
            with cols[0]:
                st.markdown("**Action**")
                st.markdown(action_badge(latest['action'].value), unsafe_allow_html=True)
            with cols[1]:
                st.markdown("**Confidence**")
                st.markdown(render_confidence_bar(latest['confidence']), unsafe_allow_html=True)
            with cols[2]:
                st.markdown("**Price**")
                st.markdown(f"${latest['price']:,.2f}")
            with cols[3]:
                st.markdown("**Time**")
                st.markdown(format_timestamp(latest['timestamp']))
            
            st.divider()
            
            col1, col2 = st.columns([1, 1])
            
            with col1:
                st.markdown("### Factor Attribution")
                FactorChart.render_attribution(latest['factors'], title="")
                
                if st.checkbox("Show Radar Chart", value=False):
                    FactorChart.render_radar(latest['factors'], title="Signal Profile")
            
            with col2:
                st.markdown("### AI Explanation")
                st.info(latest['explanation'])
                
                st.markdown("#### Why This Decision?")
                st.markdown("""
                1. **Technical signals** indicate momentum shift
                2. **News sentiment** has turned positive
                3. **Risk metrics** are within acceptable limits
                4. **Entry point** offers favorable risk/reward
                """)
    
    st.divider()
    
    st.markdown("### Decision History")
    
    history_cols = st.columns([1, 1, 2, 2, 1])
    headers = ["Time", "Symbol", "Action", "Factors", "Confidence"]
    for col, header in zip(history_cols, headers):
        with col:
            st.markdown(f"**{header}**")
    
    st.divider()
    
    for decision in decisions:
        with st.container():
            cols = st.columns([1, 1, 2, 2, 1])
            
            with cols[0]:
                st.caption(format_timestamp(decision['timestamp']))
            with cols[1]:
                st.caption(decision['symbol'])
            with cols[2]:
                st.markdown(action_badge(decision['action'].value), unsafe_allow_html=True)
            with cols[3]:
                factor_str = " / ".join([f"{k}: {v:.0%}" for k, v in decision['factors'].items()])
                st.caption(factor_str)
            with cols[4]:
                st.caption(f"{decision['confidence']:.0%}")
            
            with st.expander("View Explanation"):
                FactorChart.render_attribution(decision['factors'], title="Factor Breakdown")
                st.markdown(f"> {decision['explanation']}")
    
    st.divider()
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("### Model Transparency")
        st.markdown("""
        **Decision Process:**
        1. Data Agent collects market data and news
        2. Sentiment Agent analyzes news sentiment
        3. Technical Agent calculates indicators
        4. Risk Manager assesses portfolio risk
        5. Signal Generator combines all factors
        6. LLM provides human-readable explanation
        """)
    
    with col2:
        st.markdown("### Confidence Calibration")
        
        calibration_data = {
            'Very Low (<40%)': 15,
            'Low (40-55%)': 25,
            'Medium (55-70%)': 35,
            'High (70-85%)': 40,
            'Very High (>85%)': 20,
        }
        
        for level, count in calibration_data.items():
            st.markdown(f"**{level}**: {count} decisions")
            st.progress(count / 100, text=f"{count}%")
