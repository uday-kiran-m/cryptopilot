import asyncio
from datetime import datetime, timedelta
from typing import Optional

import httpx
from binance.client import Client

from src.core import get_logger
from src.core.config import settings
from src.core.models import OHLCVData, TechnicalIndicators

logger = get_logger("binance_client")

_interval_map = {
    "1m": Client.KLINE_INTERVAL_1MINUTE,
    "5m": Client.KLINE_INTERVAL_5MINUTE,
    "15m": Client.KLINE_INTERVAL_15MINUTE,
    "1h": Client.KLINE_INTERVAL_1HOUR,
    "4h": Client.KLINE_INTERVAL_4HOUR,
    "1d": Client.KLINE_INTERVAL_1DAY,
}


class BinanceClient:
    def __init__(self):
        self.api_key = settings.binance_api_key
        self.api_secret = settings.binance_api_secret
        self._client: Optional[Client] = None
        self._public_client: Optional[Client] = None

    @property
    def client(self) -> Client:
        if self._client is None:
            if self.api_key and self.api_secret:
                self._client = Client(self.api_key, self.api_secret)
                logger.info("Binance authenticated client initialized")
            else:
                raise ValueError("Binance API keys not configured")
        return self._client

    @property
    def public_client(self) -> Client:
        if self._public_client is None:
            self._public_client = Client()
            logger.info("Binance public client initialized")
        return self._public_client

    async def get_symbol_ticker(self, symbol: str) -> dict:
        """Get current ticker price for a symbol"""
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    "https://api.binance.com/api/v3/ticker/price",
                    params={"symbol": symbol},
                )
                response.raise_for_status()
                data = response.json()
                logger.debug(f"Ticker {symbol}: {data}")
                return data
        except Exception as e:
            logger.error(f"Error fetching ticker for {symbol}: {e}")
            raise

    async def get_klines(
        self,
        symbol: str,
        interval: str = "1h",
        limit: int = 100,
        start_str: Optional[str] = None,
    ) -> list[OHLCVData]:
        """Fetch OHLCV candlestick data"""
        try:
            klines = self.public_client.get_historical_klines(
                symbol=symbol,
                interval=_interval_map.get(interval, Client.KLINE_INTERVAL_1HOUR),
                limit=limit,
                start_str=start_str or (datetime.now() - timedelta(days=7)).strftime(
                    "%d %b, %Y"
                ),
            )

            ohlcv_data = []
            for k in klines:
                ohlcv_data.append(
                    OHLCVData(
                        timestamp=datetime.fromtimestamp(k[0] / 1000),
                        open=float(k[1]),
                        high=float(k[2]),
                        low=float(k[3]),
                        close=float(k[4]),
                        volume=float(k[5]),
                        quote_volume=float(k[7]),
                    )
                )

            logger.info(f"Fetched {len(ohlcv_data)} klines for {symbol}")
            return ohlcv_data

        except Exception as e:
            logger.error(f"Error fetching klines for {symbol}: {e}")
            raise

    async def get_24hr_ticker(self, symbol: str) -> dict:
        """Get 24-hour price change statistics"""
        try:
            ticker = self.public_client.get_ticker(symbol=symbol)
            logger.debug(f"24hr ticker {symbol}: {ticker}")
            return ticker
        except Exception as e:
            logger.error(f"Error fetching 24hr ticker for {symbol}: {e}")
            raise

    async def get_order_book(self, symbol: str, limit: int = 10) -> dict:
        """Get order book depth"""
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    "https://api.binance.com/api/v3/depth",
                    params={"symbol": symbol, "limit": limit},
                )
                response.raise_for_status()
                data = response.json()
                logger.debug(f"Order book {symbol}: {len(data.get('bids', []))} bids, {len(data.get('asks', []))} asks")
                return data
        except Exception as e:
            logger.error(f"Error fetching order book for {symbol}: {e}")
            raise


binance_client = BinanceClient()
