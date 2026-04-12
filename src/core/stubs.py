"""AI Stubs System - Mock AI responses for development/testing."""

import random
from datetime import datetime
from typing import Optional
from enum import Enum

from src.core.models import TradeAction, TradeSignal


class StubMode(str, Enum):
    ENABLED = "enabled"
    DISABLED = "disabled"
    MIXED = "mixed"


USE_STUBS = True

TRADING_EXPLANATIONS = {
    TradeAction.BUY: [
        "Strong bullish momentum detected across multiple timeframes. RSI showing oversold conditions at {rsi:.1f} with MACD crossover confirmation. Sentiment analysis indicates positive market sentiment with key institutional buying patterns.",
        "Technical indicators align favorably: EMA 20 crossed above EMA 50, suggesting upward trend acceleration. Volume spike of {volume:.1f}x average confirms the move. Risk-reward ratio of 1:2.5 makes this an attractive entry point.",
        "Multiple confirmation signals present. Bollinger Bands showing compression before expansion pattern. On-chain metrics show decreasing exchange inflows. Support level at ${support:.2f} holding strong.",
    ],
    TradeAction.SELL: [
        "Overbought conditions detected. RSI at {rsi:.1f} indicates potential pullback. Major resistance at ${resistance:.2f} limiting upside potential. Taking profits at {profit:.1f}% gain.",
        "Bearish divergence forming on MACD histogram. Volume declining on recent uptrend suggests weakening momentum. Key support breach imminent - reducing exposure.",
        "Risk management triggered: stop-loss at ${stop:.2f} activated. Adverse news catalyst identified. Portfolio allocation rebalancing in progress.",
    ],
    TradeAction.HOLD: [
        "Mixed signals across indicators. No clear directional bias. Waiting for confirmation - current volatility {volatility:.1f}% exceeds threshold. Recommend staying flat until clearer setup.",
        "Sideways consolidation phase detected. Support at ${support:.2f}, resistance at ${resistance:.2f}. Insufficient volume for breakout confirmation. Maintaining current positions.",
        "Neutral stance warranted: conflicting signals from technical ({tech_score:.0f}%) and sentiment ({sentiment_score:.0f}%) analysis. Time to be cautious.",
    ],
}

STUB_SENTIMENTS = [
    ("bullish", 0.75, 0.15),
    ("bearish", 0.20, 0.10),
    ("neutral", 0.50, 0.05),
    ("very_bullish", 0.90, 0.05),
    ("very_bearish", 0.10, 0.08),
]

CHAT_RESPONSES = [
    "Based on current market conditions, I'd recommend monitoring the key support levels closely. BTC is showing strength above ${:.2f} with healthy volume.",
    "The technical setup suggests a cautious approach. While momentum is positive, the RSI at {:.1f} indicates we should wait for a pullback before adding positions.",
    "Looking at the portfolio, your current allocation is well-balanced. Consider taking partial profits on ETH given the recent 15% gains.",
    "Historical patterns suggest this could be a good entry point. However, always consider your risk tolerance - I'd suggest sizing positions at no more than 5% of portfolio.",
    "The news sentiment has shifted positive over the past 24 hours, with major outlets highlighting increased institutional interest. This could support higher prices.",
    "From a risk management perspective, ensure your stop-losses are placed at ${:.2f} or lower to protect against adverse moves.",
]


def get_stub_explanation(action: TradeAction, **kwargs) -> str:
    """Generate a realistic trading explanation with injected values."""
    explanations = TRADING_EXPLANATIONS.get(action, TRADING_EXPLANATIONS[TradeAction.HOLD])
    template = random.choice(explanations)
    
    defaults = {
        'rsi': random.uniform(25, 75),
        'volume': random.uniform(1.2, 3.0),
        'support': kwargs.get('price', 50000) * 0.95,
        'resistance': kwargs.get('price', 50000) * 1.05,
        'profit': random.uniform(5, 20),
        'stop': kwargs.get('price', 50000) * 0.97,
        'volatility': random.uniform(2, 8),
        'tech_score': random.uniform(40, 70),
        'sentiment_score': random.uniform(40, 70),
    }
    defaults.update(kwargs)
    return template.format(**{k: v for k, v in defaults.items() if k in template})


def get_stub_sentiment():
    """Return random sentiment values."""
    label = random.choice(STUB_SENTIMENTS)
    return {
        'label': label[0],
        'score': label[1],
        'confidence': label[2],
    }


def get_stub_chat_response(context: str) -> str:
    """Generate realistic chat response based on context."""
    response = random.choice(CHAT_RESPONSES)
    
    if '{:.2f}' in response:
        price = random.uniform(45000, 65000)
        return response.format(price)
    elif '{:.1f}' in response:
        rsi = random.uniform(40, 70)
        return response.format(rsi)
    return response


def get_stub_signal(symbol: str, action: Optional[TradeAction] = None) -> TradeSignal:
    """Generate a realistic stub trade signal."""
    if action is None:
        action = random.choice(list(TradeAction))
    
    price = random.uniform(30000, 70000)
    confidence = random.uniform(0.55, 0.92)
    
    explanation = get_stub_explanation(
        action,
        price=price,
        rsi=random.uniform(30, 70),
        volume=random.uniform(1.0, 2.5),
    )
    
    return TradeSignal(
        symbol=symbol,
        action=action,
        confidence=confidence,
        price=price,
        timestamp=datetime.now(),
        explanation=explanation,
        factors={
            'technical': random.uniform(0.3, 0.9),
            'sentiment': random.uniform(0.3, 0.9),
            'risk': random.uniform(0.2, 0.8),
        },
        agent_reasoning=[
            "Technical analysis confirms momentum shift",
            "Sentiment indicators show positive bias",
            "Risk metrics within acceptable limits",
        ],
    )


def should_use_stub() -> bool:
    """Check if stubs should be used based on environment/config."""
    import os
    return os.getenv('USE_AI_STUBS', 'true').lower() == 'true'
