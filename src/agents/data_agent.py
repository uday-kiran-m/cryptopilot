from datetime import datetime
from typing import Optional

from crewai import Agent
from crewai.tools import BaseTool

from src.core import get_logger
from src.core.models import OHLCVData, TechnicalIndicators
from src.tools.binance_client import binance_client
from src.tools.coinbase_client import coinbase_client
from src.tools.indicators import calculate_all_indicators

logger = get_logger("data_agent")


class BinanceDataTool(BaseTool):
    name: str = "binance_data_fetcher"
    description: str = "Fetches cryptocurrency OHLCV data from Binance exchange"

    async def _arun(self, symbol: str, interval: str = "1h", limit: int = 100):
        try:
            data = await binance_client.get_klines(symbol=symbol, interval=interval, limit=limit)
            return data
        except Exception as e:
            logger.error(f"Error in BinanceDataTool: {e}")
            return []


class CoinbaseDataTool(BaseTool):
    name: str = "coinbase_data_fetcher"
    description: str = "Fetches cryptocurrency OHLCV data from Coinbase exchange"

    async def _arun(self, symbol: str, granularity: int = 3600, limit: int = 100):
        try:
            from src.core.config import settings

            product_id = settings.get_coinbase_product_id(symbol)
            data = await coinbase_client.get_public_candles(product_id=product_id, granularity=granularity)
            return data
        except Exception as e:
            logger.error(f"Error in CoinbaseDataTool: {e}")
            return []


class TickerPriceTool(BaseTool):
    name: str = "ticker_price_fetcher"
    description: str = "Fetches current ticker price for a cryptocurrency symbol"

    async def _arun(self, symbol: str):
        try:
            data = await binance_client.get_symbol_ticker(symbol=symbol)
            return data
        except Exception as e:
            logger.error(f"Error in TickerPriceTool: {e}")
            return {}


def create_data_agent(symbol: str) -> Agent:
    """Create a data agent for a specific symbol"""
    base, _ = symbol.replace("USDT", ""), "USDT"

    return Agent(
        role=f"{base} Data Analyst",
        goal=f"Gather accurate and up-to-date market data for {base} from multiple exchanges",
        backstory=f"""You are a specialized data analyst focused on {base} cryptocurrency.
        Your expertise is in fetching, validating, and organizing market data from various sources.
        You ensure data quality by cross-referencing between Binance and Coinbase.""",
        tools=[BinanceDataTool(), CoinbaseDataTool(), TickerPriceTool()],
        verbose=True,
        allow_delegation=False,
    )


async def fetch_market_data(symbol: str, interval: str = "1h", limit: int = 100) -> dict:
    """Fetch and combine market data from multiple sources"""
    result = {
        "symbol": symbol,
        "timestamp": datetime.now(),
        "ohlcv_data": [],
        "current_price": None,
        "indicators": None,
        "source": None,
    }

    try:
        binance_data = await binance_client.get_klines(
            symbol=symbol, interval=interval, limit=limit
        )
        if binance_data:
            result["ohlcv_data"] = binance_data
            result["current_price"] = binance_data[-1].close
            result["indicators"] = calculate_all_indicators(symbol, binance_data)
            result["source"] = "binance"
            logger.info(f"Fetched {len(binance_data)} candles for {symbol} from Binance")
            return result
    except Exception as e:
        logger.warning(f"Binance fetch failed for {symbol}: {e}")

    try:
        from src.core.config import settings

        product_id = settings.get_coinbase_product_id(symbol)
        coinbase_data = await coinbase_client.get_public_candles(
            product_id=product_id, granularity=3600
        )
        if coinbase_data:
            result["ohlcv_data"] = coinbase_data
            result["current_price"] = coinbase_data[-1].close
            result["indicators"] = calculate_all_indicators(symbol, coinbase_data)
            result["source"] = "coinbase"
            logger.info(f"Fetched {len(coinbase_data)} candles for {symbol} from Coinbase")
            return result
    except Exception as e:
        logger.warning(f"Coinbase fetch failed for {symbol}: {e}")

    logger.error(f"Failed to fetch data for {symbol} from any source")
    return result


def analyze_data_quality(data: dict) -> dict:
    """Analyze and validate fetched data quality"""
    quality_report = {
        "is_valid": False,
        "candle_count": 0,
        "has_gaps": False,
        "price_anomaly": False,
        "issues": [],
    }

    ohlcv = data.get("ohlcv_data", [])
    quality_report["candle_count"] = len(ohlcv)

    if len(ohlcv) < 50:
        quality_report["issues"].append("Insufficient candle data")

    if len(ohlcv) > 1:
        prices = [c.close for c in ohlcv]
        max_change = max(abs(prices[i] - prices[i - 1]) / prices[i - 1] for i in range(1, len(prices)))
        if max_change > 0.2:
            quality_report["issues"].append("Possible price anomaly detected")
            quality_report["price_anomaly"] = True

    quality_report["is_valid"] = len(quality_report["issues"]) == 0
    return quality_report
