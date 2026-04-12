import pandas as pd
import numpy as np
from datetime import datetime
from typing import Optional

from src.core import get_logger
from src.core.models import OHLCVData, TechnicalIndicators

logger = get_logger("indicators")


def calculate_rsi(prices: list[float], period: int = 14) -> Optional[float]:
    """Calculate Relative Strength Index"""
    if len(prices) < period + 1:
        return None

    deltas = np.diff(prices)
    gains = np.where(deltas > 0, deltas, 0)
    losses = np.where(deltas < 0, -deltas, 0)

    avg_gain = np.mean(gains[-period:])
    avg_loss = np.mean(losses[-period:])

    if avg_loss == 0:
        return 100

    rs = avg_gain / avg_loss
    rsi = 100 - (100 / (1 + rs))
    return float(rsi)


def calculate_macd(
    prices: list[float], fast: int = 12, slow: int = 26, signal: int = 9
) -> tuple[Optional[float], Optional[float], Optional[float]]:
    """Calculate MACD (Moving Average Convergence Divergence)"""
    if len(prices) < slow:
        return None, None, None

    df = pd.Series(prices)
    ema_fast = df.ewm(span=fast, adjust=False).mean()
    ema_slow = df.ewm(span=slow, adjust=False).mean()

    macd_line = ema_fast - ema_slow
    signal_line = macd_line.ewm(span=signal, adjust=False).mean()
    histogram = macd_line - signal_line

    return (
        float(macd_line.iloc[-1]),
        float(signal_line.iloc[-1]),
        float(histogram.iloc[-1]),
    )


def calculate_bollinger_bands(
    prices: list[float], period: int = 20, std_dev: float = 2.0
) -> tuple[Optional[float], Optional[float], Optional[float]]:
    """Calculate Bollinger Bands"""
    if len(prices) < period:
        return None, None, None

    df = pd.Series(prices)
    middle = df.rolling(window=period).mean()
    std = df.rolling(window=period).std()

    upper = middle + (std * std_dev)
    lower = middle - (std * std_dev)

    return (
        float(upper.iloc[-1]),
        float(middle.iloc[-1]),
        float(lower.iloc[-1]),
    )


def calculate_ema(prices: list[float], period: int) -> Optional[float]:
    """Calculate Exponential Moving Average"""
    if len(prices) < period:
        return None

    df = pd.Series(prices)
    ema = df.ewm(span=period, adjust=False).mean()
    return float(ema.iloc[-1])


def calculate_atr(
    ohlcv_data: list[OHLCVData], period: int = 14
) -> Optional[float]:
    """Calculate Average True Range"""
    if len(ohlcv_data) < period + 1:
        return None

    highs = [d.high for d in ohlcv_data]
    lows = [d.low for d in ohlcv_data]
    closes = [d.close for d in ohlcv_data]

    tr = []
    for i in range(1, len(ohlcv_data)):
        high_low = highs[i] - lows[i]
        high_close = abs(highs[i] - closes[i - 1])
        low_close = abs(lows[i] - closes[i - 1])
        tr.append(max(high_low, high_close, low_close))

    if len(tr) < period:
        return None

    atr = np.mean(tr[-period:])
    return float(atr)


def calculate_all_indicators(
    symbol: str, ohlcv_data: list[OHLCVData]
) -> TechnicalIndicators:
    """Calculate all technical indicators for a symbol"""
    if not ohlcv_data:
        return TechnicalIndicators(symbol=symbol, timestamp=datetime.now())

    prices = [d.close for d in ohlcv_data]

    rsi = calculate_rsi(prices)
    macd, macd_signal, macd_hist = calculate_macd(prices)
    bollinger_upper, bollinger_middle, bollinger_lower = calculate_bollinger_bands(prices)
    ema_20 = calculate_ema(prices, 20)
    ema_50 = calculate_ema(prices, 50)
    ema_200 = calculate_ema(prices, 200)
    atr = calculate_atr(ohlcv_data)

    return TechnicalIndicators(
        symbol=symbol,
        timestamp=datetime.now(),
        rsi=rsi,
        macd=macd,
        macd_signal=macd_signal,
        macd_histogram=macd_hist,
        bollinger_upper=bollinger_upper,
        bollinger_middle=bollinger_middle,
        bollinger_lower=bollinger_lower,
        ema_20=ema_20,
        ema_50=ema_50,
        ema_200=ema_200,
        atr=atr,
    )


def interpret_rsi(rsi: Optional[float]) -> str:
    """Interpret RSI value"""
    if rsi is None:
        return "Unknown"
    if rsi >= 70:
        return "Overbought"
    elif rsi <= 30:
        return "Oversold"
    return "Neutral"


def interpret_macd(macd: float, signal: float, histogram: float) -> str:
    """Interpret MACD value"""
    if histogram > 0 and macd > signal:
        return "Bullish"
    elif histogram < 0 and macd < signal:
        return "Bearish"
    return "Neutral"


def interpret_bollinger(
    price: float, upper: float, middle: float, lower: float
) -> str:
    """Interpret Bollinger Bands position"""
    if price >= upper:
        return "Near Upper Band (Overbought)"
    elif price <= lower:
        return "Near Lower Band (Oversold)"
    elif price > middle:
        return "Above Middle Band"
    return "Below Middle Band"


def get_signal_from_indicators(indicators: TechnicalIndicators, price: float) -> dict:
    """Generate a basic signal from technical indicators"""
    signals = []
    weights = {}

    if indicators.rsi:
        rsi_interp = interpret_rsi(indicators.rsi)
        signals.append(("RSI", indicators.rsi, rsi_interp))
        weights["rsi"] = 1.0

    if indicators.macd is not None:
        macd_interp = interpret_macd(
            indicators.macd, indicators.macd_signal, indicators.macd_histogram
        )
        signals.append(("MACD", indicators.macd_histogram, macd_interp))
        weights["macd"] = 1.0

    if indicators.bollinger_upper:
        bb_interp = interpret_bollinger(
            price, indicators.bollinger_upper, indicators.bollinger_middle, indicators.bollinger_lower
        )
        signals.append(("Bollinger", price, bb_interp))
        weights["bollinger"] = 0.5

    bullish_count = sum(1 for _, _, interp in signals if "Bullish" in interp or "Oversold" in interp)
    bearish_count = sum(1 for _, _, interp in signals if "Bearish" in interp or "Overbought" in interp)

    if bullish_count > bearish_count:
        base_signal = "BUY"
    elif bearish_count > bullish_count:
        base_signal = "SELL"
    else:
        base_signal = "HOLD"

    return {
        "signals": signals,
        "base_signal": base_signal,
        "weights": weights,
    }
