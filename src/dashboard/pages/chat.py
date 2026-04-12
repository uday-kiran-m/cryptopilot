"""Conversational AI chat page with persistent history."""

import streamlit as st
from datetime import datetime
from typing import List, Dict, Any, Optional
import random

from src.dashboard.shared.database import Database
from src.core.stubs import get_stub_chat_response


SUGGESTED_QUERIES = [
    "What's the current market outlook for BTC?",
    "Should I take profits on my ETH position?",
    "What factors drove yesterday's signal?",
    "Analyze my portfolio risk",
    "What's the sentiment on Solana?",
    "Explain the latest trading decision",
    "What are the key support levels?",
    "How has the AI performed this week?",
]


def render_message(message: Dict[str, Any]):
    """Render a chat message."""
    role = message.get('role', 'user')
    content = message.get('content', '')
    timestamp = message.get('timestamp', '')
    
    if isinstance(timestamp, str):
        try:
            ts = datetime.fromisoformat(timestamp)
            timestamp = ts.strftime("%H:%M")
        except:
            timestamp = ""
    
    if role == 'user':
        with st.chat_message("user", avatar="👤"):
            st.markdown(content)
            if timestamp:
                st.caption(timestamp)
    else:
        with st.chat_message("assistant", avatar="🤖"):
            st.markdown(content)
            if timestamp:
                st.caption(timestamp)


def generate_context_aware_response(user_message: str, context: Dict[str, Any]) -> str:
    """Generate a context-aware chat response using stubs."""
    user_lower = user_message.lower()
    
    responses = {
        'market': [
            "Based on current market analysis, Bitcoin is showing mixed signals. The 4-hour chart shows a potential consolidation phase with resistance at $52,000 and support at $48,000. I'd recommend waiting for a breakout confirmation before taking action.",
            "Looking at the technical picture, we're seeing some interesting developments. RSI is neutral at 48, which suggests room for movement in either direction. Volume has been declining over the past 24 hours, indicating market indecision.",
        ],
        'portfolio': [
            "Your portfolio currently has a balanced allocation across major cryptocurrencies. BTC represents 45%, ETH 30%, and SOL 25%. The overall risk profile is moderate. Would you like me to suggest any rebalancing?",
            "Looking at your positions, ETH has gained 12% since entry, which is a good time to consider taking some profits. However, the trend still appears bullish, so I'd suggest a partial exit rather than closing the entire position.",
        ],
        'sentiment': [
            "Current market sentiment is cautiously optimistic. News coverage has been predominantly positive over the past 48 hours, with major outlets highlighting increased institutional interest. However, we should remain vigilant for any negative catalysts.",
            "The sentiment analysis shows a shift from neutral to slightly bullish. Social media mentions of Bitcoin have increased by 15% this week, with generally positive framing. This could support further upside.",
        ],
        'signal': [
            "The latest trading signal was generated based on multiple confirmations: RSI dipped below 30 (oversold), MACD showed a bullish crossover, and news sentiment turned positive. The confidence level was 78% for a BUY recommendation.",
            "Yesterday's signal was driven primarily by technical factors (45% weight) and sentiment analysis (35% weight). The risk manager flagged moderate volatility, resulting in a conservative position size.",
        ],
        'risk': [
            "Your current portfolio risk is within acceptable parameters. Value at Risk (VaR) is estimated at 5.2%, which is below our 10% threshold. Maximum drawdown potential is estimated at 8% in a worst-case scenario.",
            "Risk metrics look favorable: Sharpe ratio of 1.4, maximum position size at 8% of portfolio, and adequate diversification across assets. I'd recommend maintaining current allocations.",
        ],
        'default': [
            "That's an interesting question. Based on my analysis, I'd recommend reviewing the current market conditions and your risk tolerance before making any decisions. Would you like me to provide a detailed analysis?",
            "I've analyzed your question and prepared a response. The key factors to consider are current market conditions, your portfolio allocation, and risk tolerance. Let me know if you'd like me to elaborate on any specific aspect.",
            "Great question! Let me break this down for you. The current market environment suggests we should be cautious but optimistic. Recent data shows increased institutional interest and stable technical indicators.",
        ],
    }
    
    if 'market' in user_lower or 'btc' in user_lower or 'bitcoin' in user_lower or 'outlook' in user_lower:
        return random.choice(responses['market'])
    elif 'portfolio' in user_lower or 'position' in user_lower or 'allocation' in user_lower:
        return random.choice(responses['portfolio'])
    elif 'sentiment' in user_lower or 'news' in user_lower or 'social' in user_lower:
        return random.choice(responses['sentiment'])
    elif 'signal' in user_lower or 'decision' in user_lower or 'explain' in user_lower or 'why' in user_lower:
        return random.choice(responses['signal'])
    elif 'risk' in user_lower or 'drawdown' in user_lower or 'var' in user_lower:
        return random.choice(responses['risk'])
    else:
        return random.choice(responses['default'])


def render_chat_page(symbol: str = "BTCUSDT", use_stubs: bool = True):
    """Render the chat page."""
    st.header("💬 Trading Assistant")
    st.markdown("Ask questions about the market, your portfolio, or trading decisions")
    
    db = Database()
    
    if 'chat_initialized' not in st.session_state:
        st.session_state.chat_initialized = True
        st.session_state.current_thread = datetime.now().strftime('%Y%m%d_%H%M%S')
        
        saved_messages = db.get_chat_history(st.session_state.current_thread)
        if saved_messages:
            st.session_state.chat_messages = [msg.to_dict() for msg in saved_messages]
        else:
            welcome_msg = {
                'role': 'assistant',
                'content': "👋 Hello! I'm your CryptoPilot trading assistant. I can help you understand market conditions, analyze your portfolio, or explain trading decisions. What would you like to know?",
                'timestamp': datetime.now().isoformat(),
            }
            st.session_state.chat_messages = [welcome_msg]
            db.save_chat_message(
                thread_id=st.session_state.current_thread,
                role='assistant',
                content=welcome_msg['content'],
            )
    
    messages = st.session_state.get('chat_messages', [])
    
    for message in messages:
        render_message(message)
    
    st.divider()
    
    col1, col2 = st.columns([4, 1])
    
    with col1:
        if prompt := st.chat_input("Ask about the market, portfolio, or trading..."):
            user_msg = {
                'role': 'user',
                'content': prompt,
                'timestamp': datetime.now().isoformat(),
            }
            st.session_state.chat_messages.append(user_msg)
            db.save_chat_message(
                thread_id=st.session_state.current_thread,
                role='user',
                content=prompt,
            )
            
            with st.chat_message("user", avatar="👤"):
                st.markdown(prompt)
            
            context = {
                'symbol': symbol,
                'portfolio': {'btc': 0.45, 'eth': 0.30, 'sol': 0.25},
            }
            
            response_text = generate_context_aware_response(prompt, context)
            
            assistant_msg = {
                'role': 'assistant',
                'content': response_text,
                'timestamp': datetime.now().isoformat(),
            }
            st.session_state.chat_messages.append(assistant_msg)
            db.save_chat_message(
                thread_id=st.session_state.current_thread,
                role='assistant',
                content=response_text,
            )
            
            with st.chat_message("assistant", avatar="🤖"):
                st.markdown(response_text)
    
    with col2:
        st.markdown("**Quick Questions**")
        for query in SUGGESTED_QUERIES[:4]:
            if st.button(query, key=f"suggest_{query[:20]}", use_container_width=True):
                st.session_state[f"query_{query[:20]}"] = True
                st.rerun()
    
    if st.session_state.get('show_chat_history', False):
        with st.expander("Chat History"):
            for i, msg in enumerate(messages):
                role_icon = "👤" if msg['role'] == 'user' else "🤖"
                st.markdown(f"{role_icon} **{msg['role'].title()}**: {msg['content'][:100]}...")
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        if st.button("🗑️ Clear Chat", use_container_width=True):
            st.session_state.chat_messages = []
            st.rerun()
    
    with col2:
        if st.button("📋 Show History", use_container_width=True):
            st.session_state.show_chat_history = not st.session_state.get('show_chat_history', False)
    
    with col3:
        if st.button("💾 Export Chat", use_container_width=True):
            import json
            chat_export = json.dumps(st.session_state.chat_messages, indent=2)
            st.download_button(
                label="Download JSON",
                data=chat_export,
                file_name=f"chat_export_{datetime.now().strftime('%Y%m%d')}.json",
                mime="application/json",
            )
