from __future__ import annotations

import json
import time
from dataclasses import replace
from datetime import datetime

from simple_trade_engine import MarketSnapshot, TradeQueueEngine

PRICE_REFRESH_SECONDS = 60
INDICATOR_REFRESH_SECONDS = 300
LOOP_SLEEP_SECONDS = 5
CANDLE_LIMIT = 100


TRADE_QUEUE_JSON = """
[
  {
    "asset_name": "BTCUSDT",
    "entry_condition": "RSI > 45 AND EMA20 > EMA50",
    "exit_condition": "RSI < 35 OR EMA20 < EMA50",
    "target": 78000,
    "stop_loss": 74000,
    "position_size": 1000,
    "timeframe": "5m",
    "valid_until": "2026-04-22T23:59:59"
  }
]
"""


def print_event(event: dict, queue_engine: TradeQueueEngine, refresh_type: str) -> None:
    indicators = event.get("indicators")
    latest_prices = {}
    if indicators is not None:
        latest_prices[event["asset_name"]] = indicators.price

    summary = queue_engine.queue_summary(latest_prices=latest_prices)

    print(f"\n[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}]")
    print(f"Trade ID: {event['trade_id']} | Asset: {event['asset_name']}")
    print(f"Refresh: {refresh_type}")
    print(f"Action: {event['action']} | Status: {event['status']}")
    print(f"Explanation: {event['reason']}")

    if indicators is not None:
        print(
            "Indicators: "
            f"price={indicators.price:.2f}, "
            f"rsi={indicators.rsi}, "
            f"ema20={indicators.ema20}, "
            f"ema50={indicators.ema50}, "
            f"macd={indicators.macd}, "
            f"macd_signal={indicators.macd_signal}, "
            f"bb_upper={indicators.bollinger_upper}, "
            f"bb_middle={indicators.bollinger_middle}, "
            f"bb_lower={indicators.bollinger_lower}"
        )

    if "pnl_usd" in event:
        print(f"Realized PnL: {event['pnl_usd']}")

    print(f"Queue Summary: {json.dumps(summary, default=str)}")


def refresh_snapshots(
    queue_engine: TradeQueueEngine,
    snapshots: dict[tuple[str, str], MarketSnapshot],
) -> str | None:
    now = datetime.now()
    refresh_type = None

    for asset_name, timeframe in queue_engine.active_market_keys():
        snapshot = snapshots.get((asset_name, timeframe))

        indicator_due = (
            snapshot is None
            or (now - snapshot.last_indicator_refresh).total_seconds() >= INDICATOR_REFRESH_SECONDS
        )
        if indicator_due:
            candles = queue_engine.__class__.fetch_binance_klines(asset_name, interval=timeframe, limit=CANDLE_LIMIT)
            indicators = queue_engine.__class__.calculate_indicators(candles)
            snapshots[(asset_name, timeframe)] = MarketSnapshot(
                asset_name=asset_name,
                timeframe=timeframe,
                indicators=indicators,
                last_indicator_refresh=now,
                last_price_refresh=now,
            )
            refresh_type = "5-min indicator refresh"
            continue

        price_due = (now - snapshot.last_price_refresh).total_seconds() >= PRICE_REFRESH_SECONDS
        if price_due:
            latest_price = queue_engine.__class__.fetch_latest_price(asset_name)
            snapshots[(asset_name, timeframe)] = replace(
                snapshot,
                indicators=replace(snapshot.indicators, price=latest_price),
                last_price_refresh=now,
            )
            refresh_type = "1-minute price refresh"

    return refresh_type


def main() -> None:
    queue_engine = TradeQueueEngine.from_json(TRADE_QUEUE_JSON, portfolio_usd=100_000)
    snapshots: dict[tuple[str, str], MarketSnapshot] = {}
    print("Starting queue-based live paper trader. Press Ctrl+C to stop.")

    while True:
        try:
            refresh_type = refresh_snapshots(queue_engine, snapshots)
            if refresh_type is not None:
                events = queue_engine.process_queue(snapshots=snapshots, now=datetime.now())
                for event in events:
                    print_event(event, queue_engine, refresh_type=refresh_type)
        except Exception as exc:
            print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] Live queue processing failed: {exc}")
        time.sleep(LOOP_SLEEP_SECONDS)


if __name__ == "__main__":
    main()
