from datetime import datetime
from enum import Enum
from pydantic import BaseModel, Field
from typing import Optional


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


# Raw OHLCV data from exchange
class OHLCVData(BaseModel):
    timestamp: datetime
    open: float
    high: float
    low: float
    close: float
    volume: float
    quote_volume: Optional[float] = None


# Snapshot of current price
class PriceSnapshot(BaseModel):
    open: float
    high: float
    low: float
    close: float


# Trend analysis
class TrendData(BaseModel):
    pct_change_50: float
    pct_change_10: float
    market_structure: str  # "Uptrend", "Downtrend", "Sideways/Ranging"


# RSI data
class RSIData(BaseModel):
    current: float
    prev: float
    avg_50: float
    trend: str  # "Increasing", "Decreasing"


# Bollinger Bands data
class BollingerData(BaseModel):
    upper: float
    lower: float
    position_label: str  # "Above Upper Band", "Below Lower Band", etc.


# EMA data
class EMAData(BaseModel):
    value: float
    price_rel: str  # "Price Above EMA", "Price Below EMA"
    slope: str  # "Increasing", "Decreasing"


# Price levels
class PriceLevels(BaseModel):
    high_50: float
    low_50: float
    high_20: float
    low_20: float
    high_55: float
    low_55: float


# Volume data
class VolumeData(BaseModel):
    current: float
    avg_50: float
    is_spike: bool


# Volatility data
class VolatilityData(BaseModel):
    atr: float


# Stochastic data
class StochasticData(BaseModel):
    current: float


# Complete market data packet for analyst
class MarketDataPacket(BaseModel):
    snapshot: PriceSnapshot
    trends: TrendData
    rsi: RSIData
    bands: BollingerData
    ema: EMAData
    levels: PriceLevels
    volume: VolumeData
    volatility: VolatilityData
    stochastic: StochasticData
    asset_name: str = "BTCUSDT"
    timestamp: datetime = Field(default_factory=datetime.now)


# Sentiment analysis result
class SentimentResult(BaseModel):
    symbol: str
    score: float  # 0.0 to 1.0 (0=fear, 0.5=neutral, 1=greed)
    timestamp: datetime = Field(default_factory=datetime.now)
    source: str = "stub"


# Analyst signal from brain agent
class AnalystSignal(BaseModel):
    signal: str = Field(description="Must be BUY, SELL, or HOLD")
    confidence: float = Field(description="Score between 0 and 1")
    strategy_used: str = Field(description="Which strategy snippet was applied")
    reasoning: str = Field(description="Brief technical justification")
    internal_monologue: str = Field(description="The full step-by-step thought process")
    entry_condition: str = Field(description="The market conditions when to trade")
    exit_condition: str = Field(description="The market conditions for when to exit the trade")
    valid_till: str = Field(description="Duration till when to keep searching for entry condition")
    asset_name: str = Field(description="Name")


# Risk assessment from risk manager
class RiskAssessment(BaseModel):
    asset_name: str
    signal: str
    entry_condition: str
    exit_condition: str
    target: float
    stop_loss: float
    position_size: float  # USD notional
    timeframe: str
    audit_summary: str
    valid_until: str
    risk_score: int = 5
    is_approved: bool = True


# Trade recommendation to be queued
class TradeRecommendation(BaseModel):
    id: str = Field(default_factory=lambda: datetime.now().strftime("%Y%m%d%H%M%S"))
    timestamp: datetime = Field(default_factory=datetime.now)
    asset_name: str
    signal: TradeAction
    entry_price: float
    position_size: float
    stop_loss: float
    take_profit: float
    confidence: float
    strategy_used: str
    reasoning: str
    status: str = "pending"  # pending, executed, cancelled, rejected


# Portfolio position
class Position(BaseModel):
    symbol: str
    quantity: float
    entry_price: float
    current_price: float
    stop_loss: Optional[float] = None
    take_profit: Optional[float] = None
    unrealized_pnl: float = 0.0
    unrealized_pnl_percent: float = 0.0

    def update(self, current_price: float):
        self.current_price = current_price
        self.unrealized_pnl = (current_price - self.entry_price) * self.quantity
        if self.entry_price > 0:
            self.unrealized_pnl_percent = ((current_price - self.entry_price) / self.entry_price) * 100


# Portfolio state
class Portfolio(BaseModel):
    balance: float
    positions: dict[str, Position] = Field(default_factory=dict)
    total_value: float = 0.0
    total_pnl: float = 0.0
    total_pnl_percent: float = 0.0

    def calculate_total_value(self, prices: dict[str, float]):
        positions_value = sum(
            pos.quantity * prices.get(symbol, pos.current_price)
            for symbol, pos in self.positions.items()
        )
        self.total_value = self.balance + positions_value
        self.total_pnl = self.total_value - 10000.0
        if self.total_value > 0:
            self.total_pnl_percent = (self.total_pnl / 10000.0) * 100


# Analysis cycle result
class AnalysisResult(BaseModel):
    timestamp: datetime = Field(default_factory=datetime.now)
    symbol: str
    market_data: MarketDataPacket
    sentiment_score: float
    analyst_signal: AnalystSignal
    risk_assessment: RiskAssessment
    recommendation: Optional[TradeRecommendation] = None
    error: Optional[str] = None