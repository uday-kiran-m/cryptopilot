from __future__ import annotations

import json
import time
from dataclasses import replace
from datetime import datetime

from simple_trade_engine import Trade

PRICE_REFRESH_SECONDS = 60
INDICATOR_REFRESH_SECONDS = 300
LOOP_SLEEP_SECONDS = 5
CANDLE_LIMIT = 100


CONFIG_JSON = """
{
  "asset": "BTCUSDT",
  "timeframe": "5m",
  "entry_condition": "RSI > 45 AND EMA20 > EMA50",
  "exit_condition": "RSI < 35 OR EMA20 < EMA50",
  "position_size": 0.01,
  "risk_reward_ratio": 2.0
}
"""


def print_update(result: dict, trade: Trade, refresh_type: str) -> None:
    indicators = result["indicators"]
    summary = trade.portfolio_summary(last_price=indicators.price)

    print(f"\n[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}]")
    print(f"Asset: {trade.stock_name} | Timeframe: {trade.interval}")
    print(f"Refresh: {refresh_type}")
    print(f"Action: {result['action']}")
    print(f"Explanation: {result['reason']}")
    print(f"Risk/Reward Ratio: {result.get('risk_reward_ratio')}")
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
    print(f"Portfolio: {json.dumps(summary, default=str)}")


def main() -> None:
    trade = Trade.from_json(CONFIG_JSON, portfolio_usd=100_000)
    cached_indicators = None
    last_price_refresh = 0.0
    last_indicator_refresh = 0.0
    print("Starting live paper trader with hourly indicator refresh and 1-minute price refresh. Press Ctrl+C to stop.")

    while True:
        try:
            now = time.time()

            if cached_indicators is None or now - last_indicator_refresh >= INDICATOR_REFRESH_SECONDS:
                candles = Trade.fetch_binance_klines(
                    symbol=trade.stock_name,
                    interval=trade.interval,
                    limit=CANDLE_LIMIT,
                )
                cached_indicators = Trade.calculate_indicators(candles)
                last_indicator_refresh = now
                last_price_refresh = now
                result = trade.evaluate_indicator_snapshot(cached_indicators)
                print_update(result, trade, refresh_type="hourly 50-candle refresh")
            elif now - last_price_refresh >= PRICE_REFRESH_SECONDS:
                latest_price = Trade.fetch_latest_price(trade.stock_name)
                cached_indicators = replace(cached_indicators, price=latest_price)
                last_price_refresh = now
                result = trade.evaluate_indicator_snapshot(cached_indicators)
                print_update(result, trade, refresh_type="1-minute latest price")
        except Exception as exc:
            print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] Live fetch failed: {exc}")
        time.sleep(LOOP_SLEEP_SECONDS)


if __name__ == "__main__":
    main()
