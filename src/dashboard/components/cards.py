"""Reusable card components."""

import streamlit as st
from datetime import datetime
from typing import Optional, Dict, Any
import random

from src.dashboard.shared.utils import action_badge, sentiment_badge, render_confidence_bar, format_timestamp, time_ago


class SignalCard:
    """Card component for displaying trade signals."""
    
    @staticmethod
    def render(signal: 'TradeSignal', expanded: bool = False):
        """Render a signal card."""
        with st.container():
            col1, col2 = st.columns([3, 1])
            
            with col1:
                st.markdown(f"### {signal.symbol}")
                st.markdown(action_badge(signal.action), unsafe_allow_html=True)
            
            with col2:
                st.markdown("**Confidence**")
                st.markdown(render_confidence_bar(signal.confidence), unsafe_allow_html=True)
            
            st.divider()
            
            col1, col2, col3 = st.columns(3)
            with col1:
                st.metric("Current Price", f"${signal.current_price:,.2f}")
            with col2:
                if signal.entry_price:
                    st.metric("Entry Price", f"${signal.entry_price:,.2f}")
            with col3:
                st.metric("Timestamp", format_timestamp(signal.timestamp))
            
            if signal.factors:
                st.markdown("**Factor Analysis**")
                cols = st.columns(len(signal.factors))
                for i, (factor, score) in enumerate(signal.factors.items()):
                    with cols[i]:
                        st.markdown(f"_{factor.title()}_")
                        st.progress(score, text=f"{score:.0%}")
            
            if expanded:
                st.divider()
                st.markdown("**AI Explanation**")
                st.info(signal.explanation)
                
                if signal.stop_loss and signal.take_profit:
                    col1, col2 = st.columns(2)
                    with col1:
                        st.metric("Stop Loss", f"${signal.stop_loss:,.2f}")
                    with col2:
                        st.metric("Take Profit", f"${signal.take_profit:,.2f}")


class NewsCard:
    """Card component for displaying news articles."""
    
    @staticmethod
    def render(article: Dict[str, Any], key: str = None):
        """Render a news card."""
        with st.expander(f"📰 {article.get('title', 'Untitled')}", expanded=False):
            col1, col2 = st.columns([3, 1])
            
            with col1:
                if article.get('source'):
                    st.markdown(f"**Source:** {article['source']}")
                if article.get('published'):
                    st.caption(f"📅 {time_ago(article['published'])}")
            
            with col2:
                if article.get('sentiment'):
                    st.markdown(sentiment_badge(article['sentiment']), unsafe_allow_html=True)
            
            if article.get('summary'):
                st.markdown(article['summary'])
            
            if article.get('url'):
                st.markdown(f"[Read more →]({article['url']})")


class MetricCard:
    """Card component for displaying metrics."""
    
    @staticmethod
    def render(label: str, value: str, delta: str = None, help_text: str = None):
        """Render a metric card."""
        st.metric(label=label, value=value, delta=delta, help=help_text)
    
    @staticmethod
    def render_row(metrics: list):
        """Render a row of metric cards."""
        cols = st.columns(len(metrics))
        for i, (label, value, delta) in enumerate(metrics):
            with cols[i]:
                st.metric(label=label, value=value, delta=delta)


class PortfolioCard:
    """Card component for portfolio display."""
    
    @staticmethod
    def render_position(position: Dict[str, Any]):
        """Render a position card."""
        with st.container():
            col1, col2, col3, col4 = st.columns([2, 2, 1, 1])
            
            with col1:
                st.markdown(f"**{position.get('symbol', 'N/A')}**")
            
            with col2:
                amount = position.get('amount', 0)
                price = position.get('current_price', 0)
                st.markdown(f"${amount * price:,.2f}")
            
            with col3:
                pnl = position.get('pnl', 0)
                color = "green" if pnl >= 0 else "red"
                st.markdown(f":{color}[${pnl:,.2f}]")
            
            with col4:
                pnl_pct = position.get('pnl_pct', 0)
                color = "green" if pnl_pct >= 0 else "red"
                st.markdown(f":{color}[{pnl_pct:.1f}%]")
