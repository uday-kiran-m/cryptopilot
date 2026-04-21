import sys
import os
from datetime import datetime
from typing import Optional

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../../.."))

import numpy as np
import pandas as pd
from binance.client import Client

from src.schema.models import (
    MarketDataPacket,
    PriceSnapshot,
    TrendData,
    RSIData,
    BollingerData,
    EMAData,
    PriceLevels,
    VolumeData,
    VolatilityData,
    StochasticData,
)


class LiveDataAgent:
    """
    Fetches live market data from Binance and calculates all indicators
    needed for the Analyst agent.
    
    Configurable timeframe (default 4h) and lookback period (default 55 candles).
    """

    def __init__(
        self,
        symbol: str = "BTCUSDT",
        timeframe: str = "4h",
        lookback: int = 55,
    ):
        self.symbol = symbol
        self.timeframe = timeframe
        self.lookback = lookback
        self._client = None

    @property
    def client(self) -> Client:
        if self._client is None:
            self._client = Client()
        return self._client

    def _fetch_candles(self) -> pd.DataFrame:
        """Fetch OHLCV data from Binance"""
        interval_map = {
            "1m": Client.KLINE_INTERVAL_1MINUTE,
            "5m": Client.KLINE_INTERVAL_5MINUTE,
            "15m": Client.KLINE_INTERVAL_15MINUTE,
            "1h": Client.KLINE_INTERVAL_1HOUR,
            "4h": Client.KLINE_INTERVAL_4HOUR,
            "1d": Client.KLINE_INTERVAL_1DAY,
        }

        klines = self.client.get_historical_klines(
            symbol=self.symbol,
            interval=interval_map.get(self.timeframe, Client.KLINE_INTERVAL_4HOUR),
            limit=self.lookback + 10,  # Extra for indicator calculation
        )

        df = pd.DataFrame(
            klines,
            columns=[
                "timestamp", "open", "high", "low", "close", "volume",
                "close_time", "quote_volume", "trades", "taker_base", "taker_quote", "ignore"
            ]
        )

        df["open"] = df["open"].astype(float)
        df["high"] = df["high"].astype(float)
        df["low"] = df["low"].astype(float)
        df["close"] = df["close"].astype(float)
        df["volume"] = df["volume"].astype(float)

        return df

    def _calculate_indicators(self, df: pd.DataFrame) -> pd.DataFrame:
        """Calculate all technical indicators"""
        close = df["close"]
        high = df["high"]
        low = df["low"]
        volume = df["volume"]

        # RSI (14-period)
        delta = close.diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
        rs = gain / loss
        df["rsi"] = 100 - (100 / (1 + rs))

        # Bollinger Bands (20-period, 2 std)
        bb_period = 20
        df["bb_middle"] = close.rolling(window=bb_period).mean()
        bb_std = close.rolling(window=bb_period).std()
        df["bb_upper"] = df["bb_middle"] + (bb_std * 2)
        df["bb_lower"] = df["bb_middle"] - (bb_std * 2)

        # EMA 20
        df["ema20"] = close.ewm(span=20, adjust=False).mean()

        # EMA 50
        df["ema50"] = close.ewm(span=50, adjust=False).mean()

        # EMA 200
        df["ema200"] = close.ewm(span=200, adjust=False).mean()

        # Stochastic (14, 3, 3)
        stoch_period = 14
        stoch_k = 3
        stoch_d = 3
        lowest_low = low.rolling(window=stoch_period).min()
        highest_high = high.rolling(window=stoch_period).max()
        df["stoch_k"] = 100 * (close - lowest_low) / (highest_high - lowest_low)
        df["stochastic"] = df["stoch_k"].rolling(window=stoch_d).mean()

        return df

    def _compute_atr(self, df: pd.DataFrame, period: int = 14) -> float:
        """Compute Average True Range"""
        high = df["high"]
        low = df["low"]
        close = df["close"]

        tr1 = high - low
        tr2 = abs(high - close.shift())
        tr3 = abs(low - close.shift())

        tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
        atr = tr.rolling(window=period).mean()

        return float(atr.iloc[-1])

    def _detect_structure(self, history_10: pd.DataFrame) -> str:
        """Detect market structure (Uptrend, Downtrend, Sideways/Ranging)"""
        if len(history_10) < 10:
            return "Sideways/Ranging"

        mid = len(history_10) // 2
        first_half = history_10.iloc[:mid]
        second_half = history_10.iloc[mid:]

        first_high = first_half["high"].max()
        first_low = first_half["low"].min()
        second_high = second_half["high"].max()
        second_low = second_half["low"].min()

        hh = second_high > first_high
        hl = second_low > first_low
        lh = second_high < first_high
        ll = second_low < first_low

        if hh and hl:
            return "Uptrend"
        elif lh and ll:
            return "Downtrend"
        else:
            return "Sideways/Ranging"

    def get_market_data(self) -> MarketDataPacket:
        """
        Fetch and process market data to create a MarketDataPacket.
        
        Returns:
            MarketDataPacket ready for the Analyst agent
        """
        df = self._fetch_candles()
        df = self._calculate_indicators(df)

        current_idx = len(df) - 1
        current_row = df.iloc[current_idx]
        prev_row = df.iloc[current_idx - 1]

        history_55 = df.iloc[current_idx - 55 + 1: current_idx + 1]
        history_50 = df.iloc[current_idx - 50 + 1: current_idx + 1]
        history_20 = df.iloc[current_idx - 20 + 1: current_idx + 1]
        history_10 = df.iloc[current_idx - 10 + 1: current_idx + 1]

        price = current_row["close"]

        # Snapshot
        snapshot = PriceSnapshot(
            open=float(current_row["open"]),
            high=float(current_row["high"]),
            low=float(current_row["low"]),
            close=float(price)
        )

        # Trends
        pct_change_50 = ((price - history_50.iloc[0]["close"]) / history_50.iloc[0]["close"]) * 100
        pct_change_10 = ((price - history_10.iloc[0]["close"]) / history_10.iloc[0]["close"]) * 100
        structure = self._detect_structure(history_10)

        trends = TrendData(
            pct_change_50=round(pct_change_50, 2),
            pct_change_10=round(pct_change_10, 2),
            market_structure=structure
        )

        # RSI
        rsi_current = float(current_row["rsi"])
        rsi_prev = float(prev_row["rsi"])
        rsi_avg_50 = float(history_50["rsi"].mean())
        rsi_trend = "Increasing" if rsi_current > float(history_10["rsi"].mean()) else "Decreasing"

        rsi = RSIData(
            current=round(rsi_current, 2),
            prev=round(rsi_prev, 2),
            avg_50=round(rsi_avg_50, 2),
            trend=rsi_trend
        )

        # Bollinger Bands
        bb_upper = float(current_row["bb_upper"])
        bb_lower = float(current_row["bb_lower"])

        if price > bb_upper:
            bb_pos = "Above Upper Band"
        elif price < bb_lower:
            bb_pos = "Below Lower Band"
        elif price > (bb_upper + bb_lower) / 2:
            bb_pos = "Upper Half"
        else:
            bb_pos = "Lower Half"

        bands = BollingerData(
            upper=round(bb_upper, 2),
            lower=round(bb_lower, 2),
            position_label=bb_pos
        )

        # EMA
        ema_20 = float(current_row["ema20"])
        ema_slope = "Increasing" if ema_20 > float(history_10["ema20"].mean()) else "Decreasing"
        ema_rel = "Price Above EMA" if price > ema_20 else "Price Below EMA"

        ema = EMAData(
            value=round(ema_20, 2),
            price_rel=ema_rel,
            slope=ema_slope
        )

        # Levels
        levels = PriceLevels(
            high_50=round(float(history_50["high"].max()), 2),
            low_50=round(float(history_50["low"].min()), 2),
            high_20=round(float(history_20["high"].max()), 2),
            low_20=round(float(history_20["low"].min()), 2),
            high_55=round(float(history_55["high"].max()), 2),
            low_55=round(float(history_55["low"].min()), 2)
        )

        # Volume
        vol_avg = float(history_50["volume"].mean())
        is_spike = bool(current_row["volume"] > vol_avg * 1.5)

        volume_data = VolumeData(
            current=round(float(current_row["volume"]), 2),
            avg_50=round(vol_avg, 2),
            is_spike=is_spike
        )

        # Volatility (ATR)
        atr = self._compute_atr(df)

        volatility = VolatilityData(
            atr=round(atr, 2)
        )

        # Stochastic
        stoch_col = "stochastic" if "stochastic" in df.columns else "stoch_k"
        stoch_val = float(current_row[stoch_col]) if stoch_col in df.columns else 50.0

        stochastic = StochasticData(
            current=round(stoch_val, 2)
        )

        return MarketDataPacket(
            snapshot=snapshot,
            trends=trends,
            rsi=rsi,
            bands=bands,
            ema=ema,
            levels=levels,
            volume=volume_data,
            volatility=volatility,
            stochastic=stochastic,
            asset_name=self.symbol,
            timestamp=datetime.now()
        )

    def get_current_price(self) -> float:
        """Get current market price"""
        ticker = self.client.get_symbol_ticker(symbol=self.symbol)
        return float(ticker["price"])


def create_live_data_agent(
    symbol: str = "BTCUSDT",
    timeframe: str = "4h",
    lookback: int = 55
) -> LiveDataAgent:
    """Factory function to create a live data agent"""
    return LiveDataAgent(
        symbol=symbol,
        timeframe=timeframe,
        lookback=lookback
    )
