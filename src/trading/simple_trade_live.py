from __future__ import annotations

import json
import time
from datetime import datetime

from simple_trade_engine import Trade


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


def print_update(result: dict, trade: Trade) -> None:
    indicators = result["indicators"]
    summary = trade.portfolio_summary(last_price=indicators.price)

    print(f"\n[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}]")
    print(f"Asset: {trade.stock_name} | Timeframe: {trade.interval}")
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
    print("Starting live paper trader. Press Ctrl+C to stop.")

    while True:
        try:
            candles = Trade.fetch_binance_klines(
                symbol=trade.stock_name,
                interval=trade.interval,
                limit=200,
            )
            result = trade.evaluate_latest_candle(candles)
            print_update(result, trade)
        except Exception as exc:
            print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] Live fetch failed: {exc}")
        time.sleep(5)


if __name__ == "__main__":
    main()
