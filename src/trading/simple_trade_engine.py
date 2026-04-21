from __future__ import annotations

import json
import re
from dataclasses import dataclass
from datetime import datetime
from typing import Any

try:
    from .simple_trade_conditions import evaluate_condition_expression, explain_condition_result
    from .simple_trade_market import (
        Candle,
        DEFAULT_PORTFOLIO_USD,
        IndicatorSnapshot,
        PaperPortfolio,
        calculate_indicators,
        fetch_binance_klines,
        fetch_latest_price,
    )
except ImportError:
    from simple_trade_conditions import evaluate_condition_expression, explain_condition_result
    from simple_trade_market import (
        Candle,
        DEFAULT_PORTFOLIO_USD,
        IndicatorSnapshot,
        PaperPortfolio,
        calculate_indicators,
        fetch_binance_klines,
        fetch_latest_price,
    )


def _parse_datetime(value: str) -> datetime:
    normalized = value.strip().replace("Z", "+00:00")
    return datetime.fromisoformat(normalized)


def _datetime_to_string(value: datetime | None) -> str | None:
    return None if value is None else value.isoformat()


@dataclass
class TradeRequest:
    asset_name: str
    entry_condition: str
    exit_condition: str
    target: float
    stop_loss: float
    position_size: float
    timeframe: str
    valid_until: datetime
    trade_id: str
    status: str = "queued"
    entry_price: float | None = None
    exit_price: float | None = None
    entry_time: datetime | None = None
    exit_time: datetime | None = None
    entry_reason: str | None = None
    exit_reason: str | None = None
    pnl_usd: float | None = None

    @property
    def market_key(self) -> tuple[str, str]:
        return self.asset_name.upper(), self.timeframe

    def to_dict(self) -> dict[str, Any]:
        return {
            "trade_id": self.trade_id,
            "asset_name": self.asset_name,
            "timeframe": self.timeframe,
            "entry_condition": self.entry_condition,
            "exit_condition": self.exit_condition,
            "target": self.target,
            "stop_loss": self.stop_loss,
            "position_size": self.position_size,
            "valid_until": _datetime_to_string(self.valid_until),
            "status": self.status,
            "entry_price": self.entry_price,
            "exit_price": self.exit_price,
            "entry_time": _datetime_to_string(self.entry_time),
            "exit_time": _datetime_to_string(self.exit_time),
            "entry_reason": self.entry_reason,
            "exit_reason": self.exit_reason,
            "pnl_usd": self.pnl_usd,
        }


@dataclass
class MarketSnapshot:
    asset_name: str
    timeframe: str
    indicators: IndicatorSnapshot
    last_indicator_refresh: datetime
    last_price_refresh: datetime

    @property
    def market_key(self) -> tuple[str, str]:
        return self.asset_name.upper(), self.timeframe


class Trade:
    """Single-trade helper kept for direct evaluation paths."""

    def __init__(
        self,
        stock_name: str,
        entry_condition_expr: str,
        exit_condition_expr: str,
        target: float,
        stop_loss: float,
        position_size: float,
        interval: str = "1h",
        portfolio: PaperPortfolio | None = None,
    ):
        self.stock_name = stock_name.upper()
        self.entry_condition_expr = entry_condition_expr
        self.exit_condition_expr = exit_condition_expr
        self.target = target
        self.stop_loss = stop_loss
        self.position_size = position_size
        self.interval = interval
        self.portfolio = portfolio or PaperPortfolio()

    @classmethod
    def _load_config(cls, config_json: str) -> dict[str, Any]:
        cleaned = re.sub(r",(\s*[}\]])", r"\1", config_json.strip())
        return json.loads(cleaned)

    @classmethod
    def from_json(cls, config_json: str, portfolio_usd: float = DEFAULT_PORTFOLIO_USD) -> "Trade":
        data = cls._load_config(config_json)
        return cls(
            stock_name=data["asset_name"],
            entry_condition_expr=data["entry_condition"],
            exit_condition_expr=data["exit_condition"],
            target=float(data["target"]),
            stop_loss=float(data["stop_loss"]),
            position_size=float(data["position_size"]),
            interval=data["timeframe"],
            portfolio=PaperPortfolio(cash_usd=portfolio_usd),
        )

    @staticmethod
    def fetch_binance_klines(symbol: str, interval: str = "1h", limit: int = 200) -> list[Candle]:
        return fetch_binance_klines(symbol=symbol, interval=interval, limit=limit)

    @staticmethod
    def calculate_indicators(candles: list[Candle]) -> IndicatorSnapshot:
        return calculate_indicators(candles)

    @staticmethod
    def fetch_latest_price(symbol: str) -> float:
        return fetch_latest_price(symbol)


class TradeQueueEngine:
    """Queue-driven paper trading engine.

    - queued trades wait for entry conditions until `valid_until`
    - entered trades are checked for stop loss, target, and exit condition
    - exited trades update paper portfolio and realized PnL
    """

    def __init__(
        self,
        trade_queue: list[TradeRequest] | None = None,
        portfolio: PaperPortfolio | None = None,
    ):
        self.trade_queue = trade_queue or []
        self.portfolio = portfolio or PaperPortfolio()

    @staticmethod
    def fetch_binance_klines(symbol: str, interval: str = "1h", limit: int = 200) -> list[Candle]:
        return fetch_binance_klines(symbol=symbol, interval=interval, limit=limit)

    @staticmethod
    def calculate_indicators(candles: list[Candle]) -> IndicatorSnapshot:
        return calculate_indicators(candles)

    @staticmethod
    def fetch_latest_price(symbol: str) -> float:
        return fetch_latest_price(symbol)

    @classmethod
    def _load_payload(cls, payload_json: str) -> Any:
        cleaned = re.sub(r",(\s*[}\]])", r"\1", payload_json.strip())
        return json.loads(cleaned)

    @classmethod
    def _trade_from_dict(cls, data: dict[str, Any], index: int) -> TradeRequest:
        return TradeRequest(
            asset_name=data["asset_name"].upper(),
            entry_condition=data["entry_condition"],
            exit_condition=data["exit_condition"],
            target=float(data["target"]),
            stop_loss=float(data["stop_loss"]),
            position_size=float(data["position_size"]),
            timeframe=data["timeframe"],
            valid_until=_parse_datetime(data["valid_until"]),
            trade_id=data.get("trade_id", f"trade-{index + 1}"),
        )

    @classmethod
    def from_json(cls, payload_json: str, portfolio_usd: float = DEFAULT_PORTFOLIO_USD) -> "TradeQueueEngine":
        payload = cls._load_payload(payload_json)
        if isinstance(payload, dict):
            payload = [payload]
        if not isinstance(payload, list):
            raise TypeError("trade queue payload must be a JSON object or JSON list")

        trades = [cls._trade_from_dict(item, index) for index, item in enumerate(payload)]
        return cls(trade_queue=trades, portfolio=PaperPortfolio(cash_usd=portfolio_usd))

    def add_trade_from_json(self, payload_json: str) -> TradeRequest:
        payload = self._load_payload(payload_json)
        if not isinstance(payload, dict):
            raise TypeError("single trade payload must be a JSON object")

        trade = self._trade_from_dict(payload, len(self.trade_queue))
        self.trade_queue.append(trade)
        return trade

    def active_market_keys(self) -> list[tuple[str, str]]:
        keys = {
            trade.market_key
            for trade in self.trade_queue
            if trade.status in {"queued", "entered"}
        }
        return sorted(keys)

    def prune_finished_trades(self) -> list[TradeRequest]:
        finished = [
            trade
            for trade in self.trade_queue
            if trade.status in {"exited", "expired"}
        ]
        self.trade_queue = [
            trade
            for trade in self.trade_queue
            if trade.status not in {"exited", "expired"}
        ]
        return finished

    def _match_condition(self, indicators: IndicatorSnapshot, expression: str) -> tuple[bool, str]:
        matched, reason = evaluate_condition_expression(indicators, expression)
        return matched, explain_condition_result(expression, matched, reason)

    def _position_is_open(self, asset_name: str) -> bool:
        return asset_name.upper() in self.portfolio.positions

    def _evaluate_entry(
        self,
        trade: TradeRequest,
        snapshot: MarketSnapshot,
        now: datetime,
    ) -> dict[str, Any]:
        if trade.valid_until <= now:
            trade.status = "expired"
            trade.exit_time = now
            trade.exit_reason = "Trade expired before entry."
            return {
                "trade_id": trade.trade_id,
                "asset_name": trade.asset_name,
                "status": trade.status,
                "action": "EXPIRE",
                "reason": trade.exit_reason,
                "indicators": snapshot.indicators,
            }

        if self._position_is_open(trade.asset_name):
            return {
                "trade_id": trade.trade_id,
                "asset_name": trade.asset_name,
                "status": trade.status,
                "action": "WAIT",
                "reason": "Another position is already open for this asset.",
                "indicators": snapshot.indicators,
            }

        matched, reason = self._match_condition(snapshot.indicators, trade.entry_condition)
        if not matched:
            return {
                "trade_id": trade.trade_id,
                "asset_name": trade.asset_name,
                "status": trade.status,
                "action": "WAIT",
                "reason": reason,
                "indicators": snapshot.indicators,
            }

        result = self.portfolio.buy(
            symbol=trade.asset_name,
            price=snapshot.indicators.price,
            usd_amount=trade.position_size,
        )
        if result["status"] != "executed":
            return {
                "trade_id": trade.trade_id,
                "asset_name": trade.asset_name,
                "status": trade.status,
                "action": "WAIT",
                "reason": result["reason"],
                "indicators": snapshot.indicators,
            }

        trade.status = "entered"
        trade.entry_price = snapshot.indicators.price
        trade.entry_time = now
        trade.entry_reason = reason
        return {
            "trade_id": trade.trade_id,
            "asset_name": trade.asset_name,
            "status": trade.status,
            "action": "BUY",
            "reason": reason,
            "result": result,
            "indicators": snapshot.indicators,
        }

    def _evaluate_exit(
        self,
        trade: TradeRequest,
        snapshot: MarketSnapshot,
        now: datetime,
    ) -> dict[str, Any]:
        price = snapshot.indicators.price
        exit_reasons: list[str] = []

        if price <= trade.stop_loss:
            exit_reasons.append(f"Stop loss hit because price {price:.2f} is at or below {trade.stop_loss:.2f}.")
        if price >= trade.target:
            exit_reasons.append(f"Target hit because price {price:.2f} is at or above {trade.target:.2f}.")

        exit_condition_matched, exit_condition_reason = self._match_condition(snapshot.indicators, trade.exit_condition)
        if exit_condition_matched:
            exit_reasons.append(exit_condition_reason)

        if not exit_reasons:
            return {
                "trade_id": trade.trade_id,
                "asset_name": trade.asset_name,
                "status": trade.status,
                "action": "MONITOR",
                "reason": "Trade is open and waiting for stop loss, target, or exit condition.",
                "indicators": snapshot.indicators,
            }

        reason = " ".join(exit_reasons)
        result = self.portfolio.sell(trade.asset_name, price=price, reason=reason)
        trade.status = "exited"
        trade.exit_price = price
        trade.exit_time = now
        trade.exit_reason = reason
        trade.pnl_usd = result["trade"]["pnl_usd"] if result["status"] == "executed" else None

        return {
            "trade_id": trade.trade_id,
            "asset_name": trade.asset_name,
            "status": trade.status,
            "action": "SELL",
            "reason": reason,
            "result": result,
            "indicators": snapshot.indicators,
            "pnl_usd": trade.pnl_usd,
        }

    def process_queue(
        self,
        snapshots: dict[tuple[str, str], MarketSnapshot],
        now: datetime | None = None,
    ) -> list[dict[str, Any]]:
        now = now or datetime.now()
        events: list[dict[str, Any]] = []

        for trade in self.trade_queue:
            if trade.status not in {"queued", "entered"}:
                continue

            snapshot = snapshots.get(trade.market_key)
            if snapshot is None:
                events.append(
                    {
                        "trade_id": trade.trade_id,
                        "asset_name": trade.asset_name,
                        "status": trade.status,
                        "action": "WAIT",
                        "reason": "No market snapshot available yet.",
                    }
                )
                continue

            if trade.status == "queued":
                events.append(self._evaluate_entry(trade, snapshot, now))
            else:
                events.append(self._evaluate_exit(trade, snapshot, now))

        self.prune_finished_trades()
        return events

    def queue_summary(self, latest_prices: dict[str, float] | None = None) -> dict[str, Any]:
        latest_prices = latest_prices or {}
        return {
            "queued_trades": [trade.to_dict() for trade in self.trade_queue],
            "portfolio": {
                "cash_usd": self.portfolio.cash_usd,
                "positions": list(self.portfolio.positions.keys()),
                "trade_count": len(self.portfolio.trade_log),
                "total_value_usd": self.portfolio.total_value(latest_prices),
                "trade_log": self.portfolio.trade_log,
            },
        }


class trade(TradeQueueEngine):
    """Lowercase alias kept only to match the requested class name."""
