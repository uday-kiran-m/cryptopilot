from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

import pandas as pd
import requests


DEFAULT_PORTFOLIO_USD = 100_000.0


@dataclass
class Candle:
    open_time: int
    open: float
    high: float
    low: float
    close: float
    volume: float


@dataclass
class IndicatorSnapshot:
    price: float
    rsi: float | None
    ema20: float | None
    ema50: float | None
    macd: float | None
    macd_signal: float | None
    bollinger_upper: float | None
    bollinger_middle: float | None
    bollinger_lower: float | None


@dataclass
class Position:
    symbol: str
    quantity: float
    entry_price: float


@dataclass
class PaperPortfolio:
    cash_usd: float = DEFAULT_PORTFOLIO_USD
    positions: dict[str, Position] = field(default_factory=dict)
    trade_log: list[dict[str, Any]] = field(default_factory=list)

    def buy(self, symbol: str, price: float, usd_amount: float) -> dict[str, Any]:
        if symbol in self.positions:
            return {"status": "skipped", "reason": "position already open"}

        spend = min(self.cash_usd, usd_amount)
        if spend <= 0:
            return {"status": "rejected", "reason": "no cash available"}

        quantity = spend / price
        self.cash_usd -= spend
        self.positions[symbol] = Position(symbol=symbol, quantity=quantity, entry_price=price)

        trade = {
            "side": "BUY",
            "symbol": symbol,
            "price": price,
            "quantity": quantity,
            "value_usd": spend,
        }
        self.trade_log.append(trade)
        return {"status": "executed", "trade": trade}

    def sell(self, symbol: str, price: float, reason: str) -> dict[str, Any]:
        position = self.positions.get(symbol)
        if position is None:
            return {"status": "skipped", "reason": "no open position"}

        proceeds = position.quantity * price
        pnl = (price - position.entry_price) * position.quantity
        self.cash_usd += proceeds
        del self.positions[symbol]

        trade = {
            "side": "SELL",
            "symbol": symbol,
            "price": price,
            "quantity": position.quantity,
            "value_usd": proceeds,
            "pnl_usd": pnl,
            "reason": reason,
        }
        self.trade_log.append(trade)
        return {"status": "executed", "trade": trade}

    def total_value(self, last_prices: dict[str, float]) -> float:
        holdings_value = sum(
            position.quantity * last_prices.get(symbol, position.entry_price)
            for symbol, position in self.positions.items()
        )
        return self.cash_usd + holdings_value


def fetch_binance_klines(symbol: str, interval: str = "1h", limit: int = 200) -> list[Candle]:
    response = requests.get(
        "https://api.binance.com/api/v3/klines",
        params={"symbol": symbol.upper(), "interval": interval, "limit": limit},
        timeout=10,
    )
    response.raise_for_status()

    candles: list[Candle] = []
    for item in response.json():
        candles.append(
            Candle(
                open_time=int(item[0]),
                open=float(item[1]),
                high=float(item[2]),
                low=float(item[3]),
                close=float(item[4]),
                volume=float(item[5]),
            )
        )
    return candles


def fetch_latest_price(symbol: str) -> float:
    response = requests.get(
        "https://api.binance.com/api/v3/ticker/price",
        params={"symbol": symbol.upper()},
        timeout=10,
    )
    response.raise_for_status()
    return float(response.json()["price"])


def _to_dataframe(candles: list[Candle]) -> pd.DataFrame:
    return pd.DataFrame({"close": [c.close for c in candles]})


def calculate_indicators(candles: list[Candle]) -> IndicatorSnapshot:
    df = _to_dataframe(candles)
    close = df["close"]

    delta = close.diff()
    gains = delta.clip(lower=0)
    losses = -delta.clip(upper=0)
    avg_gain = gains.rolling(window=14).mean()
    avg_loss = losses.rolling(window=14).mean()
    rs = avg_gain / avg_loss.replace(0, pd.NA)
    rsi = 100 - (100 / (1 + rs))

    ema20 = close.ewm(span=20, adjust=False).mean()
    ema50 = close.ewm(span=50, adjust=False).mean()

    ema12 = close.ewm(span=12, adjust=False).mean()
    ema26 = close.ewm(span=26, adjust=False).mean()
    macd = ema12 - ema26
    macd_signal = macd.ewm(span=9, adjust=False).mean()

    middle = close.rolling(window=20).mean()
    std = close.rolling(window=20).std()
    upper = middle + (2 * std)
    lower = middle - (2 * std)

    def latest(series: pd.Series) -> float | None:
        value = series.iloc[-1]
        return None if pd.isna(value) else float(value)

    return IndicatorSnapshot(
        price=float(close.iloc[-1]),
        rsi=latest(rsi),
        ema20=latest(ema20),
        ema50=latest(ema50),
        macd=latest(macd),
        macd_signal=latest(macd_signal),
        bollinger_upper=latest(upper),
        bollinger_middle=latest(middle),
        bollinger_lower=latest(lower),
    )
