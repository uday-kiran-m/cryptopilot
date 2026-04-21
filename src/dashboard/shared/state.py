"""Shared state management for dashboard."""

import streamlit as st
from datetime import datetime
from typing import Optional, Any
import json


class SessionState:
    """Manages persistent session state for the dashboard."""

    _initialized = False

    @classmethod
    def init(cls):
        """Initialize session state variables."""
        if cls._initialized:
            return

        defaults = {
            'chat_history': [],
            'chat_thread_id': datetime.now().strftime('%Y%m%d_%H%M%S'),
            'selected_symbol': 'BTCUSDT',
            'timeframe': '4h',
            'use_stubs': True,
            'last_analysis': None,
            'cached_news': [],
            'user_preferences': {
                'dark_mode': True,
                'notifications': True,
            },
            'brain_initialized': False,
            'brain_orchestrator': None,
            'brain_last_result': None,
            'brain_pending_trades': [],
            'brain_trade_history': [],
            'brain_portfolio': {
                'balance': 10000.0,
                'total_value': 10000.0,
                'total_pnl': 0.0,
                'positions': {},
            },
            'trading_interval_hours': 4.0,
            'trading_symbol': 'BTCUSDT',
            'initial_balance': 10000.0,
        }

        for key, value in defaults.items():
            if key not in st.session_state:
                st.session_state[key] = value

        cls._initialized = True
    
    @classmethod
    def get(cls, key: str, default: Any = None) -> Any:
        """Get a session state value."""
        cls.init()
        return st.session_state.get(key, default)
    
    @classmethod
    def set(cls, key: str, value: Any) -> None:
        """Set a session state value."""
        cls.init()
        st.session_state[key] = value
    
    @classmethod
    def add_chat_message(cls, role: str, content: str, metadata: Optional[dict] = None):
        """Add a message to chat history."""
        cls.init()
        message = {
            'role': role,
            'content': content,
            'timestamp': datetime.now().isoformat(),
            'metadata': metadata or {},
        }
        st.session_state.chat_history.append(message)
    
    @classmethod
    def get_chat_history(cls) -> list:
        """Get the full chat history."""
        cls.init()
        return st.session_state.chat_history
    
    @classmethod
    def clear_chat(cls):
        """Clear chat history."""
        cls.set('chat_history', [])
        cls.set('chat_thread_id', datetime.now().strftime('%Y%m%d_%H%M%S'))

    @classmethod
    def set_brain_result(cls, result: dict) -> None:
        """Store brain analysis result."""
        cls.set('brain_last_result', result)
        cls.set('last_analysis', datetime.now())

    @classmethod
    def get_brain_result(cls) -> Optional[dict]:
        """Get last brain analysis result."""
        return cls.get('brain_last_result')

    @classmethod
    def set_portfolio(cls, portfolio: dict) -> None:
        """Update portfolio from brain."""
        cls.set('brain_portfolio', portfolio)

    @classmethod
    def get_portfolio(cls) -> dict:
        """Get current portfolio."""
        return cls.get('brain_portfolio', {
            'balance': 10000.0,
            'total_value': 10000.0,
            'total_pnl': 0.0,
            'positions': {},
        })

    @classmethod
    def add_pending_trade(cls, trade: dict) -> None:
        """Add a trade to pending queue."""
        pending = cls.get('brain_pending_trades', [])
        pending.append(trade)
        cls.set('brain_pending_trades', pending)

    @classmethod
    def get_pending_trades(cls) -> list:
        """Get pending trades."""
        return cls.get('brain_pending_trades', [])

    @classmethod
    def add_executed_trade(cls, trade: dict) -> None:
        """Add an executed trade to history."""
        history = cls.get('brain_trade_history', [])
        history.append(trade)
        cls.set('brain_trade_history', history)

    @classmethod
    def get_trade_history(cls) -> list:
        """Get trade history."""
        return cls.get('brain_trade_history', [])


class CacheManager:
    """Simple cache for API responses."""
    
    _cache: dict = {}
    _timestamps: dict = {}
    
    @classmethod
    def get(cls, key: str, max_age_seconds: int = 300) -> Optional[Any]:
        """Get cached value if not expired."""
        if key not in cls._cache:
            return None
            
        timestamp = cls._timestamps.get(key)
        if timestamp is None:
            return None
            
        age = (datetime.now() - timestamp).total_seconds()
        if age > max_age_seconds:
            cls.invalidate(key)
            return None
            
        return cls._cache[key]
    
    @classmethod
    def set(cls, key: str, value: Any) -> None:
        """Set a cached value."""
        cls._cache[key] = value
        cls._timestamps[key] = datetime.now()
    
    @classmethod
    def invalidate(cls, key: str) -> None:
        """Invalidate a cached value."""
        cls._cache.pop(key, None)
        cls._timestamps.pop(key, None)
    
    @classmethod
    def clear(cls) -> None:
        """Clear all cached values."""
        cls._cache.clear()
        cls._timestamps.clear()


def init_session_state():
    """Legacy function for backwards compatibility."""
    SessionState.init()
