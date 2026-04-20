from __future__ import annotations

import json
import re
from typing import Any

try:
    from .simple_trade_conditions import evaluate_condition_expression, explain_condition_result
    from .simple_trade_market import (
        Candle,
        DEFAULT_PORTFOLIO_USD,
        PaperPortfolio,
        calculate_indicators,
        fetch_binance_klines,
    )
except ImportError:
    from simple_trade_conditions import evaluate_condition_expression, explain_condition_result
    from simple_trade_market import (
        Candle,
        DEFAULT_PORTFOLIO_USD,
        PaperPortfolio,
        calculate_indicators,
        fetch_binance_klines,
    )


class Trade:
    """Simple paper trading class driven only by JSON conditions."""

    def __init__(
        self,
        stock_name: str,
        entry_conditions: dict[str, Any] | None = None,
        exit_conditions: dict[str, Any] | None = None,
        entry_condition_expr: str | None = None,
        exit_condition_expr: str | None = None,
        trade_size_usd: float = 10_000.0,
        position_size: float | None = None,
        risk_reward_ratio: float | None = None,
        interval: str = "1h",
        portfolio: PaperPortfolio | None = None,
    ):
        self.stock_name = stock_name.upper()
        self.entry_conditions = entry_conditions or {}
        self.exit_conditions = exit_conditions or {}
        self.entry_condition_expr = entry_condition_expr
        self.exit_condition_expr = exit_condition_expr
        self.trade_size_usd = trade_size_usd
        self.position_size = position_size
        self.risk_reward_ratio = risk_reward_ratio
        self.interval = interval
        self.portfolio = portfolio or PaperPortfolio()

    @classmethod
    def _load_config(cls, config_json: str) -> dict[str, Any]:
        cleaned = re.sub(r",(\s*[}\]])", r"\1", config_json.strip())
        return json.loads(cleaned)

    @classmethod
    def from_json(cls, config_json: str, portfolio_usd: float = DEFAULT_PORTFOLIO_USD) -> "Trade":
        data = cls._load_config(config_json)
        asset = data.get("asset", data.get("stock_name"))
        if asset is None:
            raise KeyError("config must include 'asset' or 'stock_name'")

        timeframe = data.get("timeframe", data.get("interval", "1h"))
        return cls(
            stock_name=asset,
            entry_conditions=data.get("entry", {}),
            exit_conditions=data.get("exit", {}),
            entry_condition_expr=data.get("entry_condition"),
            exit_condition_expr=data.get("exit_condition"),
            trade_size_usd=data.get("trade_size_usd", 10_000.0),
            position_size=data.get("position_size"),
            risk_reward_ratio=data.get("risk_reward_ratio"),
            interval=timeframe,
            portfolio=PaperPortfolio(cash_usd=portfolio_usd),
        )

    @staticmethod
    def fetch_binance_klines(symbol: str, interval: str = "1h", limit: int = 200) -> list[Candle]:
        return fetch_binance_klines(symbol=symbol, interval=interval, limit=limit)

    @staticmethod
    def calculate_indicators(candles: list[Candle]):
        return calculate_indicators(candles)

    def _legacy_condition_reason(self, indicators, conditions: dict[str, Any]) -> tuple[bool, str]:
        for condition_name, expected_value in conditions.items():
            if condition_name == "rsi_greater_than":
                if indicators.rsi is None or indicators.rsi <= float(expected_value):
                    return False, condition_name
            elif condition_name == "rsi_less_than":
                if indicators.rsi is None or indicators.rsi >= float(expected_value):
                    return False, condition_name
            elif condition_name == "price_greater_than_ema20":
                if indicators.ema20 is None or indicators.price <= indicators.ema20:
                    return False, condition_name
            elif condition_name == "price_less_than_ema20":
                if indicators.ema20 is None or indicators.price >= indicators.ema20:
                    return False, condition_name
            elif condition_name == "ema20_greater_than_ema50":
                if indicators.ema20 is None or indicators.ema50 is None or indicators.ema20 <= indicators.ema50:
                    return False, condition_name
            elif condition_name == "ema20_less_than_ema50":
                if indicators.ema20 is None or indicators.ema50 is None or indicators.ema20 >= indicators.ema50:
                    return False, condition_name
            elif condition_name == "macd_greater_than_signal":
                if indicators.macd is None or indicators.macd_signal is None or indicators.macd <= indicators.macd_signal:
                    return False, condition_name
            elif condition_name == "macd_less_than_signal":
                if indicators.macd is None or indicators.macd_signal is None or indicators.macd >= indicators.macd_signal:
                    return False, condition_name
            elif condition_name == "price_greater_than_bollinger_middle":
                if indicators.bollinger_middle is None or indicators.price <= indicators.bollinger_middle:
                    return False, condition_name
            elif condition_name == "price_less_than_bollinger_middle":
                if indicators.bollinger_middle is None or indicators.price >= indicators.bollinger_middle:
                    return False, condition_name
            elif condition_name == "price_greater_than_bollinger_upper":
                if indicators.bollinger_upper is None or indicators.price <= indicators.bollinger_upper:
                    return False, condition_name
            elif condition_name == "price_less_than_bollinger_lower":
                if indicators.bollinger_lower is None or indicators.price >= indicators.bollinger_lower:
                    return False, condition_name
            else:
                return False, f"unsupported condition: {condition_name}"
        return True, "all conditions met"

    def _match_conditions(self, indicators, expression: str | None, conditions: dict[str, Any]) -> tuple[bool, str]:
        if expression:
            matched, reason = evaluate_condition_expression(indicators, expression)
            return matched, explain_condition_result(expression, matched, reason)
        return self._legacy_condition_reason(indicators, conditions)

    def evaluate_latest_candle(self, candles: list[Candle]) -> dict[str, Any]:
        indicators = calculate_indicators(candles)
        has_position = self.stock_name in self.portfolio.positions

        if not has_position:
            matched, reason = self._match_conditions(indicators, self.entry_condition_expr, self.entry_conditions)
            if matched:
                trade_value = self.trade_size_usd
                if self.position_size is not None:
                    trade_value = float(self.position_size) * indicators.price
                result = self.portfolio.buy(self.stock_name, indicators.price, trade_value)
                return {
                    "action": "BUY",
                    "reason": reason,
                    "result": result,
                    "indicators": indicators,
                    "risk_reward_ratio": self.risk_reward_ratio,
                }
            return {
                "action": "HOLD",
                "reason": reason,
                "indicators": indicators,
                "risk_reward_ratio": self.risk_reward_ratio,
            }

        matched, reason = self._match_conditions(indicators, self.exit_condition_expr, self.exit_conditions)
        if matched:
            result = self.portfolio.sell(self.stock_name, indicators.price, reason)
            return {
                "action": "SELL",
                "reason": reason,
                "result": result,
                "indicators": indicators,
                "risk_reward_ratio": self.risk_reward_ratio,
            }

        return {
            "action": "HOLD",
            "reason": reason,
            "indicators": indicators,
            "risk_reward_ratio": self.risk_reward_ratio,
        }

    def monitor_and_trade(self, candles: list[Candle], warmup_period: int = 60) -> list[dict[str, Any]]:
        results: list[dict[str, Any]] = []
        for index in range(warmup_period, len(candles) + 1):
            results.append(self.evaluate_latest_candle(candles[:index]))
        return results

    def portfolio_summary(self, last_price: float | None = None) -> dict[str, Any]:
        last_prices = {}
        if last_price is not None:
            last_prices[self.stock_name] = last_price

        return {
            "cash_usd": self.portfolio.cash_usd,
            "positions": list(self.portfolio.positions.keys()),
            "trade_count": len(self.portfolio.trade_log),
            "total_value_usd": self.portfolio.total_value(last_prices),
            "trade_log": self.portfolio.trade_log,
        }


class trade(Trade):
    """Lowercase alias kept only to match the requested class name."""
