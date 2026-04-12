from datetime import datetime
from typing import Optional

import httpx

from src.core import get_logger
from src.core.config import settings
from src.core.models import OHLCVData

logger = get_logger("coinbase_client")

_product_cache: dict = {}


class CoinbaseClient:
    def __init__(self):
        self.api_key = settings.coinbase_api_key
        self.api_secret = settings.coinbase_api_secret
        self._rest_client = None

    @property
    def rest_client(self):
        if self._rest_client is None:
            try:
                from coinbase.rest import RESTClient

                if self.api_key and self.api_secret:
                    self._rest_client = RESTClient(
                        api_key=self.api_key, api_secret=self.api_secret
                    )
                    logger.info("Coinbase authenticated client initialized")
                else:
                    self._rest_client = RESTClient()
                    logger.info("Coinbase public client initialized")
            except ImportError:
                logger.error("coinbase-advanced-py not installed")
                raise
        return self._rest_client

    async def get_product(self, product_id: str) -> dict:
        """Get product details (e.g., BTC-USD)"""
        global _product_cache

        if product_id in _product_cache:
            return _product_cache[product_id]

        try:
            product = self.rest_client.get_product(product_id=product_id)
            if hasattr(product, "to_dict"):
                product = product.to_dict()
            _product_cache[product_id] = product
            logger.debug(f"Product {product_id}: {product}")
            return product
        except Exception as e:
            logger.error(f"Error fetching product {product_id}: {e}")
            raise

    async def get_public_candles(
        self,
        product_id: str,
        granularity: int = 3600,
        start: Optional[datetime] = None,
        end: Optional[datetime] = None,
    ) -> list[OHLCVData]:
        """Fetch historical candle data"""
        try:
            params = {"product_id": product_id, "granularity": granularity}
            if start:
                params["start"] = start.isoformat()
            if end:
                params["end"] = end.isoformat()

            candles = self.rest_client.get_public_candles(**params)

            if hasattr(candles, "to_dict"):
                candles = candles.to_dict()

            ohlcv_data = []
            for c in candles.get("candles", []):
                ohlcv_data.append(
                    OHLCVData(
                        timestamp=datetime.fromisoformat(c["start"].replace("Z", "+00:00")),
                        open=float(c["open"]),
                        high=float(c["high"]),
                        low=float(c["low"]),
                        close=float(c["close"]),
                        volume=float(c["volume"]),
                    )
                )

            ohlcv_data.sort(key=lambda x: x.timestamp)
            logger.info(f"Fetched {len(ohlcv_data)} candles for {product_id}")
            return ohlcv_data

        except Exception as e:
            logger.error(f"Error fetching candles for {product_id}: {e}")
            raise

    async def get_best_bid_ask(self, product_id: str) -> dict:
        """Get best bid and ask for a product"""
        try:
            result = self.rest_client.get_best_bid_ask(product_ids=[product_id])
            if hasattr(result, "to_dict"):
                result = result.to_dict()
            logger.debug(f"Best bid/ask {product_id}: {result}")
            return result
        except Exception as e:
            logger.error(f"Error fetching best bid/ask for {product_id}: {e}")
            raise

    async def get_market_trades(
        self, product_id: str, limit: int = 50
    ) -> list[dict]:
        """Get recent market trades"""
        try:
            trades = self.rest_client.get_market_trades(
                product_id=product_id, limit=limit
            )
            if hasattr(trades, "to_dict"):
                trades = trades.to_dict()
            logger.debug(f"Fetched {len(trades.get('trades', []))} trades for {product_id}")
            return trades
        except Exception as e:
            logger.error(f"Error fetching trades for {product_id}: {e}")
            raise


coinbase_client = CoinbaseClient()
