from datetime import datetime
from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field


class TradeAction(str, Enum):
    BUY = "BUY"
    SELL = "SELL"
    HOLD = "HOLD"


class TimeInterval(str, Enum):
    MINUTE_1 = "1m"
    MINUTE_5 = "5m"
    MINUTE_15 = "15m"
    HOUR_1 = "1h"
    HOUR_4 = "4h"
    DAY_1 = "1d"


class OHLCVData(BaseModel):
    timestamp: datetime
    open: float
    high: float
    low: float
    close: float
    volume: float
    quote_volume: Optional[float] = None


class TechnicalIndicators(BaseModel):
    symbol: str
    timestamp: datetime
    rsi: Optional[float] = None
    macd: Optional[float] = None
    macd_signal: Optional[float] = None
    macd_histogram: Optional[float] = None
    bollinger_upper: Optional[float] = None
    bollinger_middle: Optional[float] = None
    bollinger_lower: Optional[float] = None
    ema_20: Optional[float] = None
    ema_50: Optional[float] = None
    ema_200: Optional[float] = None
    atr: Optional[float] = None


class NewsArticle(BaseModel):
    title: str
    url: str
    source: str
    published_at: datetime
    sentiment_score: float = Field(ge=-1, le=1)
    sentiment_label: str
    affected_currencies: list[str] = []
    votes_positive: int = 0
    votes_negative: int = 0


class SentimentAnalysis(BaseModel):
    symbol: str
    timestamp: datetime
    overall_score: float = Field(ge=-1, le=1)
    bullish_count: int = 0
    bearish_count: int = 0
    neutral_count: int = 0
    articles: list[NewsArticle] = []
    weighted_sentiment: float = Field(ge=-1, le=1)


class TradeSignal(BaseModel):
    symbol: str
    action: TradeAction
    confidence: float = Field(ge=0, le=1)
    timestamp: datetime
    price: float
    factors: dict[str, float] = Field(default_factory=dict)
    explanation: str
    agent_reasoning: list[str] = Field(default_factory=list)
    technical_indicators: Optional[TechnicalIndicators] = None
    sentiment: Optional[SentimentAnalysis] = None


class PortfolioPosition(BaseModel):
    symbol: str
    quantity: float
    entry_price: float
    current_price: float
    unrealized_pnl: float = 0.0
    unrealized_pnl_percent: float = 0.0
    stop_loss: Optional[float] = None
    take_profit: Optional[float] = None

    def update(self, current_price: float):
        self.current_price = current_price
        self.unrealized_pnl = (current_price - self.entry_price) * self.quantity
        self.unrealized_pnl_percent = (
            (current_price - self.entry_price) / self.entry_price * 100
        )


class Portfolio(BaseModel):
    balance: float
    positions: dict[str, PortfolioPosition] = Field(default_factory=dict)
    total_value: float = 0.0
    total_pnl: float = 0.0
    total_pnl_percent: float = 0.0

    def calculate_total_value(self, prices: dict[str, float]):
        positions_value = sum(
            pos.quantity * prices.get(pos.symbol, pos.current_price)
            for pos in self.positions.values()
        )
        self.total_value = self.balance + positions_value
        self.total_pnl = self.total_value - 10000.0
        self.total_pnl_percent = (self.total_pnl / 10000.0) * 100


class AgentDecision(BaseModel):
    agent_name: str
    decision_type: str
    inputs: dict
    outputs: dict
    reasoning: str
    timestamp: datetime = Field(default_factory=datetime.now)
    confidence: Optional[float] = None
    metadata: dict = Field(default_factory=dict)
