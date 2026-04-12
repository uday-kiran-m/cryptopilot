from crewai import Agent
from crewai.tools import BaseTool

from src.core import get_logger
from src.core.models import TechnicalIndicators, OHLCVData
from src.tools.indicators import (
    calculate_all_indicators,
    get_signal_from_indicators,
    interpret_rsi,
    interpret_macd,
    interpret_bollinger,
)

logger = get_logger("technical_agent")


class TechnicalIndicatorsTool(BaseTool):
    name: str = "technical_indicators_calculator"
    description: str = "Calculates technical indicators (RSI, MACD, Bollinger Bands, EMA)"

    async def _arun(self, symbol: str, ohlcv_data: list[dict]):
        try:
            data = [OHLCVData(**d) if isinstance(d, dict) else d for d in ohlcv_data]
            indicators = calculate_all_indicators(symbol, data)
            return indicators
        except Exception as e:
            logger.error(f"Error calculating indicators: {e}")
            return None


class SignalGenerationTool(BaseTool):
    name: str = "technical_signal_generator"
    description: str = "Generates trading signals from technical indicators"

    async def _arun(self, indicators: TechnicalIndicators, price: float):
        try:
            signal_data = get_signal_from_indicators(indicators, price)
            return signal_data
        except Exception as e:
            logger.error(f"Error generating signal: {e}")
            return {"base_signal": "HOLD", "signals": [], "weights": {}}


def create_technical_agent() -> Agent:
    """Create the technical analysis agent"""
    return Agent(
        role="Technical Analyst",
        goal="Analyze price charts and technical indicators to identify trading opportunities",
        backstory="""You are an expert technical analyst with deep knowledge of chart patterns,
        indicators, and market structure. You specialize in RSI, MACD, Bollinger Bands,
        and moving averages to identify potential trend changes and trading opportunities.
        Your analysis is grounded in established technical analysis principles.""",
        tools=[TechnicalIndicatorsTool(), SignalGenerationTool()],
        verbose=True,
        allow_delegation=False,
    )


def analyze_technical_indicators(indicators: TechnicalIndicators, price: float) -> dict:
    """Generate comprehensive technical analysis"""
    analysis = {
        "indicators": indicators,
        "interpretations": [],
        "signal": "HOLD",
        "confidence": 0.5,
        "key_levels": {},
    }

    if indicators.rsi:
        rsi_interp = interpret_rsi(indicators.rsi)
        analysis["interpretations"].append({
            "indicator": "RSI(14)",
            "value": f"{indicators.rsi:.2f}",
            "interpretation": rsi_interp,
        })
        if rsi_interp == "Overbought":
            analysis["signal"] = "SELL"
            analysis["confidence"] = max(analysis["confidence"], 0.6)
        elif rsi_interp == "Oversold":
            analysis["signal"] = "BUY"
            analysis["confidence"] = max(analysis["confidence"], 0.6)

    if indicators.macd is not None:
        macd_interp = interpret_macd(
            indicators.macd, indicators.macd_signal, indicators.macd_histogram
        )
        analysis["interpretations"].append({
            "indicator": "MACD(12,26,9)",
            "value": f"MACD: {indicators.macd:.2f}, Signal: {indicators.macd_signal:.2f}",
            "interpretation": macd_interp,
        })
        if macd_interp == "Bullish":
            if analysis["signal"] == "BUY":
                analysis["confidence"] = max(analysis["confidence"], 0.7)
        elif macd_interp == "Bearish":
            if analysis["signal"] == "SELL":
                analysis["confidence"] = max(analysis["confidence"], 0.7)

    if indicators.bollinger_upper:
        bb_interp = interpret_bollinger(
            price, indicators.bollinger_upper, indicators.bollinger_middle, indicators.bollinger_lower
        )
        analysis["interpretations"].append({
            "indicator": "Bollinger Bands(20,2)",
            "value": f"Upper: {indicators.bollinger_upper:.2f}, Middle: {indicators.bollinger_middle:.2f}, Lower: {indicators.bollinger_lower:.2f}",
            "interpretation": bb_interp,
        })
        analysis["key_levels"]["resistance"] = indicators.bollinger_upper
        analysis["key_levels"]["support"] = indicators.bollinger_lower

    if indicators.ema_20 and indicators.ema_50:
        analysis["interpretations"].append({
            "indicator": "EMA Crossover",
            "value": f"EMA20: {indicators.ema_20:.2f}, EMA50: {indicators.ema_50:.2f}",
            "interpretation": "Price Above EMAs" if price > indicators.ema_20 else "Price Below EMAs",
        })

    if indicators.atr:
        analysis["key_levels"]["atr"] = indicators.atr

    return analysis


def get_technical_weight(analysis: dict) -> float:
    """Calculate technical signal weight based on confidence"""
    confidence = analysis.get("confidence", 0.5)
    signal = analysis.get("signal", "HOLD")

    if signal == "HOLD":
        return 0.1
    elif signal in ["BUY", "SELL"]:
        return 0.3 + (confidence * 0.4)
    return 0.2
