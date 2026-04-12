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
            'timeframe': '1h',
            'use_stubs': True,
            'last_analysis': None,
            'cached_news': [],
            'user_preferences': {
                'dark_mode': True,
                'notifications': True,
            },
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
